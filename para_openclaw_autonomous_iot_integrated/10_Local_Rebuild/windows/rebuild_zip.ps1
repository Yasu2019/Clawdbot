$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Zip = "$Root.zip"
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path $Root -DestinationPath $Zip -Force
Write-Output "ZIP regenerated: $Zip"
