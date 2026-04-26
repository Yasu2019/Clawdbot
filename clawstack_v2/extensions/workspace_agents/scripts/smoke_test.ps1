Write-Host "Health check"
curl.exe http://127.0.0.1:18080/health
Write-Host "SQL guard check"
curl.exe -X POST http://127.0.0.1:18080/guard/sql-check -H "Content-Type: application/json" -d '{"sql":"DELETE FROM dbo.Test"}'
