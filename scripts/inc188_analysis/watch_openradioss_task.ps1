# INC-188 OpenRadioss P1r13-P1r16 watchdog for Windows Task Scheduler.
# One-shot per run (schedule every 5 min). Independent of any editor / AI session.
# ASCII only on purpose: Windows PowerShell 5.1 reads BOM-less UTF-8 as ANSI.
#
# Reads the host-side bind mount of /work, so it still works when the docker API is down.
# Alerts ONLY on state change: ALARM file (append) + Telegram. Silence = healthy.
# States: OK / ERROR_TERMINATION / NORMAL_TERMINATION / STALE (2 consecutive checks) /
#         DT_COLLAPSE / MASS_SCALING / LOG_MISSING
param(
  [string]$WorkDir   = "D:\Clawdbot_Docker_20260125\clawstack_v2\data\work",
  [string]$StateFile = "D:\Clawdbot_Docker_20260125\data\workspace\openradioss_watch_state.txt",
  [string]$AlarmFile = "D:\Clawdbot_Docker_20260125\data\workspace\ALARM_openradioss_p1r13_16.txt",
  [string]$EnvFile   = "D:\Clawdbot_Docker_20260125\.env",
  [string[]]$Tags    = @("P1r18"),     # P1r13-16 finished 2026-09-24; P1r17 = round-punch penetration run (stroke 4mm)
  [int]$StaleSec     = 600,
  [string]$DiskDrive = "D",
  [double]$DiskMinGB = 10,
  [switch]$NoTelegram,
  [switch]$NoAutoResume,
  [string]$Container = "clawstack-unified-openradioss-1",
  [int]$ResumeCooldownMin = 120,
  [int]$ResumeThreads = 12,   # K10 runs one engine at a time; >12 total threads slows everything (i9-13900HK P-cores)
  [string]$ResumeLogFile = "D:\Clawdbot_Docker_20260125\data\workspace\openradioss_autoresume_state.txt",
  [switch]$NoAutoFinalize,
  # Memory cap (2026-09-28): with /SURF/PART/ALL in the punch contact the engine RSS grows ~85 MB/min
  # (25.7 GB after 4.4 h) and starved the MechaRL trainers. A restart from the .rst resets it, so when
  # RSS > MemCapMB and a restart file was written < MemCapRstAgeMin ago, stop + resume (loses < that).
  [int]$MemCapMB = 8000,
  [int]$MemCapRstAgeMin = 6,
  [switch]$NoMemCap,
  [string]$MemCapLog = "D:\Clawdbot_Docker_20260125\data\workspace\openradioss_memcap_log.txt",
  # Run queue (2026-09-28): one tag per line; when no starter/engine is alive the head is launched
  # with chain_P1r19_21.sh (deck PANEL4MM_<tag>_0000/0001.rad must be in WorkDir) and removed.
  [string]$QueueFile = "D:\Clawdbot_Docker_20260125\data\workspace\openradioss_queue.txt",
  [double]$QueueMinFreeGB = 8,
  [switch]$NoQueue,
  [switch]$NoResultReport,
  [string]$PythonExe = "C:\Users\yasu\AppData\Local\Programs\Python\Python310\python.exe",
  [string]$VtkDir = "F:\clawstack_data\inc188\vtk",
  [string]$BashExe = "C:\Program Files\Git\bin\bash.exe",
  [string]$FinalizeScript = "D:/Clawdbot_Docker_20260125/scripts/inc188_analysis/finalize_runs.sh"
)

$ErrorActionPreference = "Stop"

# Tags can be switched without re-registering the task: one tag per line in this file
# (written by c0_bisect.sh when it launches the next run). An explicit -Tags on the command line still wins.
$TagsFile = "D:\Clawdbot_Docker_20260125\data\workspace\openradioss_watch_tags.txt"
if (-not $PSBoundParameters.ContainsKey("Tags") -and (Test-Path -LiteralPath $TagsFile)) {
  $ft = @(Get-Content -LiteralPath $TagsFile | ForEach-Object { $_.Trim() } | Where-Object { $_ -match "^[A-Za-z0-9_]+$" })
  if ($ft.Count -gt 0) { $Tags = $ft }
}

function Send-Tg([string]$text) {
  if ($NoTelegram) { return }
  try {
    $tok = $null; $chat = $null
    foreach ($ln in Get-Content -LiteralPath $EnvFile) {
      if ($ln -like "TELEGRAM_BOT_TOKEN=*") { $tok  = $ln.Substring(19).Trim().Trim('"') }
      if ($ln -like "TELEGRAM_CHAT_ID=*")   { $chat = $ln.Substring(17).Trim().Trim('"') }
    }
    if (-not $tok -or -not $chat) { return }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $body = @{ chat_id = $chat; text = $text }
    Invoke-RestMethod -Uri ("https://api.telegram.org/bot" + $tok + "/sendMessage") -Method Post -Body $body -TimeoutSec 20 | Out-Null
  } catch {
    Add-Content -LiteralPath $AlarmFile -Value ((Get-Date -Format "yyyy-MM-dd HH:mm:ss") + " [telegram send failed] " + $_.Exception.Message.Split("`n")[0])
  }
}

# ---- load previous state: lines "TAG|STATE|STALECOUNT" ----
$prev = @{}
if (Test-Path -LiteralPath $StateFile) {
  foreach ($ln in Get-Content -LiteralPath $StateFile) {
    $p = $ln.Split("|")
    if ($p.Count -ge 3) { $prev[$p[0]] = @{ state = $p[1]; stale = [int]$p[2] } }
  }
}

$resumeLog = @{}   # lines "TAG|yyyy-MM-dd HH:mm:ss" of the last auto-resume attempt
if (Test-Path -LiteralPath $ResumeLogFile) {
  foreach ($ln in Get-Content -LiteralPath $ResumeLogFile) { $p = $ln.Split("|"); if ($p.Count -ge 2) { $resumeLog[$p[0]] = $p[1] } }
}

$now = Get-Date
$newState = @{}
$alerts = @()

# ---- container itself stopped (2026-09-28 05:40: an external 'docker stop' left it Exited(137);
#      restart policy does not undo a manual stop and every auto-resume below is a docker exec,
#      so nothing would ever have recovered it). Start it; the STALE logic then resumes the engine.
if (-not $NoAutoResume) {
  $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  $running = (& docker inspect -f "{{.State.Running}}" $Container 2>$null | Out-String).Trim()
  if ($LASTEXITCODE -eq 0 -and $running -eq "false") {
    $st = (& docker inspect -f "{{.State.Status}} exit={{.State.ExitCode}} at={{.State.FinishedAt}}" $Container 2>$null | Out-String).Trim()
    $out = (& docker start $Container 2>&1 | Out-String).Trim()
    $alerts += ("CONTAINER was not running (" + $st + ") -> docker start: " + $out + " (rc " + $LASTEXITCODE + ")")
  }
  $ErrorActionPreference = $eap
}

foreach ($t in $Tags) {
  # After a restart the engine writes engine_run<tag>_r<N>.log; follow the newest run's log.
  $f = Join-Path $WorkDir ("engine_run" + $t + ".log")
  $newest = @(Get-ChildItem -LiteralPath $WorkDir -Filter ("engine_run" + $t + "*.log") -ErrorAction SilentlyContinue |
              Where-Object { $_.Name -match ("^engine_run" + $t + "(_r\d+)?\.log$") } |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1)
  if ($newest.Count -gt 0) { $f = $newest[0].FullName }
  $old = $prev[$t]
  $oldState = "NONE"; $oldStale = 0
  if ($old) { $oldState = $old.state; $oldStale = $old.stale }
  $state = "OK"; $extra = ""; $stale = 0

  if (-not (Test-Path -LiteralPath $f)) {
    $state = "LOG_MISSING"
  } else {
    $item = Get-Item -LiteralPath $f
    $age = ($now - $item.LastWriteTime).TotalSeconds
    $tail = @(Get-Content -LiteralPath $f -Tail 60 -ErrorAction SilentlyContinue)
    $joined = ($tail -join "`n")
    $ncLine = ($tail | Where-Object { $_ -match "NC=" } | Select-Object -Last 1)
    if ($joined -match "ERROR TERMINATION") {
      $state = "ERROR_TERMINATION"
    } elseif ($joined -match "NORMAL TERMINATION") {
      $state = "NORMAL_TERMINATION"
    } elseif ($age -gt $StaleSec) {
      $stale = $oldStale + 1
      if ($stale -ge 2) { $state = "STALE"; $extra = ("age=" + [int]$age + "s") }
      else { $state = $oldState; if ($state -eq "NONE") { $state = "OK" } }   # first sighting: wait for confirmation
    } elseif ($ncLine) {
      if ($ncLine -match "DT=\s*([0-9.]+E[+-][0-9]+)") {
        if ([double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture) -lt 5e-10) { $state = "DT_COLLAPSE"; $extra = ("DT=" + $Matches[1]) }
      }
      if ($ncLine -match "DM/M=\s*([0-9.]+E[+-][0-9]+)") {
        if ([double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture) -ne 0) { $state = "MASS_SCALING"; $extra = ("DM/M=" + $Matches[1]) }
      }
    }
  }

  # ---- auto-resume a confirmed STALE engine (2026-09-23: a Windows sign-out killed all 4 and
  #      nothing restarted them). openradioss_restart_prep.sh refuses if an engine for the tag is
  #      alive and aborts on a missing/truncated restart file, so calling it is safe. At most one
  #      attempt per tag per $ResumeCooldownMin so a deck that dies on start cannot loop.
  if ($state -eq "STALE" -and -not $NoAutoResume) {
    $last = $null
    if ($resumeLog[$t]) { $last = [datetime]::ParseExact($resumeLog[$t], "yyyy-MM-dd HH:mm:ss", $null) }
    if (-not $last -or ($now - $last).TotalMinutes -ge $ResumeCooldownMin) {
      $resumeLog[$t] = $now.ToString("yyyy-MM-dd HH:mm:ss")
      $out = ""
      $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"   # PS5.1: native stderr must not throw
      try {
        $out = (& docker exec -e ("NT=" + $ResumeThreads) $Container bash /work/openradioss_restart_prep.sh $t --go 2>&1 | ForEach-Object { "$_" } | Out-String)
        if ($LASTEXITCODE -ne 0 -and -not $out) { $out = "docker exec exit " + $LASTEXITCODE }
      } catch { $out = "docker exec failed: " + $_.Exception.Message }
      $ErrorActionPreference = $eap
      $res = ($out -split "`n" | Where-Object { $_ -match "LAUNCHED|REFUSE|ABORT|failed|Error" } | Select-Object -First 2) -join " / "
      if (-not $res) { $res = ($out.Trim() -split "`n" | Select-Object -Last 1) }
      $extra = ($extra + " AUTO-RESUME: " + $res.Trim())
      $alerts += ($t + ": auto-resume attempted: " + $res.Trim())
    }
  }

  # ---- memory cap: restart a running engine from a fresh restart file when its RSS is too high
  if ($state -eq "OK" -and -not $NoAutoResume -and -not $NoMemCap) {
    $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    $rssLine = (& docker exec $Container bash /work/engine_ctl.sh rss $t 2>$null | Select-Object -First 1)
    $ErrorActionPreference = $eap
    $rss = 0
    if ($rssLine -match "^\d+\s+(\d+)") { $rss = [int]$Matches[1] }
    if ($rss -gt $MemCapMB) {
      $rst = @(Get-ChildItem -LiteralPath $WorkDir -Filter ("PANEL4MM_" + $t + "_*_0001.rst") -ErrorAction SilentlyContinue |
               Where-Object { $_.Name -notmatch "_0000_0001\.rst$" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1)
      $age = 1e9
      if ($rst.Count -gt 0) { $age = ($now - $rst[0].LastWriteTime).TotalMinutes }
      if ($age -lt $MemCapRstAgeMin -and $age -gt 0.5) {
        $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        $stopOut = (& docker exec $Container bash /work/engine_ctl.sh stop $t 2>&1 | Out-String).Trim()
        $out = (& docker exec -e ("NT=" + $ResumeThreads) $Container bash /work/openradioss_restart_prep.sh $t --go 2>&1 | ForEach-Object { "$_" } | Out-String)
        $ErrorActionPreference = $eap
        $res = ($out -split "`n" | Where-Object { $_ -match "LAUNCHED|REFUSE|ABORT|failed|Error" } | Select-Object -First 1)
        $resumeLog[$t] = $now.ToString("yyyy-MM-dd HH:mm:ss")
        $alerts += ($t + ": MEMCAP RSS " + $rss + " MB > " + $MemCapMB + " -> " + $stopOut + "; resume from " + $rst[0].Name + " (" + [math]::Round($age,1) + " min old): " + "$res".Trim())
      } else {
        $extra = ($extra + " memcap: RSS " + $rss + " MB, waiting for a fresh restart file (newest " + [math]::Round($age,1) + " min old)")
      }
      Add-Content -LiteralPath $MemCapLog -Encoding ASCII -Value ($now.ToString("yyyy-MM-dd HH:mm:ss") + " " + $t + " RSS " + $rss + " MB > cap " + $MemCapMB + ", newest rst " + [math]::Round($age,1) + " min old -> " + $(if ($age -lt $MemCapRstAgeMin -and $age -gt 0.5) { "RESTART" } else { "wait" }))
    }
  }

  # ---- auto post-process a finished run (2026-09-26: finalize_runs.sh exited after P1r17 and nothing
  #      would have processed P1r18). Launched via WMI so it is not a child of this task / any session.
  #      Skipped when FINALIZED_<tag> exists or a finalize_runs.sh for this tag is already alive.
  if ($state -eq "NORMAL_TERMINATION" -and -not $NoAutoFinalize) {
    $done = Join-Path $VtkDir ("FINALIZED_" + $t)
    if (-not (Test-Path -LiteralPath $done)) {
      $alive = @(Get-CimInstance Win32_Process -Filter "Name='bash.exe'" |
                 Where-Object { $_.CommandLine -like ("*finalize_runs.sh*" + $t + "*") })
      if ($alive.Count -eq 0) {
        $cmd = '"' + $BashExe + '" -lc "bash ' + $FinalizeScript + ' ' + $t + '"'
        try {
          $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd }
          $alerts += ($t + ": auto-finalize launched (pid " + $r.ProcessId + ", rc " + $r.ReturnValue + ")")
        } catch { $alerts += ($t + ": auto-finalize launch FAILED: " + $_.Exception.Message) }
      }
    }
  }

  $newState[$t] = @{ state = $state; stale = $stale }
  if ($state -ne $oldState -and -not ($oldState -eq "NONE" -and $state -eq "OK")) {
    $alerts += ($t + ": " + $oldState + " -> " + $state + " " + $extra)
  }
}

# ---- disk space of the drive the engines write to (a full drive kills engines / corrupts restart files) ----
$diskState = "OK"; $diskExtra = ""
try {
  $freeGB = (Get-PSDrive $DiskDrive).Free / 1GB
  if ($freeGB -lt $DiskMinGB) { $diskState = "DISK_LOW"; $diskExtra = ($DiskDrive + ": free " + [math]::Round($freeGB,1) + " GB < " + $DiskMinGB + " GB") }
} catch { $diskState = "OK" }
$oldDisk = "NONE"
if ($prev["DISK"]) { $oldDisk = $prev["DISK"].state }
$newState["DISK"] = @{ state = $diskState; stale = 0 }
if ($diskState -ne $oldDisk -and -not ($oldDisk -eq "NONE" -and $diskState -eq "OK")) {
  $alerts += ("DISK: " + $oldDisk + " -> " + $diskState + " " + $diskExtra)
}

# ---- run queue: keep the engine slot busy (a finished run must not leave it idle) ----
if (-not $NoQueue -and (Test-Path -LiteralPath $QueueFile)) {
  $q = @(Get-Content -LiteralPath $QueueFile | ForEach-Object { $_.Trim() } | Where-Object { $_ -match "^[A-Za-z0-9_]+$" })
  # 2026-09-28 15:46: after a WSL shutdown no engine was alive, so the queue launched P1r21 while
  # P1r20 was only interrupted (resume pending). A watched run whose newest log has neither NORMAL nor
  # ERROR TERMINATION is unfinished -> leave the slot to its auto-resume.
  $unfinished = @($Tags | Where-Object { $newState[$_] -and $newState[$_].state -notin @("NORMAL_TERMINATION", "ERROR_TERMINATION", "LOG_MISSING") })
  if ($q.Count -gt 0 -and $unfinished.Count -gt 0) {
    Add-Content -LiteralPath $MemCapLog -Encoding ASCII -Value ($now.ToString("yyyy-MM-dd HH:mm:ss") + " QUEUE: " + $q[0] + " held, unfinished watched run(s): " + ($unfinished -join ","))
  }
  if ($q.Count -gt 0 -and $unfinished.Count -eq 0) {
    $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    $anyOut = @(& docker exec $Container bash /work/engine_ctl.sh any 2>$null)
    $anyRc = $LASTEXITCODE
    $ErrorActionPreference = $eap
    if ($anyRc -eq 0 -and $anyOut.Count -eq 0) {
      $next = $q[0]
      $deck = Join-Path $WorkDir ("PANEL4MM_" + $next + "_0000.rad")
      $startedLog = Join-Path $WorkDir ("engine_run" + $next + ".log")
      $freeGB = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
      if (-not (Test-Path -LiteralPath $deck) -or -not (Test-Path -LiteralPath (Join-Path $WorkDir ("PANEL4MM_" + $next + "_0001.rad")))) {
        $alerts += ("QUEUE: deck for " + $next + " missing in " + $WorkDir + " -> removed from queue")
        Set-Content -LiteralPath $QueueFile -Value ($q | Select-Object -Skip 1) -Encoding ASCII
      } elseif (Test-Path -LiteralPath $startedLog) {
        $alerts += ("QUEUE: " + $next + " was already started before (" + $startedLog + ") -> removed from queue, not relaunched")
        Set-Content -LiteralPath $QueueFile -Value ($q | Select-Object -Skip 1) -Encoding ASCII
      } elseif ($freeGB -lt $QueueMinFreeGB) {
        Add-Content -LiteralPath $MemCapLog -Encoding ASCII -Value ($now.ToString("yyyy-MM-dd HH:mm:ss") + " QUEUE: " + $next + " waiting, host free RAM " + [math]::Round($freeGB,1) + " GB < " + $QueueMinFreeGB)
      } else {
        $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        $out = (& docker exec -d -e ("TAGS=" + $next) -e ("NT=" + $ResumeThreads) $Container bash /work/chain_P1r19_21.sh 2>&1 | Out-String).Trim()
        $rc = $LASTEXITCODE
        $ErrorActionPreference = $eap
        Set-Content -LiteralPath $QueueFile -Value ($q | Select-Object -Skip 1) -Encoding ASCII
        if ($rc -eq 0) {
          $keep = @($Tags | Where-Object { $_ -ne $next } | Select-Object -Last 2) + $next
          if (-not $PSBoundParameters.ContainsKey("Tags")) { Set-Content -LiteralPath $TagsFile -Value $keep -Encoding ASCII }
          $alerts += ("QUEUE: launched " + $next + " (nt=" + $ResumeThreads + ", free RAM " + [math]::Round($freeGB,1) + " GB); " + ($q.Count - 1) + " left in queue")
        } else {
          $alerts += ("QUEUE: launch of " + $next + " FAILED rc=" + $rc + " " + $out)
        }
      }
    }
  }
}

# ---- result summary once a watched run is finalized (the user gets the result even when no AI
#      session is looking; 2026-09-29 a session-side notice arrived 7 h late) ----
if (-not $NoResultReport) {
  foreach ($t in $Tags) {
    $fin = Join-Path $VtkDir ("FINALIZED_" + $t)
    $rep = Join-Path $VtkDir ("REPORTED_" + $t)
    if ((Test-Path -LiteralPath $fin) -and -not (Test-Path -LiteralPath $rep)) {
      $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
      $env:PYTHONIOENCODING = "utf-8"
      $tbl = (& $PythonExe "D:\Clawdbot_Docker_20260125\scripts\inc188_analysis\compare_runs.py" $t 2>&1 | Where-Object { "$_" -match "^\|" } | Out-String).Trim()
      $ErrorActionPreference = $eap
      if ($tbl) {
        $alerts += ("RESULT " + $t + " (finalized):`n" + $tbl)
        Set-Content -LiteralPath $rep -Value ($now.ToString("yyyy-MM-dd HH:mm:ss")) -Encoding ASCII
      } else {
        Add-Content -LiteralPath $MemCapLog -Encoding ASCII -Value ($now.ToString("yyyy-MM-dd HH:mm:ss") + " RESULT " + $t + ": compare_runs.py produced no table, retry next tick")
      }
    }
  }
}

# ---- forward new lines of the per-frame monitor's alarm file (first separation / punch penetration) ----
$rhAlarm = Join-Path (Split-Path -Parent $StateFile) "ALARM_round_hole.txt"
$rhSeen = 0
if ($prev["RH_ALARM_LINES"]) { $rhSeen = $prev["RH_ALARM_LINES"].stale }
$rhLines = @()
if (Test-Path -LiteralPath $rhAlarm) { $rhLines = @(Get-Content -LiteralPath $rhAlarm) }
if ($rhLines.Count -gt $rhSeen) { foreach ($ln in ($rhLines | Select-Object -Skip $rhSeen)) { $alerts += ("ROUND HOLE: " + $ln) } }
$newState["RH_ALARM_LINES"] = @{ state = "SEEN"; stale = $rhLines.Count }

# ---- persist state, then alert ----
$lines = foreach ($k in ($Tags + "DISK" + "RH_ALARM_LINES")) { $k + "|" + $newState[$k].state + "|" + $newState[$k].stale }
Set-Content -LiteralPath $StateFile -Value $lines -Encoding ASCII
if ($resumeLog.Count -gt 0) {
  Set-Content -LiteralPath $ResumeLogFile -Value ($resumeLog.Keys | ForEach-Object { $_ + "|" + $resumeLog[$_] }) -Encoding ASCII
}

if ($alerts.Count -gt 0) {
  $stamp = $now.ToString("yyyy-MM-dd HH:mm:ss")
  foreach ($a in $alerts) { Add-Content -LiteralPath $AlarmFile -Value ($stamp + " " + $a) }
  Send-Tg ("INC-188 OpenRadioss watchdog " + $stamp + "`n" + ($alerts -join "`n"))
}
exit 0
