# IATF Video Low API Rules

Date: 2026-05-02 JST  
Scope: IATF video generation work under `D:\Clawdbot_Docker_20260125`

## Operating Rule

Use this workflow by default to keep Codex/API usage and cloud-model usage low.

1. Work on only one cut at a time.
2. Render 7 diagnostic frames first.
3. Create an MP4 only after the diagnostic frames pass visual review.
4. Report only results to Codex/user unless a blocker requires detail.
5. OpenCodeGo may be used for design ideas and motion suggestions.
6. Keep Codex/Claude usage concise: short status, result-only reports, no long analysis unless needed.
7. Do Blender iteration through local scripts and local reruns.

## Visual Gate

Before MP4 generation, the 7 diagnostic frames must confirm:

- the intended character is visible
- the evidence objects are visible and readable
- the frame is not character-only
- mouth/blink/expression status is known
- arm/body movement does not hide the evidence

## Current Default For IATF CUT Work

Preferred output set per cut:

```text
contact_sheet.jpg
7 diagnostic PNG frames
qa.json
index.html
```

MP4 is optional and should be generated only after approval.

## Cloud Model Boundary

OpenCodeGo may be used for:

- design alternatives
- motion ideas
- scene layout suggestions

DeepSeek/OpenCodeGo should not be used for:

- repeated render-loop debugging
- full long-script generation when local locked artifacts already exist
- direct final approval

## Reporting Style

Default user-facing update:

```text
1カット、7枚診断フレームで確認しました。結果: OK/NG。次: 修正/MP4化。
```

Avoid long explanations unless:

- visual QA failed
- a model/import/render blocker occurred
- the user asks for details

## Related Files

Latest handoff:

```text
D:\Clawdbot_Docker_20260125\data\workspace\HANDOFF_CODEX_20260501.md
```

Latest Bulma probe:

```text
D:\Clawdbot_Docker_20260125\data\workspace\iatf_cut005_bulma_probe\index.html
```

Current scripts:

```text
D:\Clawdbot_Docker_20260125\data\workspace\inspect_iatf_character_glbs_once.py
D:\Clawdbot_Docker_20260125\data\workspace\render_iatf_cut005_bulma_probe_once.py
D:\Clawdbot_Docker_20260125\data\workspace\render_iatf_cut005_motion_segment_once.py
```
