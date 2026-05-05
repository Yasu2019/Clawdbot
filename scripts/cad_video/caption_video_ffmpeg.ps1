param(
  [string]$InputVideo = "outputs\pass3_final.mp4",
  [string]$OutputVideo = "outputs\captioned_final.mp4",
  [string]$Caption = "AI動画は説明用です。寸法判断は元CAD/CAEを参照。"
)

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Error "ffmpeg not found."
  exit 1
}

# Note: Japanese font path may need adjustment on your PC.
$font = "C\:/Windows/Fonts/meiryo.ttc"
$draw = "drawtext=fontfile='$font':text='$Caption':x=20:y=h-60:fontsize=24:box=1:boxborderw=8"
ffmpeg -y -i $InputVideo -vf $draw -codec:a copy $OutputVideo
Write-Host "Captioned video written to $OutputVideo"
