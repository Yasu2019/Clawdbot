# Encode Zaku walk frames to MP4
# Usage: .\zaku_walk_encode.ps1

$framesDir = "D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\output\zaku_walk_origin\frames"
$outDir = "D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\output\zaku_walk_origin"
$outFile = "$outDir\zaku_walk_origin.mp4"

Write-Host "Encoding frames from: $framesDir"
Write-Host "Output: $outFile"

# Check frame count
$frames = Get-ChildItem "$framesDir\walk_*.png" -ErrorAction SilentlyContinue
Write-Host "Found $($frames.Count) frames"

if ($frames.Count -eq 0) {
    Write-Host "ERROR: No frames found!"
    exit 1
}

# Encode with ffmpeg - 24fps, H.264, high quality
& ffmpeg -y -framerate 24 `
    -i "$framesDir\walk_%04d.png" `
    -c:v libx264 -crf 18 -preset slow `
    -pix_fmt yuv420p `
    -vf "scale=1080:1920" `
    "$outFile"

if ($LASTEXITCODE -eq 0) {
    $size = (Get-Item $outFile).Length / 1MB
    Write-Host "SUCCESS: $outFile ($([math]::Round($size, 1)) MB)"
} else {
    Write-Host "ERROR: ffmpeg failed with exit code $LASTEXITCODE"
}
