\
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== K10 OpenVINO image generation setup ==="
Write-Host ""

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "Python was not found in PATH."
    Write-Host "Install Python 3.12 or 3.13, then run this script again."
    exit 1
}

Write-Host "Python found at:"
Write-Host $pythonCmd.Source
Write-Host ""

if (-not (Test-Path ".\.venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
} else {
    Write-Host "Virtual environment already exists."
}

Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing packages..."
python -m pip install --upgrade openvino-genai huggingface_hub pillow

Write-Host ""
Write-Host "Setup completed."
Write-Host ""
Write-Host "Next commands:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python .\03_DEVICE_CHECK.py"
Write-Host '  python .\04_GENERATE_IMAGE_FLUX.py --prompt "A high quality product photo of a precision stamped metal part, studio light, realistic, detailed"'
Write-Host ""
Write-Host "If a model compatibility issue happens, see 07_TROUBLESHOOTING.md"
