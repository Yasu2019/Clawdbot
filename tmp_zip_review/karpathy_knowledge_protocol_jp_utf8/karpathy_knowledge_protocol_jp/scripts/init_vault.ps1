\
$root = "D:\KnowledgeVault"

$dirs = @(
  "$root\raw\web",
  "$root\raw\pdf",
  "$root\raw\papers",
  "$root\raw\internal",
  "$root\raw\images",
  "$root\processed\summaries",
  "$root\processed\indexes",
  "$root\processed\entities",
  "$root\processed\relations",
  "$root\wiki\topics",
  "$root\wiki\qa",
  "$root\wiki\projects",
  "$root\wiki\glossary",
  "$root\wiki\decision_logs",
  "$root\inbox",
  "$root\archive",
  "$root\prompts",
  "$root\scripts",
  "$root\config"
)

foreach ($dir in $dirs) {
  New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

Write-Host "KnowledgeVault folders created at $root"
