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
  [double]$DiskMinGB = 15,   # one restart file is 1.55 GB; deck/anim/TH writes need headroom
  [string]$RstArchive = "G:\clawstack_data\inc188\rst_archive",
  [switch]$NoTelegram,
  [switch]$NoAutoResume,
  [string]$Container = "clawstack-unified-openradioss-1",
  [int]$ResumeCooldownMin = 120,
  [int]$ResumeThreads = 12,   # one engine at a time (2026-10-01: two engines were 30% slower in total)
  [string]$ResumeLogFile = "D:\Clawdbot_Docker_20260125\data\workspace\openradioss_autoresume_state.txt",
  [switch]$NoAutoFinalize,
  # Memory cap (2026-09-28): with /SURF/PART/ALL in the punch contact the engine RSS grows ~85 MB/min
  # (25.7 GB after 4.4 h) and starved the MechaRL trainers. A restart from the .rst resets it, so when
  # RSS > MemCapMB and a restart file was written < MemCapRstAgeMin ago, stop + resume (loses < that).
  [int]$MemCapMB = 8000,
  [int]$MemCapRstAgeMin = 6,
  [switch]$NoMemCap,
  [double]$MassBlowupRatio = 0.05,   # DM/M above this = a blow-up absorbed by mass scaling
  [string]$MemCapLog = "D:\Clawdbot_Docker_20260125\data\workspace\openradioss_memcap_log.txt",
  # Run queue (2026-09-28): one tag per line; when no starter/engine is alive the head is launched
  # with chain_P1r19_21.sh (deck PANEL4MM_<tag>_0000/0001.rad must be in WorkDir) and removed.
  [string]$QueueFile = "D:\Clawdbot_Docker_20260125\data\workspace\openradioss_queue.txt",
  [double]$QueueMinFreeGB = 8,
  [switch]$NoQueue,
  [int]$MaxEngines = 1,   # 2026-10-01: 2 engines (12+10 threads) ran at 3.3 cycles/s in total vs 6.1 for one engine alone
  [double]$QueueMinFreeGB2 = 16,   # free RAM needed to start a second engine next to a running one
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

# live starters/engines once per tick (DEAD detection, crash retry, queue)
$eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
$aliveLines = @(& docker exec $Container bash /work/engine_ctl.sh any 2>$null)
$aliveOk = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $eap
$aliveTagsNow = @($aliveLines | ForEach-Object { ("$_".Trim() -split "\s+")[1] } | Where-Object { $_ })

# crash bookkeeping: "tag|log|crashT|retries|status" (status RETRIED / GAVE_UP / FAILED)
$CrashFile = Join-Path (Split-Path -Parent $StateFile) "openradioss_crash_state.txt"
$crash = @{}
if (Test-Path -LiteralPath $CrashFile) {
  foreach ($ln in Get-Content -LiteralPath $CrashFile) {
    $p = $ln.Split("|"); if ($p.Count -ge 5) { $crash[$p[0]] = @{ log = $p[1]; T = [double]$p[2]; n = [int]$p[3]; status = $p[4] } }
  }
}

function Invoke-ResumeOnce([string]$tag) {
  $o = ""
  $eap2 = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  try {
    $o = (& docker exec -e ("NT=" + $ResumeThreads) $Container bash /work/openradioss_restart_prep.sh $tag --go 2>&1 | ForEach-Object { "$_" } | Out-String)
  } catch { $o = "docker exec failed: " + $_.Exception.Message }
  $ErrorActionPreference = $eap2
  return $o
}

# 2026-10-04 15:29: the newest restart file was truncated (a memory-cap KILL during its write) and every
# resume attempt aborted on it for 7.5 h. If restart_prep refuses the newest run's restart file
# (truncated / missing), move that run's deck and restart file aside and resume from the previous one.
function Invoke-Resume([string]$tag) {
  $o = Invoke-ResumeOnce $tag
  if ($o -match "ABORT: restart file (size|\S+ missing)") {
    $decks = @(Get-ChildItem -LiteralPath $WorkDir -Filter ("PANEL4MM_" + $tag + "_00*.rad") -ErrorAction SilentlyContinue |
               Where-Object { $_.Name -match ("^PANEL4MM_" + $tag + "_(\d{4})\.rad$") -and [int]$Matches[1] -ge 2 } | Sort-Object Name -Descending)
    if ($decks.Count -gt 0) {
      $n = $decks[0].Name.Substring(("PANEL4MM_" + $tag + "_").Length, 4)
      $bad = Join-Path $WorkDir ("corrupt_" + $tag + "_" + $now.ToString("yyyyMMdd_HHmm"))
      New-Item -ItemType Directory -Force -Path $bad | Out-Null
      Move-Item -LiteralPath $decks[0].FullName -Destination $bad -Force
      $r = Join-Path $WorkDir ("PANEL4MM_" + $tag + "_" + $n + "_0001.rst")
      if (Test-Path -LiteralPath $r) { Move-Item -LiteralPath $r -Destination $bad -Force }
      $o2 = Invoke-ResumeOnce $tag
      $o = $o + "`nFALLBACK: run " + $n + " restart file unusable, moved to " + (Split-Path -Leaf $bad) + "; retried from the previous one:`n" + $o2
    }
  }
  return $o
}

# a restart file is complete only if it is the size of the run's previous one (+-0.2 %, else +-2 % of the
# starter's) and neither size nor time changes over 2 s (it is not being written right now)
function Test-RstComplete([string]$tag, $item) {
  if (-not $item) { return $false }
  $n = 0
  if ($item.Name -match "_(\d{4})_0001\.rst$") { $n = [int]$Matches[1] }
  $prev = Join-Path $WorkDir ("PANEL4MM_" + $tag + "_" + ($n - 1).ToString("0000") + "_0001.rst")
  $st = Join-Path $WorkDir ("PANEL4MM_" + $tag + "_0000_0001.rst")
  $ok = $false
  if ($n -gt 1 -and (Test-Path -LiteralPath $prev)) {
    $p = (Get-Item -LiteralPath $prev).Length; $ok = [math]::Abs($item.Length - $p) -le $p * 0.002
  } elseif (Test-Path -LiteralPath $st) {
    $p = (Get-Item -LiteralPath $st).Length; $ok = [math]::Abs($item.Length - $p) -le $p * 0.02
  }
  if (-not $ok) { return $false }
  Start-Sleep -Seconds 2
  $again = Get-Item -LiteralPath $item.FullName
  return ($again.Length -eq $item.Length -and $again.LastWriteTimeUtc -eq $item.LastWriteTimeUtc)
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
      # 2026-10-07: P1r29f blew up (negative volumes, "NODAL VELOCITY IS TOO HIGH FOR INTERFACE") at
      # T=0.142 of 0.51 ms, the engine still printed NORMAL TERMINATION, and the queue moved on as if it
      # had finished. A normal end short of the deck's tstop is a crash.
      $tstopRun = 0.0
      $engDeck = Join-Path $WorkDir ("PANEL4MM_" + $t + "_0001.rad")
      if (Test-Path -LiteralPath $engDeck) {
        $l2 = @(Get-Content -LiteralPath $engDeck -TotalCount 2)
        if ($l2.Count -ge 2) { [double]::TryParse($l2[1].Trim(), [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$tstopRun) | Out-Null }
      }
      $tEnd = 0.0
      $ncEnd = $ncLine
      if (-not $ncEnd) {   # the end-of-run summary pushes the last NC line out of the 60-line tail
        $ncEnd = (@(Get-Content -LiteralPath $f -Tail 3000 -ErrorAction SilentlyContinue) | Where-Object { $_ -match "NC=" } | Select-Object -Last 1)
      }
      if ($ncEnd -match "\sT=\s*([0-9.]+E[+-][0-9]+)") { $tEnd = [double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture) }
      if ($tstopRun -gt 0 -and $tEnd -gt 0 -and $tEnd -lt 0.98 * $tstopRun) {
        $state = "ERROR_TERMINATION"
        $extra = ("normal termination at T=" + $tEnd + " < tstop " + $tstopRun + " (early stop)")
        if ($joined -match "NODAL VELOCITY IS TOO HIGH") { $extra = $extra + ", nodal velocity too high" }
        $ncLine = $ncEnd   # so the crash bookkeeping below gets the real stop time
      }
    } elseif ($age -gt $StaleSec) {
      $stale = $oldStale + 1
      if ($stale -ge 2) { $state = "STALE"; $extra = ("age=" + [int]$age + "s") }
      else { $state = $oldState; if ($state -eq "NONE") { $state = "OK" } }   # first sighting: wait for confirmation
    } elseif ($ncLine) {
      if ($ncLine -match "DT=\s*([0-9.]+E[+-][0-9]+)") {
        if ([double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture) -lt 5e-10) { $state = "DT_COLLAPSE"; $extra = ("DT=" + $Matches[1]) }
      }
      if ($ncLine -match "DM/M=\s*([0-9.]+E[+-][0-9]+)") {
        $dmm = [double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture)
        if ($dmm -ne 0) { $state = "MASS_SCALING"; $extra = ("DM/M=" + $Matches[1]) }
        # 2026-10-08: a node flew off at 29 km/s in P1r33f and the nodal mass scaling (CST2) absorbed it by
        # adding 3.96x the model mass (ERR 99.9 %): the run went on, but everything after it is invalid.
        if ($dmm -gt $MassBlowupRatio) { $state = "MASS_BLOWUP"; $extra = ("DM/M=" + $Matches[1] + " > " + $MassBlowupRatio) }
      }
    }
  }

  # ---- DEAD: no starter/engine process for the tag, log not terminated and quiet > 90 s.
  #      2026-10-04: waiting for STALE (2 x 10 min of silence) wasted up to 20 min per death.
  if ($aliveOk -and $t -notin $aliveTagsNow -and (Test-Path -LiteralPath $f) -and
      $state -in @("OK", "STALE", "DT_COLLAPSE", "MASS_SCALING") -and $age -gt 90 -and -not $NoAutoResume) {
    $state = "DEAD"; $extra = ("no engine process, log quiet " + [int]$age + " s")
    $dk = $t + "#dead"; $lastD = $null
    if ($resumeLog[$dk]) { $lastD = [datetime]::ParseExact($resumeLog[$dk], "yyyy-MM-dd HH:mm:ss", $null) }
    if (-not $lastD -or ($now - $lastD).TotalMinutes -ge 10) {
      $resumeLog[$dk] = $now.ToString("yyyy-MM-dd HH:mm:ss")
      $out = Invoke-Resume $t
      $res = (($out -split "`n" | Where-Object { $_ -match "LAUNCHED|REFUSE|ABORT|FALLBACK|failed|Error" } | Select-Object -First 3) -join " / ")
      $alerts += ($t + ": engine DEAD (" + $extra + ") -> immediate resume: " + "$res".Trim())
    }
  }

  # ---- MASS_BLOWUP: stop the engine and give the run up (a resume would only repeat it); queue moves on
  if ($state -eq "MASS_BLOWUP" -and $aliveOk -and $t -in $aliveTagsNow -and -not $NoAutoResume) {
    $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    $stopOut = (& docker exec $Container bash /work/engine_ctl.sh stop $t 2>&1 | Out-String).Trim()
    $ErrorActionPreference = $eap
    $tb = 0.0
    if ($ncLine -match "\sT=\s*([0-9.]+E[+-][0-9]+)") { $tb = [double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture) }
    $crash[$t] = @{ log = (Split-Path -Leaf $f); T = $tb; n = 0; status = "GAVE_UP" }
    $alerts += ($t + ": MASS BLOW-UP (" + $extra + ") at T=" + $tb + " -> " + $stopOut + "; run given up, results after this time are invalid; queue continues")
  }

  # ---- ERROR TERMINATION of the newest run (2026-10-04 08:07: P1r25f segmentation violation; the run
  #      sat unfinished for 2 h 15 min and the slot was idle 64 min). Retry once from the last restart
  #      file at once; a second crash at the same simulated time (+-2 us) or a 4th crash -> give up,
  #      so the queue moves on immediately.
  if ($state -eq "ERROR_TERMINATION" -and $aliveOk -and $t -notin $aliveTagsNow -and -not $NoAutoResume) {
    $logName = Split-Path -Leaf $f
    $crashT = 0.0
    if ($ncLine -match "\sT=\s*([0-9.]+E[+-][0-9]+)") { $crashT = [double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture) }
    $rec = $crash[$t]
    if (-not $rec -or $rec.log -ne $logName) {
      $n = 0; if ($rec) { $n = $rec.n }
      $same = ($rec -and $crashT -gt 0 -and $crashT -le ($rec.T + 2e-6))
      # 2026-10-07: P1r28f crashed at T=0.388, 0.400, 0.419 ms - each retry got further - and the old
      # "4th crash -> give up" rule stopped it at 82 %. Give up only when a retry made no progress
      # (same T within 2 us), or after 10 retries.
      if (($same -and $n -ge 1) -or $n -ge 10) {
        $crash[$t] = @{ log = $logName; T = $crashT; n = $n; status = "GAVE_UP" }
        $alerts += ($t + ": crashed again (" + $logName + ", T=" + $crashT + ", retries " + $n + ") -> GAVE UP, run kept as partial; queue continues")
      } else {
        $out = ""
        # 2026-10-05 05:48: restart file 0006 had the full size but the engine hit END OF FILE while
        # reading it (written while E: ran full). restart_prep cannot see that, so a crash at T=0 with
        # that message means: set aside the failed run N and run N-1 (whose restart file is bad) and
        # resume from run N-2's restart file.
        $eofRead = ($crashT -eq 0 -and (Select-String -LiteralPath $f -Pattern "END OF FILE DURING READING" -Quiet))
        if ($eofRead) {
          $decks = @(Get-ChildItem -LiteralPath $WorkDir -Filter ("PANEL4MM_" + $t + "_00*.rad") -ErrorAction SilentlyContinue |
                     Where-Object { $_.Name -match ("^PANEL4MM_" + $t + "_(\d{4})\.rad$") -and [int]$Matches[1] -ge 1 } | Sort-Object Name -Descending)
          if ($decks.Count -ge 3) {
            $bad = Join-Path $WorkDir ("corrupt_" + $t + "_" + $now.ToString("yyyyMMdd_HHmm"))
            New-Item -ItemType Directory -Force -Path $bad | Out-Null
            $moved = @()
            foreach ($d in $decks[0..1]) {
              $nn = $d.BaseName.Substring($d.BaseName.Length - 4)
              foreach ($sfx in (".rad", ".out", "_0001.rst")) {
                $p = Join-Path $WorkDir ("PANEL4MM_" + $t + "_" + $nn + $sfx)
                if (Test-Path -LiteralPath $p) { Move-Item -LiteralPath $p -Destination $bad -Force; $moved += (Split-Path -Leaf $p) }
              }
            }
            Move-Item -LiteralPath $f -Destination (Join-Path $bad ($logName -replace "\.log$", "_eof.log")) -Force
            $out = "FALLBACK: restart file unreadable (END OF FILE), moved " + ($moved -join ",") + " to " + (Split-Path -Leaf $bad) + "`n"
          }
        }
        $out = $out + (Invoke-Resume $t)    # falls back to the previous restart file when the newest is unusable
        $res = (($out -split "`n" | Where-Object { $_ -match "LAUNCHED|REFUSE|ABORT|FALLBACK|failed|Error" } | Select-Object -First 3) -join " / ")
        $stc = "RETRIED"; if ("$res" -notmatch "LAUNCHED") { $stc = "FAILED" }
        $crash[$t] = @{ log = $logName; T = $crashT; n = ($n + 1); status = $stc }
        $alerts += ($t + ": ERROR TERMINATION at T=" + $crashT + " (" + $logName + ") -> auto-retry " + ($n + 1) + ": " + "$res".Trim())
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
      $mcLock = Join-Path (Split-Path -Parent $StateFile) ".memcap.lock"
      $lockFresh = (Test-Path -LiteralPath $mcLock) -and (($now - (Get-Item -LiteralPath $mcLock).LastWriteTime).TotalSeconds -lt 180)
      if ($lockFresh) {
        $age = 1e9   # engine_mem_log.sh (fast memory cap) is restarting it right now
      }
      if ($age -lt $MemCapRstAgeMin -and $age -gt 0.5 -and -not (Test-RstComplete $t $rst[0])) {
        $age = 1e9   # newest restart file incomplete (being written / truncated): never KILL now
      }
      if ($age -lt $MemCapRstAgeMin -and $age -gt 0.5) {
        Set-Content -LiteralPath $mcLock -Value ($now.ToString("yyyy-MM-dd HH:mm:ss") + " watchdog " + $t) -Encoding ASCII
        $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        $stopOut = (& docker exec $Container bash /work/engine_ctl.sh stop $t 2>&1 | Out-String).Trim()
        $ErrorActionPreference = $eap
        $out = Invoke-Resume $t
        $res = (($out -split "`n" | Where-Object { $_ -match "LAUNCHED|REFUSE|ABORT|FALLBACK|failed|Error" } | Select-Object -First 3) -join " / ")
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
  # 2026-10-05 04:20: WorkDir is a junction to E: and only D: was checked -> E: reached 0 bytes, the
  # resume deck could not be written and P1r26f sat dead 80 min with D: showing 152 GB free.
  # Measure the drive the junction really points to.
  # 2026-10-10: the link is two levels deep (D:\Clawdbot...\work -> D:\ClawstackData\...\work -> E:) and
  # PS 5.1 shows an empty LinkType for it, so the old check stayed on D: while E: filled up (16 h idle).
  # Follow every Target until a real directory is reached.
  # Item.Target of the second hop is a stale string (D:\ClawstackData\..., which does not exist), so ask
  # Windows for the final path of the opened directory instead.
  if (-not ("FinalPath" -as [type])) {
    Add-Type -Language CSharp -TypeDefinition @"
using System; using System.Runtime.InteropServices; using System.Text; using Microsoft.Win32.SafeHandles;
public static class FinalPath {
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern SafeFileHandle CreateFileW(string n, uint a, uint s, IntPtr sa, uint c, uint f, IntPtr t);
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern uint GetFinalPathNameByHandleW(SafeFileHandle h, StringBuilder b, uint n, uint f);
  public static string Get(string p) {
    using (var h = CreateFileW(p, 0, 7, IntPtr.Zero, 3, 0x02000000, IntPtr.Zero)) {
      if (h.IsInvalid) return null;
      var sb = new StringBuilder(1024); GetFinalPathNameByHandleW(h, sb, 1024, 0);
      var r = sb.ToString(); if (r.StartsWith(@"\\?\")) r = r.Substring(4); return r; } } }
"@
  }
  $wdReal = [FinalPath]::Get($WorkDir)
  if (-not $wdReal) { throw ("cannot resolve the final path of " + $WorkDir) }
  $drv = $DiskDrive
  if ($wdReal -match "^([A-Za-z]):") { $drv = $Matches[1] }
  $freeGB = (Get-PSDrive $drv).Free / 1GB
  # Below 2x the minimum, move the restart files of finished runs (FINALIZED_<tag>, not being watched)
  # to the archive drive, one run per tick. Move, never delete.
  if ($freeGB -lt 2 * $DiskMinGB -and (Test-Path -LiteralPath $RstArchive)) {
    $fin = @(Get-ChildItem -LiteralPath $VtkDir -Filter "FINALIZED_*" -ErrorAction SilentlyContinue |
             Sort-Object LastWriteTime | ForEach-Object { $_.Name.Substring(10) } | Where-Object { $Tags -notcontains $_ })
    # 2026-10-10: also runs that were stopped / abandoned (not watched, not queued, no engine): P1r29f and
    # P1r33f kept 15 GB of restart files on E: because they never got FINALIZED.
    $queued = @()
    if (Test-Path -LiteralPath $QueueFile) { $queued = @(Get-Content -LiteralPath $QueueFile | ForEach-Object { ($_.Trim() -replace "^resume_", "") }) }
    $abandoned = @(Get-ChildItem -LiteralPath $WorkDir -File -Filter "PANEL4MM_*_0001.rst" -ErrorAction SilentlyContinue |
                   ForEach-Object { if ($_.Name -match "^PANEL4MM_([A-Za-z0-9]+)_\d{4}_0001\.rst$") { $Matches[1] } } | Select-Object -Unique |
                   Where-Object { $Tags -notcontains $_ -and $queued -notcontains $_ -and $aliveTagsNow -notcontains $_ -and $fin -notcontains $_ })
    $fin = @($fin) + @($abandoned)
    foreach ($ft in $fin) {
      $rf = @(Get-ChildItem -LiteralPath $WorkDir -File -Filter ("PANEL4MM_" + $ft + "_*.rst") -ErrorAction SilentlyContinue | Where-Object { $_.Name -match ("^PANEL4MM_" + $ft + "_\d{4}_0001\.rst$") })
      if ($rf.Count -eq 0) { continue }
      $gb = [math]::Round((($rf | Measure-Object Length -Sum).Sum) / 1GB, 1)
      try { $rf | Move-Item -Destination $RstArchive -ErrorAction Stop
            $alerts += ("DISK: " + $drv + ": free " + [math]::Round($freeGB,1) + " GB -> moved " + $rf.Count + " restart files of finished/abandoned " + $ft + " (" + $gb + " GB) to " + $RstArchive) }
      catch { $alerts += ("DISK: moving " + $ft + " restart files failed: " + $_.Exception.Message) }
      $freeGB = (Get-PSDrive $drv).Free / 1GB
      break
    }
  }
  if ($freeGB -lt $DiskMinGB) { $diskState = "DISK_LOW"; $diskExtra = ($drv + ": free " + [math]::Round($freeGB,1) + " GB < " + $DiskMinGB + " GB (WorkDir " + $wdReal + ")") }
} catch { $diskState = "CHECK_FAILED"; $diskExtra = $_.Exception.Message }
$oldDisk = "NONE"
if ($prev["DISK"]) { $oldDisk = $prev["DISK"].state }
$newState["DISK"] = @{ state = $diskState; stale = 0 }
if ($diskState -ne $oldDisk -and -not ($oldDisk -eq "NONE" -and $diskState -eq "OK")) {
  $alerts += ("DISK: " + $oldDisk + " -> " + $diskState + " " + $diskExtra)
}

# ---- persist crash bookkeeping ----
if ($crash.Count -gt 0) {
  Set-Content -LiteralPath $CrashFile -Encoding ASCII -Value ($crash.Keys | ForEach-Object { $_ + "|" + $crash[$_].log + "|" + $crash[$_].T.ToString("E6", [Globalization.CultureInfo]::InvariantCulture) + "|" + $crash[$_].n + "|" + $crash[$_].status })
}

# ---- run queue: keep the engine slots busy (a finished run must not leave a slot idle) ----
# 2026-10-01: up to $MaxEngines engines at once (user paused MechaRL so INC-188 can run 2 jobs).
if (-not $NoQueue -and (Test-Path -LiteralPath $QueueFile)) {
  $q = @(Get-Content -LiteralPath $QueueFile | ForEach-Object { $_.Trim() } | Where-Object { $_ -match "^[A-Za-z0-9_]+$" })
  $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  $anyOut = @(& docker exec $Container bash /work/engine_ctl.sh any 2>$null)
  $anyRc = $LASTEXITCODE
  $ErrorActionPreference = $eap
  $aliveTags = @($anyOut | ForEach-Object { ("$_".Trim() -split "\s+")[1] } | Where-Object { $_ } | Select-Object -Unique)
  # 2026-09-28 15:46: after a WSL shutdown no engine was alive, so the queue launched P1r21 while
  # P1r20 was only interrupted (resume pending). A watched run whose newest log has neither NORMAL nor
  # ERROR TERMINATION is unfinished.
  $unfinished = @($Tags | Where-Object { $newState[$_] -and $newState[$_].state -notin @("NORMAL_TERMINATION", "ERROR_TERMINATION", "LOG_MISSING", "MASS_BLOWUP") })
  # A run whose newest log ended in ERROR TERMINATION stays unfinished until the crash retry above has
  # either relaunched it (engine alive -> slot busy) or given up (GAVE_UP / FAILED -> finished, move on).
  # (2026-10-04: replaces the fixed 60-min hold, which only left the slot idle.)
  foreach ($tg in $Tags) {
    if ($newState[$tg] -and $newState[$tg].state -eq "ERROR_TERMINATION") {
      $cr = $crash[$tg]
      if (-not $cr -or $cr.status -eq "RETRIED") { $unfinished += $tg }
    }
  }
  # unfinished runs without a live engine are waiting for a resume: they own the next free slot
  $needResume = @($unfinished | Where-Object { $_ -notin $aliveTags })
  if ($q.Count -gt 0 -and $needResume.Count -gt 0) {
    if ($anyOut.Count -eq 0) {
      Add-Content -LiteralPath $MemCapLog -Encoding ASCII -Value ($now.ToString("yyyy-MM-dd HH:mm:ss") + " QUEUE: " + $q[0] + " held, unfinished watched run(s) without engine: " + ($needResume -join ",") + " (waiting for auto-resume)")
    }
  }
  # 2026-10-10: the slot sat idle 16 h - the queue was held by a watched run that "waited for auto-resume"
  # but could never resume (disk full), and nothing alerted. If the queue has work, no engine is alive and
  # this lasts 15 min: alert, give the blocking runs up and let the queue continue.
  $nowMin = [int]($now.ToUniversalTime() - [datetime]'1970-01-01').TotalMinutes
  if ($q.Count -gt 0 -and $anyRc -eq 0 -and $anyOut.Count -eq 0) {
    $idleSince = $nowMin; $idleAlert = "NONE"
    if ($prev["QUEUE_IDLE"]) { $idleSince = $prev["QUEUE_IDLE"].stale; $idleAlert = $prev["QUEUE_IDLE"].state }
    $idleMin = $nowMin - $idleSince
    if ($idleMin -ge 15) {
      if ($needResume.Count -gt 0) {
        foreach ($tg in $needResume) { $crash[$tg] = @{ log = "blocked"; T = 0.0; n = 0; status = "GAVE_UP" } }
        Set-Content -LiteralPath $CrashFile -Encoding ASCII -Value @($crash.Keys | ForEach-Object { $_ + "|" + $crash[$_].log + "|" + $crash[$_].T.ToString("E6", [Globalization.CultureInfo]::InvariantCulture) + "|" + $crash[$_].n + "|" + $crash[$_].status })
        if (-not $PSBoundParameters.ContainsKey("Tags")) {
          Set-Content -LiteralPath $TagsFile -Value @($Tags | Where-Object { $needResume -notcontains $_ }) -Encoding ASCII
        }
        $alerts += ("QUEUE: slot idle " + $idleMin + " min, held by " + ($needResume -join ",") + " that could not resume -> given up (re-queue as resume_<tag> if needed); queue continues")
        $needResume = @()
      }
      if ($idleAlert -ne "ALERTED" -or ($idleMin % 60) -eq 0) {
        $alerts += ("QUEUE: no engine running for " + $idleMin + " min with " + $q.Count + " run(s) queued (head " + $q[0] + ")")
        $idleAlert = "ALERTED"
      }
    }
    $newState["QUEUE_IDLE"] = @{ state = $idleAlert; stale = $idleSince }
  }

  # 2026-10-07: "resume_<tag>" in the queue resumes a run that was given up (GAVE_UP) or left partial,
  # from its newest restart file, when the slot is free; its crash record is reset and it is watched again.
  if ($q.Count -gt 0 -and $q[0] -match "^resume_([A-Za-z0-9]+)$" -and $needResume.Count -eq 0 -and $anyRc -eq 0 -and $anyOut.Count -lt $MaxEngines) {
    $rt = $Matches[1]
    $freeGB = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
    if ($freeGB -ge $QueueMinFreeGB) {
      $out = Invoke-Resume $rt
      $res = (($out -split "`n" | Where-Object { $_ -match "LAUNCHED|REFUSE|ABORT|FALLBACK|failed|Error" } | Select-Object -First 3) -join " / ")
      Set-Content -LiteralPath $QueueFile -Value ($q | Select-Object -Skip 1) -Encoding ASCII
      if ("$res" -match "LAUNCHED") {
        $crash.Remove($rt)
        # crash file was already written above this block: rewrite it without the resumed run
        Set-Content -LiteralPath $CrashFile -Encoding ASCII -Value @($crash.Keys | ForEach-Object { $_ + "|" + $crash[$_].log + "|" + $crash[$_].T.ToString("E6", [Globalization.CultureInfo]::InvariantCulture) + "|" + $crash[$_].n + "|" + $crash[$_].status })
        if (-not $PSBoundParameters.ContainsKey("Tags")) {
          $keep = @(@($Tags | Where-Object { $_ -ne $rt }) | Select-Object -Last 3) + $rt
          Set-Content -LiteralPath $TagsFile -Value $keep -Encoding ASCII
        }
      }
      $alerts += ("QUEUE: resume " + $rt + " (free RAM " + [math]::Round($freeGB,1) + " GB): " + "$res".Trim())
    }
    $q = @()   # one action per tick
  }
  if ($q.Count -gt 0 -and $needResume.Count -eq 0 -and $anyRc -eq 0 -and $anyOut.Count -lt $MaxEngines) {
    $next = $q[0]
    $deck = Join-Path $WorkDir ("PANEL4MM_" + $next + "_0000.rad")
    $startedLog = Join-Path $WorkDir ("engine_run" + $next + ".log")
    $freeGB = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
    $needGB = $QueueMinFreeGB
    if ($anyOut.Count -gt 0) { $needGB = $QueueMinFreeGB2 }
    if (-not (Test-Path -LiteralPath $deck) -or -not (Test-Path -LiteralPath (Join-Path $WorkDir ("PANEL4MM_" + $next + "_0001.rad")))) {
      $alerts += ("QUEUE: deck for " + $next + " missing in " + $WorkDir + " -> removed from queue")
      Set-Content -LiteralPath $QueueFile -Value ($q | Select-Object -Skip 1) -Encoding ASCII
    } elseif (Test-Path -LiteralPath $startedLog) {
      $alerts += ("QUEUE: " + $next + " was already started before (" + $startedLog + ") -> removed from queue, not relaunched")
      Set-Content -LiteralPath $QueueFile -Value ($q | Select-Object -Skip 1) -Encoding ASCII
    } elseif ($freeGB -lt $needGB) {
      Add-Content -LiteralPath $MemCapLog -Encoding ASCII -Value ($now.ToString("yyyy-MM-dd HH:mm:ss") + " QUEUE: " + $next + " waiting, host free RAM " + [math]::Round($freeGB,1) + " GB < " + $needGB + " (" + $anyOut.Count + " engine(s) alive)")
      if ($anyOut.Count -eq 0) {
        # no engine at all while we wait: alert once after 30 min so a human can free memory
        $since = [int]($now.ToUniversalTime() - [datetime]'1970-01-01').TotalMinutes
        if ($prev["QUEUE_RAMWAIT"]) { $since = $prev["QUEUE_RAMWAIT"].stale }
        $waited = [int]($now.ToUniversalTime() - [datetime]'1970-01-01').TotalMinutes - $since
        $st = "WAIT"
        if ($prev["QUEUE_RAMWAIT"]) { $st = $prev["QUEUE_RAMWAIT"].state }
        if ($waited -ge 30 -and $st -ne "ALERTED") {
          $alerts += ("QUEUE: " + $next + " has waited " + $waited + " min for host RAM (free " + [math]::Round($freeGB,1) + " GB < " + $needGB + " GB); the OpenRadioss slot is IDLE")
          $st = "ALERTED"
        }
        $newState["QUEUE_RAMWAIT"] = @{ state = $st; stale = $since }
      }
    } else {
      $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
      $out = (& docker exec -d -e ("TAGS=" + $next) -e ("NT=" + $ResumeThreads) $Container bash /work/chain_P1r19_21.sh 2>&1 | Out-String).Trim()
      $rc = $LASTEXITCODE
      $ErrorActionPreference = $eap
      Set-Content -LiteralPath $QueueFile -Value ($q | Select-Object -Skip 1) -Encoding ASCII
      if ($rc -eq 0) {
        # keep every running / unfinished tag watched, plus the last 2 finished ones, plus the new one
        $active = @($Tags | Where-Object { $_ -ne $next -and ($_ -in $aliveTags -or $_ -in $unfinished) })
        $done2 = @($Tags | Where-Object { $_ -ne $next -and $_ -notin $aliveTags -and $_ -notin $unfinished } | Select-Object -Last 2)
        $keep = @($done2) + @($active) + $next
        if (-not $PSBoundParameters.ContainsKey("Tags")) { Set-Content -LiteralPath $TagsFile -Value $keep -Encoding ASCII }
        $alerts += ("QUEUE: launched " + $next + " (nt=" + $ResumeThreads + ", engines alive before: " + $anyOut.Count + ", free RAM " + [math]::Round($freeGB,1) + " GB); " + ($q.Count - 1) + " left in queue")
      } else {
        $alerts += ("QUEUE: launch of " + $next + " FAILED rc=" + $rc + " " + $out)
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

# ---- set summaries: data\workspace\openradioss_report_sets.txt, one set per line "<name>: TAG TAG ...".
#      When every tag of a set is FINALIZED, send one compare_runs.py table for the whole set
#      (marker REPORTED_SET_<name> in $VtkDir). 2026-10-03: the six-order re-run ends at night. ----
$setsFile = Join-Path (Split-Path -Parent $StateFile) "openradioss_report_sets.txt"
if (-not $NoResultReport -and (Test-Path -LiteralPath $setsFile)) {
  foreach ($ln in Get-Content -LiteralPath $setsFile) {
    if ($ln -notmatch "^\s*([A-Za-z0-9_]+)\s*:\s*(.+)$") { continue }
    $setName = $Matches[1]; $setTags = @($Matches[2].Trim() -split "\s+" | Where-Object { $_ -match "^[A-Za-z0-9_]+$" })
    $rep = Join-Path $VtkDir ("REPORTED_SET_" + $setName)
    if ($setTags.Count -eq 0 -or (Test-Path -LiteralPath $rep)) { continue }
    $missing = @($setTags | Where-Object { -not (Test-Path -LiteralPath (Join-Path $VtkDir ("FINALIZED_" + $_))) })
    if ($missing.Count -gt 0) { continue }
    $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    $env:PYTHONIOENCODING = "utf-8"
    $tbl = (& $PythonExe "D:\Clawdbot_Docker_20260125\scripts\inc188_analysis\compare_runs.py" @setTags 2>&1 | Where-Object { "$_" -match "^\|" } | Out-String).Trim()
    $ErrorActionPreference = $eap
    if ($tbl) {
      $alerts += ("SET RESULT " + $setName + " (all " + $setTags.Count + " runs finalized):`n" + $tbl)
      Set-Content -LiteralPath $rep -Value ($now.ToString("yyyy-MM-dd HH:mm:ss")) -Encoding ASCII
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
$lines = foreach ($k in (@($Tags) + "DISK" + "RH_ALARM_LINES" + @($newState.Keys | Where-Object { $_ -eq "QUEUE_RAMWAIT" }))) { $k + "|" + $newState[$k].state + "|" + $newState[$k].stale }
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
