$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $repoRoot "scripts\telegram_fast_bridge_lib.ps1")

function JpText {
  param([int[]]$Codes)
  return (-join ([char[]]$Codes))
}

$jpEvening = JpText @(0x3053,0x3093,0x3070,0x3093,0x306F)
$jpMorning = JpText @(0x304A,0x306F,0x3088,0x3046)
$jpTomorrowSchedule = JpText @(0x660E,0x65E5,0x306E,0x4E88,0x5B9A,0x306F,0xFF1F)
$jpTodaySchedule = JpText @(0x4ECA,0x65E5,0x306E,0x4E88,0x5B9A)
$jpTomorrowWeather = JpText @(0x660E,0x65E5,0x306E,0x5929,0x6C17,0x306F,0xFF1F)
$jpRoger = JpText @(0x4E86,0x89E3)
$jpSpecifyCalendar = JpText @(0x4E88,0x5B9A,0x3092,0x78BA,0x8A8D,0x3059,0x308B,0x5BFE,0x8C61,0x3092,0x6307,0x5B9A,0x3057,0x3066,0x304F,0x3060,0x3055,0x3044,0x3002)
$jpPeriod = JpText @(0x3002)
$jpAccepted = JpText @(0x53D7,0x3051,0x4ED8,0x3051,0x307E,0x3057,0x305F,0x3002,0x7528,0x4EF6,0x3092,0x31,0x6587,0x3067,0x9001,0x3063,0x3066,0x304F,0x3060,0x3055,0x3044,0x3002)
$jpAck = JpText @(0x53D7,0x3051,0x4ED8,0x3051,0x307E,0x3057,0x305F,0x3002,0x78BA,0x8A8D,0x3057,0x307E,0x3059,0x3002)

$cases = @(
  @{ Name = "jp_evening"; Input = $jpEvening; Expected = $jpAccepted; Type = "fast" },
  @{ Name = "jp_evening_spaces"; Input = "$jpEvening    "; Expected = $jpAccepted; Type = "fast" },
  @{ Name = "jp_morning"; Input = $jpMorning; Expected = $jpAccepted; Type = "fast" },
  @{ Name = "jp_schedule_tomorrow"; Input = $jpTomorrowSchedule; Expected = "This bot does not read your calendar yet. Specify the calendar or file to check."; Type = "fast" },
  @{ Name = "jp_schedule_today"; Input = $jpTodaySchedule; Expected = "This bot does not read your calendar yet. Specify the calendar or file to check."; Type = "fast" },
  @{ Name = "jp_weather_tomorrow"; Input = $jpTomorrowWeather; Expected = "This bot does not read weather data yet. Specify the weather source if needed."; Type = "fast" },
  @{ Name = "jp_short_other"; Input = $jpRoger; Expected = $jpAccepted; Type = "fast" },
  @{ Name = "en_ping"; Input = "ping"; Expected = "pong"; Type = "fast" },
  @{ Name = "en_status"; Input = "/status"; Expected = "telegram_fast_bridge running / model=qwen3:8b"; Type = "fast" },
  @{ Name = "ollama_echo_exact"; Input = $jpEvening; Reply = $jpEvening; Expected = "Send the task."; Type = "sanitize" },
  @{ Name = "ollama_echo_with_spaces"; Input = "$jpEvening    "; Reply = " $jpEvening "; Expected = "Send the task."; Type = "sanitize" },
  @{ Name = "ollama_echo_wrapped"; Input = $jpEvening; Reply = ($jpEvening + $jpPeriod + $jpEvening); Expected = "Send the task."; Type = "sanitize" },
  @{ Name = "ollama_real_reply"; Input = $jpTomorrowSchedule; Reply = $jpSpecifyCalendar; Expected = $jpSpecifyCalendar; Type = "sanitize" },
  @{ Name = "ack_jp"; Input = $jpTomorrowSchedule; Expected = $jpAck; Type = "ack" },
  @{ Name = "ack_en"; Input = "Summarize yesterday's mail"; Expected = "Received. Checking now."; Type = "ack" }
)

$results = foreach ($case in $cases) {
  if ($case.Type -eq "fast") {
    $actual = Get-FastReply -Text $case.Input -ModelName "qwen3:8b"
  } elseif ($case.Type -eq "ack") {
    $actual = Get-AckReply -Text $case.Input
  } else {
    $actual = Sanitize-OllamaReply -InputText $case.Input -ReplyText $case.Reply
  }

  [pscustomobject]@{
    name = $case.Name
    passed = ($actual -eq $case.Expected)
    expected = $case.Expected
    actual = $actual
  }
}

$results | ConvertTo-Json -Depth 4

if (($results | Where-Object { -not $_.passed }).Count -gt 0) {
  exit 1
}
