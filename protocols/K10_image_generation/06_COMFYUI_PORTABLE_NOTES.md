# ComfyUI Portable notes for the K10

## When to use ComfyUI

Use ComfyUI only if:
- you want a visual GUI
- you like node-based workflows
- you want to test prompts interactively

## Best fit on the K10

For the K10, use:
- ComfyUI Portable on Windows
- CPU launch path first

Why:
- it is easy to extract and run
- it includes an embedded Python
- CPU mode is supported

## Minimal safe approach

1. Get the Portable package from the official docs
2. Extract it with 7-Zip
3. Start with `run_cpu.bat`
4. Do not add many custom nodes at first
5. Confirm a simple workflow works before expanding

## Important notes

- Portable is easier than a complex manual setup
- The K10 can run it, but speed will not match a discrete GPU workstation
- Keep your first workflow simple
- If the main goal is zero-cost local generation, the script path in this ZIP should remain your primary method

## Suggested rule

Use ComfyUI for:
- GUI exploration
- visual workflow building
- demo sessions

Use OpenVINO script mode for:
- repeatable production runs
- easy troubleshooting
- lower setup complexity
