[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$QueuePath = "docs/knowledge/byterover_curate_queue.jsonl",

    [string]$ArchivePath = "docs/knowledge/byterover_curate_queue_synced.jsonl",

    [int]$MaxItems = 10,

    [int]$TimeoutSec = 120,

    [int]$RetryDelayMinutes = 180
)

$ErrorActionPreference = "Stop"

function Quote-WindowsArgument {
    param([string]$Value)

    if ($null -eq $Value) {
        return '""'
    }

    $escaped = $Value -replace '\\', '\\' -replace '"', '\"'
    return '"' + $escaped + '"'
}

function Stop-ProcessTreeSafe {
    param([int]$RootPid)

    $allProcesses = Get-CimInstance Win32_Process
    $toStop = New-Object System.Collections.Generic.List[int]
    $queue = New-Object System.Collections.Generic.Queue[int]
    $queue.Enqueue($RootPid)

    while ($queue.Count -gt 0) {
        $currentPid = $queue.Dequeue()
        $toStop.Add($currentPid)
        $children = $allProcesses | Where-Object { $_.ParentProcessId -eq $currentPid }
        foreach ($child in $children) {
            $queue.Enqueue([int]$child.ProcessId)
        }
    }

    [array]::Reverse($toStop)
    foreach ($targetPid in $toStop) {
        try {
            Stop-Process -Id $targetPid -Force -ErrorAction Stop
        } catch {
            # The process may have already exited.
        }
    }
}

function Invoke-BrvCurate {
    param(
        [string]$ContextText,
        [string[]]$SourceFiles,
        [int]$TimeoutSeconds
    )

    $tmpOut = [System.IO.Path]::GetTempFileName()
    $tmpErr = [System.IO.Path]::GetTempFileName()
    $process = $null

    try {
        $argLine = "curate $(Quote-WindowsArgument $ContextText) --format json"
        $validFiles = @()
        foreach ($file in @($SourceFiles)) {
            if ($validFiles.Count -ge 5) {
                break
            }
            if (-not [string]::IsNullOrWhiteSpace($file) -and (Test-Path -LiteralPath $file)) {
                $validFiles += $file
            }
        }
        foreach ($file in $validFiles) {
            $argLine += " -f $(Quote-WindowsArgument $file)"
        }

        $brvCommand = Get-Command "brv.cmd" -ErrorAction SilentlyContinue
        if (-not $brvCommand) {
            $brvCommand = Get-Command "brv" -ErrorAction Stop
        }

        $process = Start-Process -FilePath $brvCommand.Source -ArgumentList $argLine -NoNewWindow -PassThru -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr
        $completed = $process.WaitForExit($TimeoutSeconds * 1000)

        if (-not $completed) {
            Stop-ProcessTreeSafe -RootPid $process.Id
            return [ordered]@{
                ok = $false
                reason = "timeout after ${TimeoutSeconds}s"
                stdout = ""
                stderr = ""
            }
        }

        $stdout = Get-Content -LiteralPath $tmpOut -Raw -ErrorAction SilentlyContinue
        $stderr = Get-Content -LiteralPath $tmpErr -Raw -ErrorAction SilentlyContinue
        $curateCompleted = $stdout -match '"event"\s*:\s*"completed"' -or $stdout -match '"status"\s*:\s*"completed"'
        $curateErrored = $stdout -match '"success"\s*:\s*false' -or $stdout -match '"event"\s*:\s*"error"' -or $stdout -match '"status"\s*:\s*"error"'

        if ($curateCompleted) {
            return [ordered]@{
                ok = $true
                reason = "completed"
                stdout = $stdout
                stderr = $stderr
            }
        }

        $reason = "brv curate failed"
        if ($curateErrored -and $stdout) {
            $reason = ($stdout.Trim() -replace "\s+", " ")
        } elseif ($stderr) {
            $reason = ($stderr.Trim() -replace "\s+", " ")
        } elseif ($process.ExitCode -ne 0) {
            $reason = "brv curate exit code $($process.ExitCode)"
        }

        return [ordered]@{
            ok = $false
            reason = $reason
            stdout = $stdout
            stderr = $stderr
        }
    } finally {
        foreach ($tmp in @($tmpOut, $tmpErr)) {
            for ($attempt = 0; $attempt -lt 5; $attempt++) {
                if (-not (Test-Path -LiteralPath $tmp)) {
                    break
                }
                try {
                    Remove-Item -LiteralPath $tmp -Force
                    break
                } catch {
                    Start-Sleep -Milliseconds 200
                }
            }
        }
    }
}

function ConvertTo-QueueJsonLine {
    param([object]$Item)
    return ($Item | ConvertTo-Json -Compress -Depth 10)
}

function Set-QueueProperty {
    param(
        [object]$Item,
        [string]$Name,
        [object]$Value
    )

    $Item | Add-Member -NotePropertyName $Name -NotePropertyValue $Value -Force
}

$fullQueuePath = Join-Path (Get-Location) $QueuePath
if (-not (Test-Path -LiteralPath $fullQueuePath)) {
    Write-Output "queue_missing=$QueuePath"
    exit 0
}

$archiveFullPath = Join-Path (Get-Location) $ArchivePath
$archiveDir = Split-Path -Parent $archiveFullPath
if (-not (Test-Path -LiteralPath $archiveDir)) {
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
}

$now = Get-Date
$items = New-Object System.Collections.Generic.List[object]
$invalidLines = New-Object System.Collections.Generic.List[string]

foreach ($line in Get-Content -LiteralPath $fullQueuePath -ErrorAction Stop) {
    if ([string]::IsNullOrWhiteSpace($line)) {
        continue
    }
    try {
        $items.Add(($line | ConvertFrom-Json))
    } catch {
        $invalidLines.Add($line)
    }
}

$remaining = New-Object System.Collections.Generic.List[object]
$processed = 0
$synced = 0
$failed = 0

foreach ($item in $items) {
    $status = [string]$item.status
    if ($status -and $status -ne "pending") {
        $remaining.Add($item)
        continue
    }

    $nextAttemptRaw = [string]$item.next_attempt_after
    if ($nextAttemptRaw) {
        try {
            $nextAttempt = [datetime]::Parse($nextAttemptRaw)
            if ($nextAttempt -gt $now) {
                $remaining.Add($item)
                continue
            }
        } catch {
            # Bad dates should not block a retry.
        }
    }

    if ($processed -ge $MaxItems) {
        $remaining.Add($item)
        continue
    }

    $processed += 1
    $files = @()
    if ($null -ne $item.files) {
        $files = @($item.files)
    }

    $result = Invoke-BrvCurate -ContextText ([string]$item.context) -SourceFiles $files -TimeoutSeconds $TimeoutSec
    if ($result.ok) {
        Set-QueueProperty -Item $item -Name "status" -Value "synced"
        Set-QueueProperty -Item $item -Name "synced_at" -Value ((Get-Date).ToString("o"))
        Set-QueueProperty -Item $item -Name "last_error" -Value ""
        Add-Content -LiteralPath $archiveFullPath -Value (ConvertTo-QueueJsonLine $item) -Encoding UTF8
        $synced += 1
        continue
    }

    $attempts = 0
    if ($null -ne $item.attempts) {
        $attempts = [int]$item.attempts
    }
    $attempts += 1
    Set-QueueProperty -Item $item -Name "status" -Value "pending"
    Set-QueueProperty -Item $item -Name "attempts" -Value $attempts
    Set-QueueProperty -Item $item -Name "last_error" -Value ([string]$result.reason)
    Set-QueueProperty -Item $item -Name "last_attempt_at" -Value ((Get-Date).ToString("o"))
    $delay = [Math]::Min($RetryDelayMinutes * [Math]::Max(1, $attempts), 1440)
    Set-QueueProperty -Item $item -Name "next_attempt_after" -Value ((Get-Date).AddMinutes($delay).ToString("o"))
    $remaining.Add($item)
    $failed += 1
}

$tmpQueue = [System.IO.Path]::GetTempFileName()
try {
    foreach ($badLine in $invalidLines) {
        Add-Content -LiteralPath $tmpQueue -Value $badLine -Encoding UTF8
    }
    foreach ($item in $remaining) {
        Add-Content -LiteralPath $tmpQueue -Value (ConvertTo-QueueJsonLine $item) -Encoding UTF8
    }
    Move-Item -LiteralPath $tmpQueue -Destination $fullQueuePath -Force
} finally {
    if (Test-Path -LiteralPath $tmpQueue) {
        Remove-Item -LiteralPath $tmpQueue -Force
    }
}

[ordered]@{
    queue = $QueuePath
    archive = $ArchivePath
    processed = $processed
    synced = $synced
    failed = $failed
    remaining = $remaining.Count
    invalid_lines = $invalidLines.Count
} | ConvertTo-Json -Compress
