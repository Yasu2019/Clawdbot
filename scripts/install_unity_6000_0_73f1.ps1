param(
    [string]$InstallerPath = "F:\UnityInstallers\6000.0.73f1\UnitySetup64-6000.0.73f1.exe",
    [string]$InstallRoot = "F:\Unity\Hub\Editor\6000.0.73f1",
    [string]$StatusPath = "D:\Clawdbot_Docker_20260125\harness_status.json"
)

$ErrorActionPreference = "Stop"
$expectedInstallerBytes = 4031619680
$expectedVersion = "6000.0.73f1"

function Write-InstallStatus {
    param(
        [string]$State,
        [string]$Detail,
        [Nullable[int]]$ExitCode = $null,
        [string]$EditorPath = "",
        [string]$EditorVersion = "",
        [Nullable[bool]]$EditorSignatureValid = $null,
        [string]$EditorSigner = ""
    )

    [ordered]@{
        task = "Install Unity 6000.0.73f1 side-by-side on F drive"
        state = $State
        installer_path = $InstallerPath
        install_root = $InstallRoot
        detail = $Detail
        installer_exit_code = $ExitCode
        editor_path = $EditorPath
        editor_version = $EditorVersion
        editor_signature_valid = $EditorSignatureValid
        editor_signer = $EditorSigner
        protected_existing_unity = "C:\Program Files\Unity\Hub\Editor\6000.3.6f1"
        updated_at = (Get-Date).ToString("o")
    } | ConvertTo-Json | Set-Content -LiteralPath $StatusPath -Encoding UTF8
}

if (-not (Test-Path -LiteralPath $InstallerPath)) {
    Write-InstallStatus -State "install_failed_missing_installer" -Detail "Verified installer is missing."
    exit 2
}

$installer = Get-Item -LiteralPath $InstallerPath
if ($installer.Length -ne $expectedInstallerBytes) {
    Write-InstallStatus -State "install_failed_installer_size" -Detail "Installer size gate failed."
    exit 3
}

if (Test-Path -LiteralPath $InstallRoot) {
    Write-InstallStatus -State "install_failed_target_exists" -Detail "Target exists; refusing to overwrite."
    exit 4
}

$parent = Split-Path -Parent $InstallRoot
New-Item -ItemType Directory -Path $parent -Force | Out-Null

Write-InstallStatus -State "installing" -Detail "Silent installer running; /D target is the final argument."
try {
    $process = Start-Process -FilePath $InstallerPath -ArgumentList @("/S", "/D=$InstallRoot") -PassThru -Wait
} catch {
    $message = $_.Exception.Message
    Write-InstallStatus -State "install_blocked_uac_or_start_failed" -Detail $message
    exit 9
}

if ($process.ExitCode -ne 0) {
    Write-InstallStatus -State "install_failed_exit_code" -Detail "Installer returned a non-zero exit code." -ExitCode $process.ExitCode
    exit 5
}

$editorPath = Join-Path $InstallRoot "Editor\Unity.exe"
if (-not (Test-Path -LiteralPath $editorPath)) {
    Write-InstallStatus -State "install_failed_editor_missing" -Detail "Installer exited successfully but Unity.exe is missing." -ExitCode $process.ExitCode
    exit 6
}

$editor = Get-Item -LiteralPath $editorPath
$editorVersion = $editor.VersionInfo.ProductVersion
$signature = Get-AuthenticodeSignature -LiteralPath $editorPath
$signer = ""
if ($null -ne $signature.SignerCertificate) {
    $signer = $signature.SignerCertificate.Subject
}
$signatureValid = ($signature.Status -eq "Valid" -and $signer -match "Unity Technologies")
$versionValid = ($editorVersion -match [regex]::Escape($expectedVersion))

if (-not $versionValid) {
    Write-InstallStatus -State "install_failed_version_gate" -Detail "Unity.exe version does not match 6000.0.73f1." -ExitCode $process.ExitCode -EditorPath $editorPath -EditorVersion $editorVersion -EditorSignatureValid $signatureValid -EditorSigner $signer
    exit 7
}
if (-not $signatureValid) {
    Write-InstallStatus -State "install_failed_signature_gate" -Detail "Unity.exe signature is not valid for Unity Technologies." -ExitCode $process.ExitCode -EditorPath $editorPath -EditorVersion $editorVersion -EditorSignatureValid $false -EditorSigner $signer
    exit 8
}

Write-InstallStatus -State "install_verified_complete" -Detail "Side-by-side Unity installation passed exit-code, executable, version, and signature gates." -ExitCode $process.ExitCode -EditorPath $editorPath -EditorVersion $editorVersion -EditorSignatureValid $true -EditorSigner $signer
exit 0
