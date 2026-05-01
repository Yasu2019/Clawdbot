[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory = $true)]
    [string]$Context,

    [string[]]$Files = @(),

    [int]$TimeoutSec = 120,

    [string]$FallbackPath = ".brv/context-tree/infrastructure/byterover_repair/safe_curate_fallback.md"
)

$ErrorActionPreference = "Stop"

function Write-FallbackMemory {
    param(
        [string]$Reason,
        [string]$ContextText,
        [string[]]$SourceFiles,
        [string]$OutputPath
    )

    $fullPath = Join-Path (Get-Location) $OutputPath
    $dir = Split-Path -Parent $fullPath
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    if (-not (Test-Path -LiteralPath $fullPath)) {
        @"
---
title: ByteRover Safe Curate Fallback
tags: [byterover, memory, fallback]
importance: 70
maturity: operational
createdAt: '2026-04-29T00:00:00+09:00'
---

# ByteRover Safe Curate Fallback

This file is an emergency local memory sink. Use it only when brv curate
fails or times out, so project decisions are not lost while ByteRover is
unhealthy.

"@ | Set-Content -LiteralPath $fullPath -Encoding UTF8
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss K"
    $fileLines = if ($SourceFiles.Count -gt 0) {
        ($SourceFiles | ForEach-Object { "- $_" }) -join "`n"
    } else {
        "- none"
    }

    $entry = @"
## $timestamp

**Fallback reason:** $Reason

**Context**

$ContextText

**Source files**

$fileLines

"@

    Add-Content -LiteralPath $fullPath -Value $entry -Encoding UTF8
    Write-Output "fallback_written=$OutputPath"
}

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

$tmpOut = [System.IO.Path]::GetTempFileName()
$tmpErr = [System.IO.Path]::GetTempFileName()
$process = $null

try {
    $argLine = "curate $(Quote-WindowsArgument $Context) --format json"
    foreach ($file in $Files) {
        $argLine += " -f $(Quote-WindowsArgument $file)"
    }

    $brvCommand = (Get-Command "brv.cmd" -ErrorAction SilentlyContinue)
    if (-not $brvCommand) {
        $brvCommand = Get-Command "brv" -ErrorAction Stop
    }

    $process = Start-Process -FilePath $brvCommand.Source -ArgumentList $argLine -NoNewWindow -PassThru -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr
    $completed = $process.WaitForExit($TimeoutSec * 1000)

    if (-not $completed) {
        Stop-ProcessTreeSafe -RootPid $process.Id
        Write-FallbackMemory -Reason "brv curate timed out after ${TimeoutSec}s" -ContextText $Context -SourceFiles $Files -OutputPath $FallbackPath
        exit 2
    }

    $stdout = Get-Content -LiteralPath $tmpOut -Raw -ErrorAction SilentlyContinue
    $stderr = Get-Content -LiteralPath $tmpErr -Raw -ErrorAction SilentlyContinue
    if ($stdout) {
        Write-Output $stdout.Trim()
    }
    if ($stderr) {
        Write-Output $stderr.Trim()
    }

    if ($process.ExitCode -ne 0 -or $stdout -match '"success"\s*:\s*false' -or $stdout -match '"status"\s*:\s*"error"') {
        $reason = "brv curate failed"
        if ($stdout -match "401") {
            $reason = "brv curate failed with HTTP 401"
        } elseif ($stderr) {
            $reason = "brv curate failed: $($stderr.Trim())"
        }
        Write-FallbackMemory -Reason $reason -ContextText $Context -SourceFiles $Files -OutputPath $FallbackPath
        exit 1
    }

    exit 0
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
