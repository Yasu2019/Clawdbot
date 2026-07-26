param(
    [string]$InstallerPath = "F:\UnityInstallers\6000.0.73f1\UnitySetup64-6000.0.73f1.exe",
    [string]$StatusPath = "D:\Clawdbot_Docker_20260125\harness_status.json"
)

$ErrorActionPreference = "Stop"
$expectedBytes = 4031619680
$downloadUrl = "https://download.unity3d.com/download_unity/a166abc3bf0e/Windows64EditorInstaller/UnitySetup64-6000.0.73f1.exe"
$noGrowthCount = 0

function Write-HarnessStatus {
    param(
        [string]$State,
        [long]$Bytes,
        [int]$NoGrowth,
        [string]$Detail = "",
        [Nullable[bool]]$SignatureValid = $null,
        [string]$Signer = ""
    )

    $payload = [ordered]@{
        task = "Unity 6000.0.73f1 installer download for commercial heroine integration"
        state = $State
        path = $InstallerPath
        bytes = $Bytes
        expected_bytes = $expectedBytes
        percent = [math]::Round(100.0 * $Bytes / $expectedBytes, 2)
        no_growth_count = $NoGrowth
        detail = $Detail
        signature_valid = $SignatureValid
        signer = $Signer
        unrelated_rl_training_preserved = $true
        updated_at = (Get-Date).ToString("o")
    }
    $payload | ConvertTo-Json | Set-Content -LiteralPath $StatusPath -Encoding UTF8
}

if (-not (Test-Path -LiteralPath $InstallerPath)) {
    Write-HarnessStatus -State "failed_missing_partial" -Bytes 0 -NoGrowth 0 -Detail "Partial installer not found."
    exit 2
}

while ($true) {
    $before = (Get-Item -LiteralPath $InstallerPath).Length
    if ($before -gt $expectedBytes) {
        Write-HarnessStatus -State "failed_size_overflow" -Bytes $before -NoGrowth $noGrowthCount -Detail "File is larger than the official expected size."
        exit 3
    }
    if ($before -eq $expectedBytes) {
        break
    }

    Write-HarnessStatus -State "downloading_on_f_drive" -Bytes $before -NoGrowth $noGrowthCount -Detail "Starting 25-second Range chunk with curl retry disabled."
    & curl.exe -L --fail --continue-at - --retry 0 --max-time 25 -o $InstallerPath $downloadUrl
    $curlExit = $LASTEXITCODE
    $after = (Get-Item -LiteralPath $InstallerPath).Length

    if ($after -gt $before) {
        $noGrowthCount = 0
    } else {
        $noGrowthCount++
    }

    Write-HarnessStatus -State "chunk_complete" -Bytes $after -NoGrowth $noGrowthCount -Detail "curl exit code $curlExit; added $($after - $before) bytes."

    if ($after -gt $expectedBytes) {
        Write-HarnessStatus -State "failed_size_overflow" -Bytes $after -NoGrowth $noGrowthCount -Detail "File is larger than the official expected size."
        exit 4
    }
    if ($noGrowthCount -ge 3) {
        Write-HarnessStatus -State "stopped_three_no_growth_chunks" -Bytes $after -NoGrowth $noGrowthCount -Detail "Stopped after three consecutive chunks with zero byte growth."
        exit 5
    }
}

$finalBytes = (Get-Item -LiteralPath $InstallerPath).Length
$signature = Get-AuthenticodeSignature -LiteralPath $InstallerPath
$signer = ""
if ($null -ne $signature.SignerCertificate) {
    $signer = $signature.SignerCertificate.Subject
}
$signatureValid = ($signature.Status -eq "Valid" -and $signer -match "Unity Technologies")

if (-not $signatureValid) {
    Write-HarnessStatus -State "failed_signature_gate" -Bytes $finalBytes -NoGrowth $noGrowthCount -Detail "Authenticode status: $($signature.Status)." -SignatureValid $false -Signer $signer
    exit 6
}

Write-HarnessStatus -State "verified_complete" -Bytes $finalBytes -NoGrowth 0 -Detail "Exact size and Unity Technologies Authenticode signature verified." -SignatureValid $true -Signer $signer
exit 0
