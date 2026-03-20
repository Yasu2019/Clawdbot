$ErrorActionPreference = "Stop"

function Normalize-CompareText {
  param([string]$Text)
  if ($null -eq $Text) { return '' }
  return ([regex]::Replace($Text.Trim().ToLowerInvariant(), '\s+', ''))
}

function Get-FastReply {
  param([string]$Text, [string]$ModelName = "qwen3:8b")

  $trimmed = $Text.Trim()
  $normalized = [regex]::Replace($trimmed, '\s+', '')
  $hasNonAscii = $false
  foreach ($ch in $normalized.ToCharArray()) {
    if ([int][char]$ch -gt 127) {
      $hasNonAscii = $true
      break
    }
  }
  $shortJapaneseLike = ($normalized.Length -le 40) -and $hasNonAscii
  $jpTomorrow = (-join ([char[]](0x660E,0x65E5)))
  $jpToday = (-join ([char[]](0x4ECA,0x65E5)))
  $jpSchedule = (-join ([char[]](0x4E88,0x5B9A)))
  $jpWeather = (-join ([char[]](0x5929,0x6C17)))
  $jpMorning = (-join ([char[]](0x304A,0x306F,0x3088)))
  $jpHello = (-join ([char[]](0x3053,0x3093,0x306B,0x3061,0x306F)))
  $jpEvening = (-join ([char[]](0x3053,0x3093,0x3070,0x3093,0x306F)))
  $jpAccepted = (-join ([char[]](0x53D7,0x3051,0x4ED8,0x3051,0x307E,0x3057,0x305F,0x3002,0x7528,0x4EF6,0x3092,0x31,0x6587,0x3067,0x9001,0x3063,0x3066,0x304F,0x3060,0x3055,0x3044,0x3002)))

  if ($normalized.Contains($jpTomorrow) -and $normalized.Contains($jpSchedule)) {
    return 'This bot does not read your calendar yet. Specify the calendar or file to check.'
  }
  if ($normalized.Contains($jpToday) -and $normalized.Contains($jpSchedule)) {
    return 'This bot does not read your calendar yet. Specify the calendar or file to check.'
  }
  if (($normalized.Contains($jpToday) -or $normalized.Contains($jpTomorrow)) -and $normalized.Contains($jpWeather)) {
    return 'This bot does not read weather data yet. Specify the weather source if needed.'
  }
  if ($normalized.Contains($jpWeather)) {
    return 'This bot does not read weather data yet. Specify the weather source if needed.'
  }
  if ($normalized.StartsWith($jpMorning)) {
    return $jpAccepted
  }
  if ($normalized.StartsWith($jpHello)) {
    return $jpAccepted
  }
  if ($normalized.StartsWith($jpEvening)) {
    return $jpAccepted
  }
  if ($shortJapaneseLike) {
    return $jpAccepted
  }

  switch -Regex ($trimmed) {
    '^(?i)ping$' { return 'pong' }
    '^(?i)ohayo|^good morning' { return 'Good morning. Send the task.' }
    '^(?i)hello|^hi|^konnichiwa' { return 'Hello. Send the task.' }
    '^(?i)konbanwa|^good evening' { return 'Good evening. Send the task.' }
    'weather|forecast' { return 'This bot does not read weather data yet. Specify the weather source if needed.' }
    'schedule|plan|tomorrow|today' { return 'This bot does not read your calendar yet. Specify the calendar or file to check.' }
    '^(?i)/status$' { return "telegram_fast_bridge running / model=$ModelName" }
    default { return $null }
  }
}

function Get-AckReply {
  param([string]$Text)

  $trimmed = $Text.Trim()
  if ([string]::IsNullOrWhiteSpace($trimmed)) {
    return 'Received.'
  }

  $normalized = [regex]::Replace($trimmed, '\s+', '')
  $hasNonAscii = $false
  $jpAck = (-join ([char[]](0x53D7,0x3051,0x4ED8,0x3051,0x307E,0x3057,0x305F,0x3002,0x78BA,0x8A8D,0x3057,0x307E,0x3059,0x3002)))
  foreach ($ch in $normalized.ToCharArray()) {
    if ([int][char]$ch -gt 127) {
      $hasNonAscii = $true
      break
    }
  }

  if ($hasNonAscii) {
    return $jpAck
  }

  return 'Received. Checking now.'
}

function Sanitize-OllamaReply {
  param([string]$InputText, [string]$ReplyText)

  $trimmed = $InputText.Trim()
  $reply = $ReplyText.Trim()
  if ([string]::IsNullOrWhiteSpace($reply)) { return "Received." }

  $inputNorm = Normalize-CompareText -Text $trimmed
  $replyNorm = Normalize-CompareText -Text $reply
  if ($replyNorm -eq $inputNorm) { return "Send the task." }
  if ($inputNorm.Length -gt 0 -and $replyNorm.Contains($inputNorm)) { return "Send the task." }

  return $reply
}
