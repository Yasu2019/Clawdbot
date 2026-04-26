Write-Host "=== Healthcheck ==="
Write-Host "Milvus port 19530:"
Test-NetConnection 127.0.0.1 -Port 19530
Write-Host "Milvus metrics/API port 19091:"
Test-NetConnection 127.0.0.1 -Port 19091
Write-Host "Ollama port 11434:"
Test-NetConnection 127.0.0.1 -Port 11434
