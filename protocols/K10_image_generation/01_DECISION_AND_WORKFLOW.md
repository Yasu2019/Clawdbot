# Decision and workflow for the GMKtec K10

## Final recommendation

Use this priority order:

1. **OpenVINO GenAI + FLUX.1-schnell**
2. **ComfyUI Portable in CPU mode** only when you want a GUI
3. **Paid cloud tools** only as optional extras, not as the main path

## Why this is the best fit

Your machine is strong on CPU and RAM, but it is not a dedicated image-generation GPU box.
That means the best zero-recurring-cost path is a local Intel-friendly stack.

OpenVINO is the center of this protocol because it can:
- run on Intel hardware
- expose image generation pipelines
- use a simple Python API
- auto-select devices when available

FLUX.1-schnell is chosen because:
- it is strong in image quality
- it can run in only 1 to 4 steps
- it uses an Apache 2.0 license

## Practical workflow

### Mode A: best local quality
Use:
- script: `04_GENERATE_IMAGE_FLUX.py`
- model: `OpenVINO/FLUX.1-schnell-fp16-ov`

Recommended settings:
- steps: 4
- guidance_scale: 0.0
- size: default unless you really need bigger images

Use this for:
- product images
- concept art
- marketing mockups
- realistic scene creation

### Mode B: GUI mode
Use:
- ComfyUI Portable
- CPU mode on the K10

Use this only if:
- you want a visual workflow
- you want drag-and-drop prompt testing
- you accept slower speed than a discrete GPU system

### Mode C: optional cloud testing
Use cloud tools only when:
- you want a quick comparison
- you want a specific proprietary look
- you accept non-zero future cost

Do not make cloud tools your main workflow if your goal is zero recurring cost.

## Recommended operating style

1. Start with local OpenVINO
2. Keep prompts and outputs in a local project folder
3. Do not overcomplicate the first setup
4. Add ComfyUI only after the script path works
5. If you later add a discrete GPU, you can re-evaluate the stack

## Suggested folders

```text
D:\AI_ImageGen\
  project_01\
  models\
  outputs\
  prompts\
  logs\
```

## Model policy for this protocol

Main:
- `OpenVINO/FLUX.1-schnell-fp16-ov`

Optional later:
- SD-Turbo or other lighter models for rough drafts
- more advanced pipelines only after the basic path is stable

## What not to do first

Avoid this at the beginning:
- very large SDXL pipelines
- too many custom nodes
- mixing many launchers at once
- assuming GUI is required from day one

Keep the first success path simple and repeatable.
