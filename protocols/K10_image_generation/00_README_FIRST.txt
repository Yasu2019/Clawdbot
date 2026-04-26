K10 ZERO-COST IMAGE GENERATION PROTOCOL
=======================================

Target machine:
- GMKtec K10
- Intel Core i9-13900HK
- Intel integrated graphics
- 48 GB RAM
- Windows 11

Goal:
- Use image generation locally
- Avoid monthly fees
- Keep the setup robust and easy to recover
- Use ASCII file names and English text to reduce garbling risk

Recommended path:
1) OpenVINO GenAI + FLUX.1-schnell as the main path
2) ComfyUI Portable (CPU mode) only if you need a GUI
3) SD-Turbo only as a speed-first fallback for rough drafts

Why this path:
- It fits an Intel mini PC better than paid cloud-first tools
- It keeps recurring cost at zero after model download
- It can auto-select GPU if OpenVINO sees one, otherwise CPU

Files in this ZIP:
- 00_README_FIRST.txt              : this file
- 01_DECISION_AND_WORKFLOW.md      : what to use and when
- 02_SETUP_WINDOWS_OPENVINO.ps1    : PowerShell setup script
- 03_DEVICE_CHECK.py               : check OpenVINO devices
- 04_GENERATE_IMAGE_FLUX.py        : main image generation script
- 05_RUN_EXAMPLES.txt              : copy-paste examples
- 06_COMFYUI_PORTABLE_NOTES.md     : GUI option notes
- 07_TROUBLESHOOTING.md            : common issues and fixes
- 08_SOURCES.txt                   : source URLs used to prepare this protocol

Fast start:
1) Open Windows PowerShell
2) cd to the extracted folder
3) Run:
   powershell -ExecutionPolicy Bypass -File .\02_SETUP_WINDOWS_OPENVINO.ps1
4) Activate the venv:
   .\.venv\Scripts\Activate.ps1
5) Check devices:
   python .\03_DEVICE_CHECK.py
6) Generate a test image:
   python .\04_GENERATE_IMAGE_FLUX.py --prompt "A high quality product photo of a precision stamped metal part, studio light, realistic, detailed"

Notes:
- First model download can take a while and uses disk space
- FLUX.1-schnell is the main quality-first option in this protocol
- Use ComfyUI only if you really want a node UI
