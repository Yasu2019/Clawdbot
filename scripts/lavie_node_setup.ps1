#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot NEC LAVIE setup: n8n + exec_bridge for K10 remote control.

.DESCRIPTION
  Mirrors K3 integration pattern documented in docs/K3_NODE_SETUP_PLAYBOOK.md.
  Installs to C:\clawstack_satellite by default.

.PARAMETER RepoRoot
  Path to Clawdbot_Docker_20260125 (USB or D: copy).

.PARAMETER InstallRoot
  Target install directory on LAVIE.

.PARAMETER NodeId
  Node identifier (lavie, k3, etc.) for status files.

.PARAMETER K10Ip
  K10 LAN IP (default 192.168.3.87).

.PARAMETER LanIp
  LAVIE LAN IP. Auto-detected if omitted.

.PARAMETER SkipBridge
  Skip exec_bridge workflow deployment (n8n owner not ready yet).

.EXAMPLE
  .\scripts\lavie_node_setup.ps1

.EXAMPLE
  .\scripts\lavie_node_setup.ps1 -LanIp 192.168.3.152 -SkipBridge
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$InstallRoot = "C:\clawstack_satellite",
    [string]$NodeId = "lavie",
    [string]$NodeName = "NEC LAVIE",
    [string]$K10Ip = "192.168.3.87",
    [string]$LanIp = "",
    [switch]$SkipBridge,
    [switch]$SkipFirewall
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "== $Message =="
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Get-RepoRoot {
    param([string]$Candidate)
    if ($Candidate -and (Test-Path $Candidate)) {
        return (Resolve-Path $Candidate).Path
    }
    $scriptRoot = Split-Path -Parent $PSScriptRoot
    if (Test-Path (Join-Path $scriptRoot "deploy\satellite_node\docker-compose.yml")) {
        return $scriptRoot
    }
    throw "Repo root not found. Pass -RepoRoot D:\Clawdbot_Docker_20260125"
}

function Get-LanIPv4 {
    param([string]$Preferred)
    if ($Preferred) { return $Preferred }
    $addrs = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*" -and
            $_.PrefixOrigin -ne "WellKnown"
        } |
        Sort-Object InterfaceMetric
    if (-not $addrs) {
        throw "Could not detect LAN IPv4. Pass -LanIp explicitly."
    }
    return $addrs[0].IPAddress
}

function Get-N8nPassword {
    param([string]$Root)
    $envFile = Join-Path $Root ".env"
    if (-not (Test-Path $envFile)) {
        throw "Missing $envFile (need n8n_PW=...)"
    }
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*n8n_PW=(.+)$') { return $Matches[1].Trim() }
        if ($line -match '^\s*N8N_PASSWORD=(.+)$') { return $Matches[1].Trim() }
    }
    throw "n8n_PW not found in $envFile"
}

function Ensure-Directory([string]$Path) {
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Copy-SatellitePackage {
    param(
        [string]$SourceRoot,
        [string]$TargetRoot
    )
    $src = Join-Path $SourceRoot "deploy\satellite_node"
    if (-not (Test-Path $src)) {
        throw "Missing satellite package: $src"
    }
    Ensure-Directory $TargetRoot
    robocopy $src $TargetRoot /E /XD data /NFL /NDL /NJH /NJS /NC /NS | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy failed with exit code $LASTEXITCODE"
    }
    Ensure-Directory (Join-Path $TargetRoot "data\n8n")
    Ensure-Directory (Join-Path $TargetRoot "data\work")
}

function Get-DefaultJobsRootPath {
    if (Test-Path "D:\") { return "D:\clawstack_satellite\data\work\jobs" }
    if (Test-Path "E:\") { return "E:\clawstack_satellite\data\work\jobs" }
    return "C:\clawstack_satellite\data\work\jobs"
}

function Set-SatelliteEnv {
    param(
        [string]$TargetRoot,
        [string]$Ip,
        [string]$Password,
        [string]$K10,
        [string]$Id,
        [string]$Name
    )
    $port = 5679
    $webhook = "http://${Ip}:${port}/"
    $content = @(
        "NODE_ID=$Id"
        "NODE_NAME=$Name"
        "N8N_PORT=$port"
        "N8N_HOST_BIND=0.0.0.0"
        "N8N_LAN_IP=$Ip"
        "WEBHOOK_URL=$webhook"
        "K10_IP=$K10"
        "K10_BRIDGE_URL=http://${K10}:${port}/webhook/k10_exec_bridge"
        "N8N_PASSWORD=$Password"
        "N8N_OWNER_EMAIL=y.suzuki.hk@gmail.com"
        "SATELLITE_JOBS_ROOT=$(Get-DefaultJobsRootPath)"
    ) -join "`r`n"
    Write-Utf8NoBom -Path (Join-Path $TargetRoot ".env") -Content $content
}

function Add-FirewallRule {
    param([int]$Port, [string]$NodeLabel)
    if ($SkipFirewall) {
        Write-Host "[SKIP] Firewall rule (--SkipFirewall)"
        return
    }
    $ruleName = "Clawstack satellite n8n $Port ($NodeLabel)"
    $existing = netsh advfirewall firewall show rule name="$ruleName" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Firewall rule exists: $ruleName"
        return
    }
    netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=$Port profile=Private,Domain | Out-Null
    Write-Host "[OK] Added firewall rule TCP $Port"
}

function Wait-Healthz {
    param([string]$Url, [int]$Seconds = 120)
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -eq 200) {
                Write-Host "[OK] $Url"
                return
            }
        } catch {
            Start-Sleep -Seconds 3
        }
    }
    throw "Timeout waiting for $Url"
}

function Test-ExecBridge {
    param([string]$BaseUrl, [string]$Tag)
    $body = @{ cmd = "echo ${Tag}_BRIDGE_OK" } | ConvertTo-Json
    $r = Invoke-RestMethod -Uri "$BaseUrl/webhook/exec_bridge" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
    $text = ($r | ConvertTo-Json -Compress)
    if ($text -notmatch "${Tag}_BRIDGE_OK") {
        throw "exec_bridge echo test failed: $text"
    }
    Write-Host "[OK] exec_bridge echo test"
}

function Write-NodeStatus {
    param(
        [string]$TargetRoot,
        [hashtable]$Status
    )
    $path = Join-Path $TargetRoot "node_status.json"
    Write-Utf8NoBom -Path $path -Content ($Status | ConvertTo-Json -Depth 4)
    Write-Host "[OK] Wrote $path"
}

# --- main ---
Write-Step "Resolve paths"
$repo = Get-RepoRoot -Candidate $RepoRoot
$install = $InstallRoot
Write-Host "RepoRoot   : $repo"
Write-Host "InstallRoot: $install"

Write-Step "Preflight"
$lan = Get-LanIPv4 -Preferred $LanIp
Write-Host "LAN IP     : $lan"
$n8nPw = Get-N8nPassword -Root $repo

docker version 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker not available. Start Docker Desktop, run this script from an elevated PowerShell, then retry."
}
Write-Host "[OK] Docker CLI"

Write-Step "Install satellite package"
Copy-SatellitePackage -SourceRoot $repo -TargetRoot $install
Set-SatelliteEnv -TargetRoot $install -Ip $lan -Password $n8nPw -K10 $K10Ip -Id $NodeId -Name $NodeName
Add-FirewallRule -Port 5679 -NodeLabel $NodeId

Write-Step "Docker compose up (uses build cache)"
Push-Location $install
try {
    docker compose build
    if ($LASTEXITCODE -ne 0) { throw "docker compose build failed" }
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }
} finally {
    Pop-Location
}

Write-Step "Wait for n8n"
Wait-Healthz -Url "http://${lan}:5679/healthz"

if (-not $SkipBridge) {
    Write-Step "Deploy exec_bridge workflow"
    Push-Location $repo
    try {
        $py = Get-Command python -ErrorAction SilentlyContinue
        if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
        if (-not $py) { throw "python not found for satellite_deploy_exec_bridge.py" }
        $pyExe = $py.Source
        & $pyExe (Join-Path $repo "scripts\satellite_deploy_exec_bridge.py") --base-url "http://${lan}:5679"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[WARN] Bridge deploy failed. Complete n8n owner setup at http://${lan}:5679 then re-run:"
            Write-Host "  python scripts\satellite_deploy_exec_bridge.py --base-url http://${lan}:5679"
        } else {
            Test-ExecBridge -BaseUrl "http://${lan}:5679" -Tag $NodeId.ToUpper()
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[SKIP] exec_bridge (--SkipBridge)"
}

Write-Step "Write status"
$status = @{
    node_id = $NodeId
    node_name = $NodeName
    lan_ip = $lan
    install_root = $install
    n8n_url = "http://${lan}:5679"
    exec_bridge = "http://${lan}:5679/webhook/exec_bridge"
    k10_bridge = "http://${K10Ip}:5679/webhook/k10_exec_bridge"
    updated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
}
Write-NodeStatus -TargetRoot $install -Status $status

Write-Step "K10 next steps"
Write-Host @"
1. On K10 (this repo):
   python scripts\k10_verify_satellite_node.py --node-id $NodeId --ip $lan

2. Optional K10 firewall (if not done for K3):
   powershell -ExecutionPolicy Bypass -File scripts\open_k10_n8n_firewall.ps1

3. Put IATF or other always-on apps on LAVIE under $install\data\work

4. Control LAVIE from K10:
   POST http://${lan}:5679/webhook/exec_bridge
   body: {"cmd":"docker ps"}
"@
