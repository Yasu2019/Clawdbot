Write-Host "Pull embedding model for local code indexing"
try {
  ollama pull nomic-embed-text
  ollama list
} catch {
  Write-Host "Native ollama not found. If OpenClaw Docker Ollama is used, run inside/against that service instead:"
  Write-Host "docker exec -it <ollama_container_name> ollama pull nomic-embed-text"
}
