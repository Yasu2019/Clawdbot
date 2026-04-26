# Open official LTspice download page.
# This script does not download or redistribute LTspice.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$url = 'https://www.analog.com/jp/resources/design-tools-and-calculators/ltspice-simulator.html'
Write-Host 'Analog Devices LTspice official download pageを開きます:' -ForegroundColor Cyan
Write-Host $url
Start-Process $url
Write-Host ''
Write-Host 'Windows 10/11 64bit版をダウンロードし、通常インストールしてください。' -ForegroundColor Yellow
Write-Host 'インストール後、02_check_ltspice_cli.ps1 を実行してください。'
