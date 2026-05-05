param(
  [string]$InputVideo = "input\guide.mp4",
  [string]$OutputDir = "outputs\frames",
  [int]$Fps = 12
)

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Error "ffmpeg not found. Install or add to PATH."
  exit 1
}
ffmpeg -y -i $InputVideo -vf "fps=$Fps" "$OutputDir\frame_%05d.png"
Write-Host "Frames written to $OutputDir"
