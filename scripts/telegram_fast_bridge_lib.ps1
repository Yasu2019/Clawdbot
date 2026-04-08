$ErrorActionPreference = "Stop"

function Normalize-CompareText {
  param([string]$Text)
  if ($null -eq $Text) { return '' }
  return ([regex]::Replace($Text.Trim().ToLowerInvariant(), '\s+', ''))
}

function Get-FastReply {
  param([string]$Text, [string]$ModelName = "google/gemini-2.5-flash")

  $trimmed = $Text.Trim()
  if ([string]::IsNullOrWhiteSpace($trimmed)) {
    return 'Please send a message.'
  }

  switch -Regex ($trimmed) {
    '^(?i:ping)$' { return 'pong' }
    '^(?i:/status)$' {
      return @(
        'telegram_fast_bridge status'
        "reply_model=$ModelName"
        'reply_backend=litellm-openai'
        'router=commands-local_context-aware'
        'task_search=sqlite tasks-context'
        'email_search=sqlite email context'
        'telegram_path=general-direct-model'
      ) -join "`n"
    }
    default { return $null }
  }
}

function Get-AckReply {
  param([string]$Text)
  return 'Checking now. Please wait a moment.'
}

function Sanitize-OllamaReply {
  param([string]$InputText, [string]$ReplyText)

  $inputNorm = Normalize-CompareText -Text $InputText
  $reply = $ReplyText.Trim()
  $replyNorm = Normalize-CompareText -Text $reply

  if ([string]::IsNullOrWhiteSpace($reply)) {
    return 'Could not generate a reply.'
  }
  if (($replyNorm -eq 'received') -or ($replyNorm -eq 'received.')) {
    return 'Please send a more specific request.'
  }
  if ($inputNorm.Length -gt 0 -and (($replyNorm -eq $inputNorm) -or $replyNorm.Contains($inputNorm))) {
    return 'Send the task.'
  }

  return $reply
}
