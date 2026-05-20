[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Repo = "",
    [string]$Branch = "",
    [string]$CommitSha = "",
    [string]$WorkflowName = "CI Fast",
    [int]$TimeoutSec = 900,
    [int]$PollSec = 20,
    [switch]$Wait
)

$ErrorActionPreference = "Stop"

function Get-RemoteRepo {
    $remote = git remote get-url origin 2>$null
    if (-not $remote) {
        throw "Could not read git remote origin. Pass -Repo owner/name."
    }

    if ($remote -match "github\.com[:/](?<owner>[^/]+)/(?<repo>[^/.]+)(\.git)?$") {
        return "$($Matches.owner)/$($Matches.repo)"
    }

    throw "Could not parse GitHub repo from origin URL: $remote"
}

function Get-CurrentBranch {
    $current = git rev-parse --abbrev-ref HEAD 2>$null
    if (-not $current) {
        throw "Could not read current git branch. Pass -Branch."
    }
    return $current.Trim()
}

function Get-CurrentCommit {
    $current = git rev-parse HEAD 2>$null
    if (-not $current) {
        throw "Could not read current git commit. Pass -CommitSha."
    }
    return $current.Trim()
}

function Invoke-GitHubApi {
    param([string]$Uri)

    $headers = @{
        "Accept" = "application/vnd.github+json"
        "User-Agent" = "Clawdbot-CI-Checker"
    }

    if ($env:GITHUB_TOKEN) {
        $headers["Authorization"] = "Bearer $env:GITHUB_TOKEN"
    }

    return Invoke-RestMethod -Headers $headers -Uri $Uri
}

if (-not $Repo) {
    $Repo = Get-RemoteRepo
}
if (-not $Branch) {
    $Branch = Get-CurrentBranch
}
if (-not $CommitSha) {
    $CommitSha = Get-CurrentCommit
}

$encodedBranch = [System.Uri]::EscapeDataString($Branch)
$deadline = (Get-Date).AddSeconds($TimeoutSec)
$latest = $null

do {
    $url = "https://api.github.com/repos/$Repo/actions/runs?branch=$encodedBranch&per_page=20"
    $runs = (Invoke-GitHubApi -Uri $url).workflow_runs
    $latest = $runs |
        Where-Object { $_.name -eq $WorkflowName -and $_.head_sha -eq $CommitSha } |
        Select-Object -First 1

    if (-not $latest) {
        Write-Output "status=pending_run repo=$Repo branch=$Branch commit=$($CommitSha.Substring(0, 7)) workflow=$WorkflowName"
    } else {
        Write-Output "status=$($latest.status) conclusion=$($latest.conclusion) run_id=$($latest.id) url=$($latest.html_url)"

        if ($latest.status -eq "completed") {
            if ($latest.conclusion -eq "success") {
                exit 0
            }
            exit 1
        }
    }

    if (-not $Wait) {
        exit 2
    }

    if ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds $PollSec
    }
} while ((Get-Date) -lt $deadline)

Write-Output "status=timeout repo=$Repo branch=$Branch commit=$($CommitSha.Substring(0, 7)) workflow=$WorkflowName"
exit 3
