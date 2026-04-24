param(
  [string]$Phase0Dir = "",
  [int]$PerCallTimeoutSec = 240,
  [int]$NumPredict = 128,
  [string]$FoundryBaseUrlV1 = "",
  [string]$FoundryModel = ""
)

$ErrorActionPreference = "Stop"

function Get-LatestPhase0Dir() {
  $root = "tmp/foundrylocal_phase0"
  if (!(Test-Path $root)) { return $null }
  return (Get-ChildItem -LiteralPath $root -Directory | Sort-Object Name -Descending | Select-Object -First 1).FullName
}

function Read-Json([string]$Path) {
  return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Try-GetJson([string]$Url, [int]$TimeoutSec) {
  try {
    return Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec $TimeoutSec
  } catch {
    return $null
  }
}

function Write-Utf8BomFile([string]$Path, [string]$Text) {
  $dir = Split-Path -Parent $Path
  if ($dir -and !(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  $Text | Out-File -LiteralPath $Path -Encoding UTF8
}

function Invoke-Compare([string]$OllamaModel, [string]$PromptFile, [string]$FoundryV1, [string]$FoundryModelId) {
  $tempRoot = [System.IO.Path]::GetTempPath()
  $stdoutPath = [System.IO.Path]::Combine($tempRoot, ("hybrid_eval_stdout_{0}.txt" -f ([guid]::NewGuid().ToString("N"))))
  $stderrPath = [System.IO.Path]::Combine($tempRoot, ("hybrid_eval_stderr_{0}.txt" -f ([guid]::NewGuid().ToString("N"))))

  $foundryCmd = @(
    "python",
    "scripts/hybrid_eval/foundry_openai_compat.py",
    "--base-url", $FoundryV1,
    "--model", $FoundryModelId
  )

  $args = @(
    "scripts/hybrid_eval/hybrid_eval.py",
    "--ollama-model", $OllamaModel,
    "--ollama-timeout", "$PerCallTimeoutSec",
    "--num-predict", "$NumPredict",
    "--no-think",
    "--prompt-file", $PromptFile,
    "--foundry-timeout", "$PerCallTimeoutSec",
    "--foundry-cmd"
  ) + $foundryCmd

  $p = Start-Process -FilePath "python" -ArgumentList $args -NoNewWindow -PassThru -Wait -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath

  $stdout = ""
  if (Test-Path $stdoutPath) {
    $raw = Get-Content -LiteralPath $stdoutPath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    $stdout = if ($raw) { $raw.Trim() } else { "" }
  }
  $stderr = ""
  if (Test-Path $stderrPath) {
    $raw = Get-Content -LiteralPath $stderrPath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    $stderr = if ($raw) { $raw.Trim() } else { "" }
  }

  Remove-Item -LiteralPath $stdoutPath -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue

  if ($p.ExitCode -ne 0) {
    throw "hybrid_eval.py failed (exit=$($p.ExitCode)) for $PromptFile`n$stderr"
  }
  return $stdout
}

if (!$Phase0Dir) { $Phase0Dir = Get-LatestPhase0Dir }
if (!$Phase0Dir) { throw "Phase0Dir not found. Run scripts/hybrid_eval/setup_phase0.ps1 first." }
if (!(Test-Path $Phase0Dir)) { throw "Phase0Dir not found: $Phase0Dir" }

$preflightPath = Join-Path $Phase0Dir "preflight.json"
if (!(Test-Path $preflightPath)) { throw "Missing preflight.json: $preflightPath" }
$preflight = Read-Json $preflightPath
$ollamaModel = [string]$preflight.ollama.model
if (!$ollamaModel) { throw "Empty ollama.model in preflight.json: $preflightPath" }

if (!$FoundryBaseUrlV1) {
  $disc = "tmp/foundrylocal_phase0/openai_compat_discovery.json"
  if (Test-Path $disc) {
    $d = Read-Json $disc
    $hit = $d.results | Where-Object { $_.models_ok } | Select-Object -First 1
    if ($hit) { $FoundryBaseUrlV1 = [string]$hit.v1 }
  }
}

if (!$FoundryBaseUrlV1) {
  $blocked = Join-Path $Phase0Dir "foundry_blocked.md"
  Write-Utf8BomFile -Path $blocked -Text ("# Foundry compare blocked`r`n`r`nNo OpenAI-compatible endpoint found. Start Foundry Local, then rerun:`r`n`r`n- powershell -NoProfile -ExecutionPolicy Bypass -File scripts/hybrid_eval/discover_openai_compat_endpoints.ps1`r`n- powershell -NoProfile -ExecutionPolicy Bypass -File scripts/hybrid_eval/run_foundry_compare_suite.ps1`r`n")
  Write-Host $blocked
  exit 2
}

if (!$FoundryModel) {
  $models = Try-GetJson -Url ($FoundryBaseUrlV1.TrimEnd("/") + "/models") -TimeoutSec 5
  if ($models -and $models.data -and $models.data.Count -ge 1) {
    $FoundryModel = [string]$models.data[0].id
  }
}

if (!$FoundryModel) {
  $blocked = Join-Path $Phase0Dir "foundry_blocked.md"
  Write-Utf8BomFile -Path $blocked -Text ("# Foundry compare blocked`r`n`r`nFoundry endpoint found but model list is unavailable.`r`n- base_url_v1: $FoundryBaseUrlV1`r`n")
  Write-Host $blocked
  exit 2
}

$filled = Get-ChildItem -LiteralPath $Phase0Dir -Filter "filled_*.txt" | Sort-Object Name | Where-Object { $_.Name -notlike "filled_06_*" }
if ($filled.Count -eq 0) { throw "No filled prompt files found in: $Phase0Dir" }

$results = @()
$i = 0
foreach ($f in $filled) {
  $i++
  $started = Get-Date
  $runDir = Invoke-Compare -OllamaModel $ollamaModel -PromptFile $f.FullName -FoundryV1 $FoundryBaseUrlV1 -FoundryModelId $FoundryModel
  $elapsed = (Get-Date) - $started

  $ollamaRaw = Join-Path $runDir "ollama_raw.json"
  $foundryRaw = Join-Path $runDir "foundry_raw.json"

  $oChars = 0
  $fChars = 0
  $err = ""

  if (Test-Path $ollamaRaw) {
    $o = Read-Json $ollamaRaw
    $oChars = ([string]$o.response).Length
    if ($o.error) { $err = "ollama: " + [string]$o.error }
  }
  if (Test-Path $foundryRaw) {
    $fr = Read-Json $foundryRaw
    $fChars = ([string]$fr.stdout).Length
    if ($fr.error) { $err = ($err + " / foundry: " + [string]$fr.error).Trim(" /") }
  }

  $results += [pscustomobject]@{
    case_no = $i
    date = (Get-Date).ToString("yyyy-MM-dd")
    prompt_file = $f.Name
    ollama_model = "Ollama/$ollamaModel"
    foundry = "Foundry/$FoundryModel"
    elapsed_sec = [Math]::Round($elapsed.TotalSeconds, 2)
    ollama_chars = $oChars
    foundry_chars = $fChars
    run_dir = $runDir
    error = $err
  }
}

$outCsv = Join-Path $Phase0Dir "compare_results.csv"
$results | Export-Csv -LiteralPath $outCsv -NoTypeInformation -Encoding UTF8
Write-Host $outCsv
