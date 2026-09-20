# INC-188 OpenRadioss restart-file snapshotter for Windows Task Scheduler (run every 15 min).
# ASCII only on purpose: Windows PowerShell 5.1 reads BOM-less UTF-8 as ANSI.
#
# Why: the engine overwrites ONE restart file (PANEL4MM_<tag>_0001_0001.rst) every 20000 cycles.
# A crash during that write would destroy the only resume point. This keeps the last 2 generations
# of each tag on a second drive, copied only when the source has been stable and unchanged.
#
# Safety rules built in:
#  - skip a file modified in the last 180 s (may be mid-write)
#  - copy to a .part name, verify size, and verify the source mtime did not change during the copy
#  - only then rename to the final name; keep the newest 2 generations per tag
#  - refuse to copy when the destination drive has less than MinFreeGB free
param(
  [string]$WorkDir  = "D:\Clawdbot_Docker_20260125\clawstack_v2\data\work",
  [string]$DestRoot = "F:\clawstack_data\inc188\rst_snapshots",
  [string]$StateFile = "D:\Clawdbot_Docker_20260125\data\workspace\openradioss_rst_snapshot_state.txt",
  [string]$LogFile  = "D:\Clawdbot_Docker_20260125\data\workspace\openradioss_rst_snapshot_log.txt",
  [string[]]$Tags   = @("P1r13","P1r14","P1r15","P1r16"),
  [int]$StableSec   = 180,
  [int]$Keep        = 2,
  [double]$MinFreeGB = 40
)

$ErrorActionPreference = "Stop"
function Log([string]$m) { Add-Content -LiteralPath $LogFile -Value ((Get-Date -Format "yyyy-MM-dd HH:mm:ss") + " " + $m) }

$done = @{}
if (Test-Path -LiteralPath $StateFile) {
  foreach ($ln in Get-Content -LiteralPath $StateFile) { $p = $ln.Split("|"); if ($p.Count -ge 2) { $done[$p[0]] = $p[1] } }
}

$driveLetter = $DestRoot.Substring(0,1)
foreach ($t in $Tags) {
  try {
    $src = Join-Path $WorkDir ("PANEL4MM_" + $t + "_0001_0001.rst")
    if (-not (Test-Path -LiteralPath $src)) { continue }
    $fi = Get-Item -LiteralPath $src
    $age = ((Get-Date) - $fi.LastWriteTime).TotalSeconds
    if ($age -lt $StableSec) { continue }                                  # maybe being written
    $stamp = [string]$fi.LastWriteTimeUtc.Ticks
    if ($done[$t] -eq $stamp) { continue }                                 # this generation already saved

    $free = (Get-PSDrive $driveLetter).Free / 1GB
    if ($free -lt $MinFreeGB) { Log ($t + " SKIP: destination free " + [int]$free + " GB < " + $MinFreeGB + " GB"); continue }

    $dir = Join-Path $DestRoot $t
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $name = "PANEL4MM_" + $t + "_0001_0001_" + $fi.LastWriteTime.ToString("yyyyMMdd_HHmm") + ".rst"
    $part = Join-Path $dir ($name + ".part")
    $final = Join-Path $dir $name
    $size0 = $fi.Length
    Copy-Item -LiteralPath $src -Destination $part -Force
    $fi2 = Get-Item -LiteralPath $src
    $pi = Get-Item -LiteralPath $part
    if ($pi.Length -ne $size0 -or $fi2.LastWriteTimeUtc.Ticks -ne $fi.LastWriteTimeUtc.Ticks) {
      Remove-Item -LiteralPath $part -Force
      Log ($t + " DISCARDED copy: source changed during copy (size " + $pi.Length + " vs " + $size0 + "); will retry")
      continue
    }
    Move-Item -LiteralPath $part -Destination $final -Force
    $done[$t] = $stamp
    Log ($t + " SNAPSHOT " + $name + " (" + [math]::Round($size0/1GB,3) + " GB)")

    $old = @(Get-ChildItem -LiteralPath $dir -Filter "*.rst" | Sort-Object LastWriteTime -Descending | Select-Object -Skip $Keep)
    foreach ($o in $old) { Remove-Item -LiteralPath $o.FullName -Force; Log ($t + " pruned old " + $o.Name) }
  } catch {
    Log ($t + " ERROR: " + $_.Exception.Message.Split("`n")[0])
  }
}

$lines = foreach ($k in $done.Keys) { $k + "|" + $done[$k] }
if ($lines) { Set-Content -LiteralPath $StateFile -Value $lines -Encoding ASCII }
exit 0
