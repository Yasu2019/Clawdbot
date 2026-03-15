$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot "data\state\telegram_fast"
$statusFile = Join-Path $stateDir "harness_status.json"
$offsetFile = Join-Path $stateDir "offset.json"
$pidFile = Join-Path $stateDir "bridge.pid"
$configFile = Join-Path $repoRoot "data\state\openclaw.json"
$ollamaUrl = if ($env:OLLAMA_URL) { $env:OLLAMA_URL.TrimEnd("/") } else { "http://127.0.0.1:11434" }
$ollamaModel = if ($env:TELEGRAM_FAST_MODEL) { $env:TELEGRAM_FAST_MODEL } else { "qwen3:8b" }

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

function Write-Status {
  param(
    [string]$State,
    [hashtable]$Extra = @{}
  )

  $payload = @{
    service = "telegram_fast_bridge"
    updatedAt = (Get-Date).ToString("o")
    pid = $PID
    state = $State
  }

  foreach ($k in $Extra.Keys) {
    $payload[$k] = $Extra[$k]
  }

  $payload | ConvertTo-Json -Depth 6 | Set-Content -Path $statusFile -Encoding UTF8
}

function Load-Offset {
  if (-not (Test-Path $offsetFile)) { return $null }
  try {
    $obj = Get-Content $offsetFile -Raw | ConvertFrom-Json
    return [int64]$obj.lastUpdateId
  } catch {
    return $null
  }
}

function Save-Offset {
  param([int64]$UpdateId)

  @{
    version = 1
    lastUpdateId = $UpdateId
    updatedAt = (Get-Date).ToString("o")
  } | ConvertTo-Json -Depth 4 | Set-Content -Path $offsetFile -Encoding UTF8
}

function Acquire-Lock {
  if (Test-Path $pidFile) {
    try {
      $existing = [int](Get-Content $pidFile -Raw)
    } catch {
      $existing = 0
    }

    if ($existing -gt 0 -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)) {
      Write-Status -State "already_running" -Extra @{ existingPid = $existing }
      exit 0
    }
  }

  Set-Content -Path $pidFile -Value $PID -Encoding ascii
}

function Release-Lock {
  if (-not (Test-Path $pidFile)) { return }

  try {
    $existing = [int](Get-Content $pidFile -Raw)
    if ($existing -eq $PID) {
      Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
  } catch {
  }
}

function Send-TelegramMessage {
  param(
    [string]$BotToken,
    [string]$ChatId,
    [string]$Text,
    [int]$ReplyToMessageId = 0
  )

  $body = @{
    chat_id = $ChatId
    text = $Text
  }
  if ($ReplyToMessageId -gt 0) {
    $body["reply_to_message_id"] = "$ReplyToMessageId"
  }

  Invoke-RestMethod `
    -Method Post `
    -Uri "https://api.telegram.org/bot$BotToken/sendMessage" `
    -Body $body `
    -TimeoutSec 20 | Out-Null
}

function Get-TelegramUpdates {
  param(
    [string]$BotToken,
    [Nullable[Int64]]$Offset
  )

  $query = "timeout=20&allowed_updates=%5B%22message%22%5D"
  if ($null -ne $Offset) {
    $query += "&offset=$([string]($Offset + 1))"
  }

  Invoke-RestMethod `
    -Method Get `
    -Uri "https://api.telegram.org/bot$BotToken/getUpdates?$query" `
    -TimeoutSec 30
}

function Get-FastReply {
  param([string]$Text)

  $trimmed = $Text.Trim()
  switch -Regex ($trimmed) {
    '^(?i)ping$' { return 'pong' }
    '^おはよ' { return 'おはようございます。要件を送ってください。' }
    '^こんにちは' { return 'こんにちは。要件を送ってください。' }
    '^こんばんは' { return 'こんばんは。要件を送ってください。' }
    '明日.*予定|予定.*明日' { return 'この bot は予定表をまだ読んでいません。確認対象のカレンダーやファイルを指定してください。' }
    '今日.*予定|予定.*今日' { return 'この bot は予定表をまだ読んでいません。確認対象のカレンダーやファイルを指定してください。' }
    '^(?i)ohayo|^good morning' { return 'Good morning. Send the task.' }
    '^(?i)hello|^hi|^konnichiwa' { return 'Hello. Send the task.' }
    '^(?i)konbanwa|^good evening' { return 'Good evening. Send the task.' }
    'schedule|plan|tomorrow' { return 'This bot does not read your calendar yet. Specify the file or calendar to check.' }
    '^(?i)/status$' { return "telegram_fast_bridge running / model=$ollamaModel" }
    default { return $null }
  }
}

function Invoke-OllamaReply {
  param([string]$Text)

  $trimmed = $Text.Trim()
  if ([string]::IsNullOrWhiteSpace($trimmed)) {
    return "Received."
  }

  $prompt = @(
    "You are a Telegram work assistant."
    "Reply in the same language as the user."
    "Keep the answer short and direct."
    "Do not use preamble."
    ""
    "User:"
    $trimmed
  ) -join "`n"

  $payload = @{
    model = $ollamaModel
    prompt = $prompt
    stream = $false
    options = @{
      temperature = 0.2
      num_predict = 120
      num_ctx = 2048
    }
  } | ConvertTo-Json -Depth 6

  try {
    $response = Invoke-RestMethod `
      -Method Post `
      -Uri "$ollamaUrl/api/generate" `
      -ContentType "application/json" `
      -Body $payload `
      -TimeoutSec 45

    $reply = "$($response.response)".Trim()
    if ([string]::IsNullOrWhiteSpace($reply)) {
      return "Received."
    }
    return $reply
  } catch {
    return "Received. Please send the task in one short sentence."
  }
}

try {
  Acquire-Lock

  $cfg = Get-Content $configFile -Raw | ConvertFrom-Json
  $botToken = $cfg.channels.telegram.botToken
  $allowedChatIds = @($cfg.channels.telegram.allowFrom | ForEach-Object { "$_" })
  if (-not $botToken -or $allowedChatIds.Count -eq 0) {
    Write-Status -State "config_error" -Extra @{ model = $ollamaModel }
    exit 1
  }

  $offset = Load-Offset
  Write-Status -State "starting" -Extra @{ lastUpdateId = $offset; model = $ollamaModel }

  while ($true) {
    $response = Get-TelegramUpdates -BotToken $botToken -Offset $offset
    $updates = @($response.result)

    if ($updates.Count -eq 0) {
      Write-Status -State "idle" -Extra @{ lastUpdateId = $offset; model = $ollamaModel }
      continue
    }

    foreach ($update in $updates) {
      $updateId = [int64]$update.update_id
      $message = $update.message
      $chatId = "$($message.chat.id)"
      $text = "$($message.text)"
      $messageId = [int]$message.message_id

      if ($allowedChatIds -notcontains $chatId) {
        $offset = $updateId
        Save-Offset -UpdateId $offset
        Write-Status -State "ignored" -Extra @{
          lastUpdateId = $offset
          lastChatId = $chatId
          model = $ollamaModel
        }
        continue
      }

      $reply = Get-FastReply -Text $text
      if ($null -eq $reply) {
        Write-Status -State "generating" -Extra @{
          lastUpdateId = $updateId
          lastChatId = $chatId
          lastMessage = $text
          model = $ollamaModel
        }
        $reply = Invoke-OllamaReply -Text $text
      }

      Send-TelegramMessage -BotToken $botToken -ChatId $chatId -Text $reply -ReplyToMessageId $messageId
      $offset = $updateId
      Save-Offset -UpdateId $offset
      Write-Status -State "replied" -Extra @{
        lastUpdateId = $offset
        lastChatId = $chatId
        lastMessage = $text
        lastReply = $reply
        model = $ollamaModel
      }
    }
  }
} catch {
  Write-Status -State "error" -Extra @{
    lastError = $_.Exception.Message
    model = $ollamaModel
  }
  throw
} finally {
  Release-Lock
}
