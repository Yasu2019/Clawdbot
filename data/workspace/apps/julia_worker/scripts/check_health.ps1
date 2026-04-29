$ErrorActionPreference = "Stop"
Write-Host "Julia Worker:"
Invoke-RestMethod http://localhost:8096/health
Write-Host "Python Bridge:"
Invoke-RestMethod http://localhost:8097/health
