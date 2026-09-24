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
  [string[]]$Tags    = @("P1r17"),   # P1r13-16 finished 2026-09-24; P1r17 = round-punch penetration run (stroke 4mm)
  [int]$StaleSec     = 600,
  [string]$DiskDrive = "D",
  [double]$DiskMinGB = 10,
  [switch]$NoTelegram,
  [switch]$NoAutoResume,
  [string]$Container = "clawstack-unified-openradioss-1",
  [int]$ResumeCooldownMin = 120,
  [string]$ResumeLogFile = "D:\Clawdbot_Docker_20260125\data\workspace\openradioss_autoresume_state.txt"
)

$ErrorActionPreference = "Stop"

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
        $out = (& docker exec $Container bash /work/openradioss_restart_prep.sh $t --go 2>&1 | ForEach-Object { "$_" } | Out-String)
        if ($LASTEXITCODE -ne 0 -and -not $out) { $out = "docker exec exit " + $LASTEXITCODE }
      } catch { $out = "docker exec failed: " + $_.Exception.Message }
      $ErrorActionPreference = $eap
      $res = ($out -split "`n" | Where-Object { $_ -match "LAUNCHED|REFUSE|ABORT|failed|Error" } | Select-Object -First 2) -join " / "
      if (-not $res) { $res = ($out.Trim() -split "`n" | Select-Object -Last 1) }
      $extra = ($extra + " AUTO-RESUME: " + $res.Trim())
      $alerts += ($t + ": auto-resume attempted: " + $res.Trim())
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

# ---- persist state, then alert ----
$lines = foreach ($k in ($Tags + "DISK")) { $k + "|" + $newState[$k].state + "|" + $newState[$k].stale }
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
