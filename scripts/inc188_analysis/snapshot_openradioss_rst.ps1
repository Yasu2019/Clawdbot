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
  [string[]]$Tags   = @("P1r17","P1r18"),
  [int]$StableSec   = 180,
  [int]$Keep        = 2,
  [double]$MinFreeGB = 40
)

$ErrorActionPreference = "Stop"
function Log([string]$m) { Add-Content -LiteralPath $LogFile -Value ((Get-Date -Format "yyyy-MM-dd HH:mm:ss") + " " + $m) }
# any error outside the per-tag try/catch used to exit 1 silently; record where and why
trap { try { Log ("FATAL line " + $_.InvocationInfo.ScriptLineNumber + ": " + $_.Exception.Message.Split("`n")[0]) } catch {}; exit 1 }

$done = @{}
if (Test-Path -LiteralPath $StateFile) {
  foreach ($ln in Get-Content -LiteralPath $StateFile) { $p = $ln.Split("|"); if ($p.Count -ge 2) { $done[$p[0]] = $p[1] } }
}

$driveLetter = $DestRoot.Substring(0,1)
foreach ($t in $Tags) {
  try {
    # Run N writes PANEL4MM_<tag>_<N:04d>_0001.rst (run 1 = _0001_0001, after a restart _0002_0001 ...).
    # Snapshot the newest engine run; _0000_ is the starter restart and is never overwritten.
    $cand = @(Get-ChildItem -LiteralPath $WorkDir -Filter ("PANEL4MM_" + $t + "_*_0001.rst") -ErrorAction SilentlyContinue |
              Where-Object { $_.Name -match ("^PANEL4MM_" + $t + "_(\d{4})_0001\.rst$") -and $Matches[1] -ne "0000" } |
              Sort-Object Name -Descending | Select-Object -First 1)
    if ($cand.Count -eq 0) { continue }
    $src = $cand[0].FullName
    $runId = $cand[0].Name.Substring(("PANEL4MM_" + $t + "_").Length, 4)
    $fi = Get-Item -LiteralPath $src
    $age = ((Get-Date) - $fi.LastWriteTime).TotalSeconds
    if ($age -lt $StableSec) { continue }                                  # maybe being written
    $stamp = [string]$fi.LastWriteTimeUtc.Ticks
    if ($done[$t] -eq $stamp) { continue }                                 # this generation already saved

    $free = (Get-PSDrive $driveLetter).Free / 1GB
    if ($free -lt $MinFreeGB) { Log ($t + " SKIP: destination free " + [int]$free + " GB < " + $MinFreeGB + " GB"); continue }

    $dir = Join-Path $DestRoot $t
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $name = "PANEL4MM_" + $t + "_" + $runId + "_0001_" + $fi.LastWriteTime.ToString("yyyyMMdd_HHmm") + ".rst"
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
