# Troubleshooting

## 1) Python not found
Fix:
- Install Python 3.12 or 3.13
- Check "Add Python to PATH" during installation

## 2) PowerShell execution policy blocks the script
Fix:
```powershell
powershell -ExecutionPolicy Bypass -File .\02_SETUP_WINDOWS_OPENVINO.ps1
```

## 3) openvino import error
Fix:
- Activate the virtual environment first
- Reinstall:
```powershell
python -m pip install --upgrade openvino-genai huggingface_hub pillow
```

## 4) Model download fails
Fix:
- Check internet access
- Retry later
- If Hugging Face is blocked on your network, use a different network
- Make sure there is enough free disk space

## 5) GPU is not detected
Fix:
- Run:
```powershell
python .\03_DEVICE_CHECK.py
```
- If only CPU appears, stay on CPU mode
- Update Intel graphics driver if you want to test GPU availability with OpenVINO

## 6) Generation is too slow
Fix:
- Stay with the default 4 steps
- Avoid very large output sizes
- Close heavy background applications
- Use the K10 on AC power
- Treat ComfyUI as optional, not as the fastest path

## 7) Memory pressure or crashes
Fix:
- Close browser tabs and other large apps
- Reboot the machine
- Keep only one generation stack open
- Do not run many custom nodes at the same time

## 8) Compatibility issue with a model
Fix:
- First try the stable package set in this ZIP
- If needed, check the model card for newer package guidance
- Only move to nightly packages if the stable path fails and you understand the tradeoff

## 9) Output quality is not good enough
Fix:
- Improve the prompt
- Add subject, style, lighting, camera, material, and background detail
- Generate several seeds and keep the best

## 10) You want a GUI after the script path works
Fix:
- Add ComfyUI Portable later
- Start with CPU mode
- Keep the script path as the fallback baseline
