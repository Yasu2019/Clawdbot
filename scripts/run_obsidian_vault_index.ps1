$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
python data\workspace\obsidian_vault_manager.py build-index
