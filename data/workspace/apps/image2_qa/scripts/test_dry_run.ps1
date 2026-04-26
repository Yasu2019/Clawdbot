$body = Get-Content .\samples\request_internal_audit.json -Raw
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:18789/api/image2-qa/generate" -ContentType "application/json; charset=utf-8" -Body $body | ConvertTo-Json -Depth 10
