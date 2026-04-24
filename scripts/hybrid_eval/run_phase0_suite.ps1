param(
  [string]$Phase0Dir = "",
  [int]$PerCallTimeoutSec = 180,
  [int]$NumPredict = 48
)

$ErrorActionPreference = "Stop"

function Write-Utf8BomFile([string]$Path, [string]$Text) {
  $dir = Split-Path -Parent $Path
  if ($dir -and !(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  # Windows PowerShell 5.1: -Encoding UTF8 writes UTF-8 with BOM
  $Text | Out-File -LiteralPath $Path -Encoding UTF8
}

function Get-LatestPhase0Dir() {
  $root = "tmp/foundrylocal_phase0"
  if (!(Test-Path $root)) { return $null }
  return (Get-ChildItem -LiteralPath $root -Directory | Sort-Object Name -Descending | Select-Object -First 1).FullName
}

function Read-Json([string]$Path) {
  return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Invoke-HybridEval([string]$OllamaModel, [string]$PromptFile) {
  $tempRoot = [System.IO.Path]::GetTempPath()
  $stdoutPath = [System.IO.Path]::Combine($tempRoot, ("hybrid_eval_stdout_{0}.txt" -f ([guid]::NewGuid().ToString("N"))))
  $stderrPath = [System.IO.Path]::Combine($tempRoot, ("hybrid_eval_stderr_{0}.txt" -f ([guid]::NewGuid().ToString("N"))))

  $p = Start-Process -FilePath "python" -ArgumentList @(
    "scripts/hybrid_eval/hybrid_eval.py",
    "--ollama-model", $OllamaModel,
    "--ollama-timeout", "$PerCallTimeoutSec",
    "--num-predict", "$NumPredict",
    "--no-think",
    "--prompt-file", $PromptFile
  ) -NoNewWindow -PassThru -Wait -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath

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
  if (!$stdout) {
    throw "hybrid_eval.py produced no stdout path for $PromptFile"
  }
  return $stdout
}

if (!$Phase0Dir) {
  $Phase0Dir = Get-LatestPhase0Dir
}
if (!$Phase0Dir) { throw "Phase0Dir not found. Run scripts/hybrid_eval/setup_phase0.ps1 first." }
if (!(Test-Path $Phase0Dir)) { throw "Phase0Dir not found: $Phase0Dir" }

$preflightPath = Join-Path $Phase0Dir "preflight.json"
if (!(Test-Path $preflightPath)) { throw "Missing preflight.json: $preflightPath" }
$preflight = Read-Json $preflightPath

$ollamaModel = [string]$preflight.ollama.model
if (!$ollamaModel) { throw "Empty ollama.model in preflight.json: $preflightPath" }

$promptsDir = Join-Path $Phase0Dir "prompts"
if (!(Test-Path $promptsDir)) { throw "Missing prompts dir: $promptsDir" }

$sampleInputsPath = "scripts/hybrid_eval/sample_inputs_ja.json"
$sampleInputs = @{}
if (Test-Path $sampleInputsPath) {
  $sampleInputs = Read-Json $sampleInputsPath
}
function Get-SampleInput([object]$obj, [string]$key) {
  if (-not $obj) { return $null }
  $p = $obj.PSObject.Properties | Where-Object { $_.Name -eq $key } | Select-Object -First 1
  if ($p) { return [string]$p.Value }
  return $null
}

$promptFiles = Get-ChildItem -LiteralPath $promptsDir -Filter *.txt | Sort-Object Name
if ($promptFiles.Count -eq 0) { throw "No prompt templates found in: $promptsDir" }

$results = @()
$caseNo = 0

foreach ($pf in $promptFiles) {
  if ($pf.Name -like "06_*") { continue } # common record section is not a model prompt

  $caseNo++
  $prefix = ""
  if ($pf.Name -match '^(\d\d)_') { $prefix = $Matches[1] }

  $inputText = ""
  $sample = if ($prefix) { Get-SampleInput $sampleInputs $prefix } else { $null }
  if ($sample) {
    $inputText = $sample
  } else {
    $inputText = "<<<INPUT_HERE>>>"
  }

  $template = Get-Content -LiteralPath $pf.FullName -Raw -Encoding UTF8
  $filled = $template -replace "<<<INPUT_HERE>>>", $inputText

  $filledPath = Join-Path $Phase0Dir ("filled_" + $pf.Name)
  Write-Utf8BomFile -Path $filledPath -Text $filled

  $started = Get-Date
  $runDir = Invoke-HybridEval -OllamaModel $ollamaModel -PromptFile $filledPath
  $elapsed = (Get-Date) - $started

  $ollamaRawPath = Join-Path $runDir "ollama_raw.json"
  $ok = $false
  $outChars = 0
  $err = ""

  if (Test-Path $ollamaRawPath) {
    $raw = Read-Json $ollamaRawPath
    if ($raw.error) { $err = [string]$raw.error }
    $resp = [string]$raw.response
    $outChars = if ($resp) { $resp.Length } else { 0 }
    $ok = (-not $err) -and ($outChars -gt 0)
  } else {
    $err = "missing ollama_raw.json"
  }

  $results += [pscustomobject]@{
    case_no = $caseNo
    date = (Get-Date).ToString("yyyy-MM-dd")
    prompt_template = $pf.Name
    model = "Ollama/$ollamaModel"
    elapsed_sec = [Math]::Round($elapsed.TotalSeconds, 2)
    output_chars = $outChars
    ok = $ok
    run_dir = $runDir
    error = $err
  }
}

$resultsCsv = Join-Path $Phase0Dir "suite_results.csv"
$results | Export-Csv -LiteralPath $resultsCsv -NoTypeInformation -Encoding UTF8

$summaryPath = Join-Path $Phase0Dir "suite_summary.md"
$summary = @(
  "# Prompt Suite Results",
  "",
  "- phase0_dir: $Phase0Dir",
  "- model: Ollama/$ollamaModel",
  "- per_call_timeout_sec: $PerCallTimeoutSec",
  "- num_predict: $NumPredict",
  "- results_csv: suite_results.csv",
  "",
  "## Notes",
  "- This runner intentionally does not modify LiteLLM/OpenClaw/n8n configs.",
  "- To add Foundry comparison, run scripts/hybrid_eval/hybrid_eval.py with --foundry-cmd for the same filled_* prompt files.",
  ""
) -join "`r`n"
Write-Utf8BomFile -Path $summaryPath -Text ($summary + "`r`n")

Write-Host $resultsCsv
