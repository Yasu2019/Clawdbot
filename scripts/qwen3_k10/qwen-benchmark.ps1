# qwen-benchmark.ps1
# Simple local latency benchmark for Ollama.
# Measures elapsed time for one prompt per model.

param(
    [string[]]$Models = @("qwen3:14b", "qwen2.5-coder:14b", "qwen3.6:35b-a3b")
)

$prompt = "Summarize the advantages of keeping manufacturing quality data local in 5 bullet points."

foreach ($m in $Models) {
    Write-Host "==== Testing $m ===="
    $start = Get-Date
    try {
        $result = ollama run $m $prompt
        $end = Get-Date
        $sec = ($end - $start).TotalSeconds
        Write-Host "ElapsedSeconds: $sec"
        Write-Host "OutputPreview:"
        Write-Host ($result | Out-String)
    } catch {
        Write-Host "FAILED: $m"
        Write-Host $_
    }
    Write-Host ""
}
