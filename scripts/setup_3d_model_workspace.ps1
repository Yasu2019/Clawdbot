$ErrorActionPreference = "Stop"

$root = "E:\"
if (-not (Test-Path $root)) {
  throw "Drive E: is not available."
}

$paths = @(
  "E:\Assets\3D\Incoming\Meshy",
  "E:\Assets\3D\Incoming\DXF",
  "E:\Assets\3D\Incoming\STEP",
  "E:\Assets\3D\Incoming\STL",
  "E:\Assets\3D\Working\Blender",
  "E:\Assets\3D\Working\PortalPreview",
  "E:\Assets\3D\Working\DxfTo3D",
  "E:\Assets\3D\ExportReady\HTML",
  "E:\Assets\3D\ExportReady\GLB",
  "E:\Assets\3D\ExportReady\GLTF",
  "E:\Assets\3D\ExportReady\STL",
  "E:\Assets\3D\ExportReady\STEP",
  "E:\Assets\3D\Archive\OldVersions",
  "E:\Assets\3D\Archive\Released",
  "E:\Assets\3D\Cache\Blender",
  "E:\Assets\3D\Cache\DDC",
  "E:\Assets\3D\Cache\Temp",
  "E:\Unreal\Engine",
  "E:\Unreal\Projects",
  "E:\Unreal\Cache"
)

foreach ($path in $paths) {
  New-Item -ItemType Directory -Force -Path $path | Out-Null
}

$status = [ordered]@{
  updatedAt = (Get-Date).ToString("s")
  root = $root
  createdCount = $paths.Count
  paths = $paths
}

$statusPath = Join-Path (Split-Path -Parent $PSScriptRoot) "data\state\3d_model_workspace_status.json"
$status | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
Write-Output "3d workspace initialized"
