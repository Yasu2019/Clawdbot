param(
  [string]$OutRoot = "tmp/foundrylocal_phase0",
  [string]$OllamaUrl = $(if ($env:OLLAMA_URL) { $env:OLLAMA_URL } else { "http://127.0.0.1:11434" }),
  [string]$OllamaModel = $(if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "" }),
  [int]$OllamaTimeoutSec = $(if ($env:OLLAMA_TIMEOUT) { [int]$env:OLLAMA_TIMEOUT } else { 10 }),
  [string]$FoundryCmdLine = "",
  [int]$FoundryTimeoutSec = $(if ($env:FOUNDRY_TIMEOUT) { [int]$env:FOUNDRY_TIMEOUT } else { 15 })
)

$ErrorActionPreference = "Stop"

function Write-Utf8BomFile([string]$Path, [string]$Text) {
  $dir = Split-Path -Parent $Path
  if ($dir -and !(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  # Windows PowerShell 5.1: -Encoding UTF8 writes UTF-8 with BOM
  $Text | Out-File -LiteralPath $Path -Encoding UTF8
}

function Safe-Run([scriptblock]$Block) {
  try { & $Block } catch { return $null }
}

function Try-HttpJson([string]$Url, [int]$TimeoutSec) {
  try {
    return Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec $TimeoutSec
  } catch {
    return $null
  }
}

function Get-PortFromUrl([string]$Url) {
  try {
    $u = [Uri]$Url
    if ($u.Port -gt 0) { return $u.Port }
  } catch {}
  return $null
}

function Quote-PsSingle([string]$s) {
  return "'" + ($s -replace "'", "''") + "'"
}

$runId = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = Join-Path $OutRoot $runId
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$protocolDir = "protocols/foundrylocal_complete_protocol_20260416"
$envChecklistTemplate = Join-Path $protocolDir "02_環境前提チェックリスト.csv"
$evalSheetTemplate = Join-Path $protocolDir "08_評価記録シート.csv"
$promptSetPath = Join-Path $protocolDir "07_比較試験プロンプト集.md"

$preflight = [ordered]@{
  run_id = $runId
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  ollama = [ordered]@{
    url = $OllamaUrl.TrimEnd("/")
    model = $OllamaModel
  }
  foundry = [ordered]@{
    cmdline = $FoundryCmdLine
  }
  system = [ordered]@{
    computername = $env:COMPUTERNAME
    username = $env:USERNAME
    pwsh_version = $PSVersionTable.PSVersion.ToString()
  }
}

$osInfo = Safe-Run { Get-ComputerInfo | Select-Object -Property WindowsProductName, WindowsVersion, OsVersion, WindowsBuildLabEx, CsSystemType }
if ($osInfo) {
  $preflight.system.os = $osInfo
}

$wslList = Safe-Run { (& wsl.exe -l -v 2>&1 | Out-String) -replace "`0", "" }
if ($wslList) {
  $preflight.system.wsl = @{ list = $wslList.Trim() }
}

$dockerVersion = Safe-Run { & docker version 2>&1 | Out-String }
if ($dockerVersion) {
  $preflight.system.docker = @{ version = $dockerVersion.Trim() }
}

$ollamaPort = Get-PortFromUrl $OllamaUrl
if ($ollamaPort) {
  $tnc = Safe-Run { Test-NetConnection -ComputerName 127.0.0.1 -Port $ollamaPort -WarningAction SilentlyContinue | Select-Object ComputerName, RemotePort, TcpTestSucceeded }
  if ($tnc) { $preflight.ollama.port_probe = $tnc }
}

$tags = Try-HttpJson -Url ($OllamaUrl.TrimEnd("/") + "/api/tags") -TimeoutSec $OllamaTimeoutSec
if ($tags) {
  $preflight.ollama.tags = $tags
}

$ollamaUrlTrim = $OllamaUrl.TrimEnd("/")
if (-not $OllamaModel -and $tags -and $tags.models -and $tags.models.Count -ge 1) {
  $OllamaModel = [string]$tags.models[0].name
  $preflight.ollama.model = $OllamaModel
}

$preflightPath = Join-Path $outDir "preflight.json"
Write-Utf8BomFile -Path $preflightPath -Text (ConvertTo-Json $preflight -Depth 8)

if (!(Test-Path $envChecklistTemplate)) { throw "Missing template: $envChecklistTemplate" }
$checkItems = Import-Csv -LiteralPath $envChecklistTemplate -Encoding UTF8

foreach ($row in $checkItems) {
  $category = (($row.'カテゴリ') | ForEach-Object { $_.ToString().Trim() })
  $item = (($row.'確認項目') | ForEach-Object { $_.ToString().Trim() })

  $row.'状態' = ""
  $row.'備考' = ""

  if ($category -eq "OS") {
    if ($osInfo) { $row.'状態' = "OK"; $row.'備考' = "$($osInfo.WindowsProductName) / $($osInfo.OsVersion)" } else { $row.'状態' = "TODO" }
    continue
  }
  if ($category -eq "仮想化") {
    if ($wslList) { $row.'状態' = "OK"; $row.'備考' = ($wslList -split "`r?`n" | Select-Object -First 3) -join " / " } else { $row.'状態' = "TODO" }
    continue
  }
  if ($category -eq "Ollama") {
    if ($tags) { $row.'状態' = "OK"; $row.'備考' = "tags models: " + ($tags.models.Count) } else { $row.'状態' = "NG"; $row.'備考' = "GET /api/tags failed: $ollamaUrlTrim" }
    continue
  }
  if ($category -eq "LiteLLM") {
    $row.'状態' = "TODO"
    $row.'備考' = "バックアップ対象の config パスを特定する"
    continue
  }
  if ($category -eq "OpenClaw") {
    $row.'状態' = "TODO"
    $row.'備考' = "接続先 model 名 / alias をメモする"
    continue
  }
  if ($category -eq "n8n") {
    $row.'状態' = "TODO"
    $row.'備考' = "本番フローは変更しない（比較用に複製）"
    continue
  }
  if ($category -eq "ポート") {
    $row.'状態' = "TODO"
    $row.'備考' = "Foundry の使用ポート決定後に競合確認"
    continue
  }
  if ($category -eq "モデル") {
    if ($OllamaModel) { $row.'状態' = "OK"; $row.'備考' = "Ollama: $OllamaModel / Foundry: TBD" } else { $row.'状態' = "TODO"; $row.'備考' = "OLLAMA_MODEL を決める（例: env:OLLAMA_MODEL）" }
    continue
  }
  if ($category -eq "ログ") {
    $row.'状態' = "OK"
    $row.'備考' = "run artifacts: tmp/hybrid_eval/<run_id>/"
    continue
  }
  if ($category -eq "復旧") {
    $row.'状態' = "OK"
    $row.'備考' = "Foundry 側は比較系。--foundry-cmd を外すだけで rollback"
    continue
  }
}

$envChecklistOut = Join-Path $outDir "02_環境前提チェックリスト_filled.csv"
$checkItems | Export-Csv -LiteralPath $envChecklistOut -NoTypeInformation -Encoding UTF8

if (!(Test-Path $evalSheetTemplate)) { throw "Missing template: $evalSheetTemplate" }
$evalRows = Import-Csv -LiteralPath $evalSheetTemplate -Encoding UTF8
$today = (Get-Date).ToString("yyyy-MM-dd")

foreach ($row in $evalRows) {
  $row.'日付' = $today
  if ($row.'モデル' -eq "Ollama" -and $OllamaModel) { $row.'モデル' = "Ollama/$OllamaModel" }
  if ($row.'モデル' -eq "Foundry" -and $FoundryCmdLine) { $row.'モデル' = "Foundry/$FoundryCmdLine" }
}

$evalOut = Join-Path $outDir "08_評価記録シート_filled.csv"
$evalRows | Export-Csv -LiteralPath $evalOut -NoTypeInformation -Encoding UTF8

$promptsDir = Join-Path $outDir "prompts"
New-Item -ItemType Directory -Path $promptsDir -Force | Out-Null

if (Test-Path $promptSetPath) {
  $lines = Get-Content -LiteralPath $promptSetPath -Encoding UTF8
  $currentTitle = $null
  $currentBody = @()
  $emit = {
    param([string]$title, [string[]]$body)
    if (!$title) { return }
    $safe = ($title -replace '[\\/:*?"<>|]', "_").Trim()
    $idx = ($safe -split "\.")[0].Trim()
    if (!$idx) { $idx = "prompt" }
    $file = Join-Path $promptsDir ("{0}_{1}.txt" -f $idx.PadLeft(2,'0'), ($safe -replace "^\d+\.\s*", ""))
    $text = ($body -join "`r`n").Trim() + "`r`n`r`n<<<INPUT_HERE>>>`r`n"
    Write-Utf8BomFile -Path $file -Text $text
  }

  foreach ($line in $lines) {
    if ($line -match "^\s*##\s+(.+)$") {
      & $emit $currentTitle $currentBody
      $currentTitle = $Matches[1].Trim()
      $currentBody = @()
      continue
    }
    if ($currentTitle) { $currentBody += $line }
  }
  & $emit $currentTitle $currentBody
}

$runOllamaOnly = @(
  ('$env:OLLAMA_URL = ' + (Quote-PsSingle $ollamaUrlTrim)),
  ('$env:OLLAMA_MODEL = ' + (Quote-PsSingle $OllamaModel)),
  "",
  "# 例: プロンプトファイルを指定して 1回実行",
  ('python scripts/hybrid_eval/hybrid_eval.py --ollama-model $env:OLLAMA_MODEL --prompt-file "{0}"' -f (Join-Path $promptsDir "01_短文即答.txt"))
) -join "`r`n"
$runOllamaOnly += "`r`n"
Write-Utf8BomFile -Path (Join-Path $outDir "RUN_ollama_only.ps1") -Text $runOllamaOnly

$runWithFoundry = @(
  ('$env:OLLAMA_URL = ' + (Quote-PsSingle $ollamaUrlTrim)),
  ('$env:OLLAMA_MODEL = ' + (Quote-PsSingle $OllamaModel)),
  "",
  "# Foundry 比較系コマンド例（標準入力prompt -> 標準出力result のコマンドを指定）",
  "# 例: python scripts/foundry_wrapper.py",
  '$foundryCmd = @(',
  "  # 'python', 'scripts/foundry_wrapper.py'",
  ")",
  "",
  ('python scripts/hybrid_eval/hybrid_eval.py --ollama-model $env:OLLAMA_MODEL --prompt-file "{0}" --foundry-cmd @foundryCmd' -f (Join-Path $promptsDir "01_短文即答.txt"))
) -join "`r`n"
$runWithFoundry += "`r`n"
Write-Utf8BomFile -Path (Join-Path $outDir "RUN_with_foundry.ps1") -Text $runWithFoundry

$readme = @"
# Phase 0 Preflight（Foundry Local 併用評価）

生成日時: $($preflight.created_at)
出力フォルダ: $outDir

## 生成物
- 02_環境前提チェックリスト_filled.csv（現状の自動取得 + TODO）
- 08_評価記録シート_filled.csv（今日の日付を自動反映）
- prompts/（比較プロンプト雛形 + <<<INPUT_HERE>>>）
- RUN_ollama_only.ps1（Ollama 単独テスト）
- RUN_with_foundry.ps1（Foundry 併用テストの雛形）
- preflight.json（OS/WSL/Docker/Ollama の観測ログ）

## ロールバック（最短）
- Foundry 併用を止める: RUN_with_foundry.ps1 の利用を止める / hybrid_eval 実行時に --foundry-cmd を外す
"@
Write-Utf8BomFile -Path (Join-Path $outDir "README.md") -Text $readme

Write-Host $outDir
