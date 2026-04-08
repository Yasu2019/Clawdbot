$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $repoRoot "scripts\telegram_fast_bridge_lib.ps1")

function JpText {
  param([int[]]$Codes)
  return (-join ([char[]]$Codes))
}

$jpEvening = JpText @(0x3053,0x3093,0x3070,0x3093,0x306F)
$jpTomorrowSchedule = JpText @(0x660E,0x65E5,0x306E,0x4E88,0x5B9A,0x306F,0xFF1F)
$jpTomorrowWeather = JpText @(0x660E,0x65E5,0x306E,0x5929,0x6C17,0x306F,0xFF1F)
$jpSpecifyCalendar = JpText @(0x4E88,0x5B9A,0x3092,0x78BA,0x8A8D,0x3059,0x308B,0x5BFE,0x8C61,0x3092,0x6307,0x5B9A,0x3057,0x3066,0x304F,0x3060,0x3055,0x3044,0x3002)
$jpPeriod = JpText @(0x3002)
$jpAck = "Checking now. Please wait a moment."

$cases = @(
  @{ Name = "en_ping"; Input = "ping"; Expected = "pong"; Type = "fast" },
  @{ Name = "en_status"; Input = "/status"; Expected = "telegram_fast_bridge status"; Type = "contains" },
  @{ Name = "jp_hello_goes_model"; Input = $jpEvening; Expected = $null; Type = "null" },
  @{ Name = "jp_weather_goes_model"; Input = $jpTomorrowWeather; Expected = $null; Type = "null" },
  @{ Name = "sanitize_echo_exact"; Input = $jpEvening; Reply = $jpEvening; Expected = "Send the task."; Type = "sanitize" },
  @{ Name = "sanitize_echo_wrapped"; Input = $jpEvening; Reply = ($jpEvening + $jpPeriod + $jpEvening); Expected = "Send the task."; Type = "sanitize" },
  @{ Name = "sanitize_real_reply"; Input = $jpTomorrowSchedule; Reply = $jpSpecifyCalendar; Expected = $jpSpecifyCalendar; Type = "sanitize" },
  @{ Name = "ack_en"; Input = "Summarize yesterday's mail"; Expected = $jpAck; Type = "ack" },
  @{ Name = "ack_jp"; Input = $jpTomorrowSchedule; Expected = $jpAck; Type = "ack" }
)

$results = foreach ($case in $cases) {
  if ($case.Type -eq "fast") {
    $actual = Get-FastReply -Text $case.Input -ModelName "google/gemini-2.5-flash"
    $passed = ($actual -eq $case.Expected)
  } elseif ($case.Type -eq "contains") {
    $actual = Get-FastReply -Text $case.Input -ModelName "google/gemini-2.5-flash"
    $passed = $actual -like "*$($case.Expected)*"
  } elseif ($case.Type -eq "null") {
    $actual = Get-FastReply -Text $case.Input -ModelName "google/gemini-2.5-flash"
    $passed = $null -eq $actual
  } elseif ($case.Type -eq "ack") {
    $actual = Get-AckReply -Text $case.Input
    $passed = ($actual -eq $case.Expected)
  } else {
    $actual = Sanitize-OllamaReply -InputText $case.Input -ReplyText $case.Reply
    $passed = ($actual -eq $case.Expected)
  }

  [pscustomobject]@{
    name = $case.Name
    passed = $passed
    expected = $case.Expected
    actual = $actual
  }
}

$results | ConvertTo-Json -Depth 4

if (($results | Where-Object { -not $_.passed }).Count -gt 0) {
  exit 1
}
