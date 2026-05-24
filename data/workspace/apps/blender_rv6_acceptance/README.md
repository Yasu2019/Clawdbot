# Mini PC Blender+RV6 Acceptance Harness Full v2

目的:
UE5を無理に導入せず、現在のミニPC環境で安定しやすい **Blender + RV6 + ESRGAN NCNN Vulkan** を中心に、
リアルな3D動画生成・DXFからSTEP生成・停止監視・自動修復限界判定・OpenClaw/Portal受入れ判定を行うための全部入りパックです。

## 基本方針

Claude Code側の結論を尊重します。

- UE5は今回の標準ルートから外す
- Blender+RV6が既に満足水準に到達している前提
- UE5 headless / EditorFramework 問題で詰まるリスクを避ける
- 品質改善は Blender+RV6 範囲で行う
- 採用判断はミニPC側の Acceptance Gate に任せる

## 優先改善順

1. カメラを街路レベルに下げる
2. RV6 strength を 0.55 から 0.65 に上げる
3. ESRGAN NCNN Vulkan を後段に追加
4. 夕方・夜景HDRIに切り替える
5. 自動停止監視と修復限界判定を追加
6. DXFからSTEPはFreeCAD headless優先

## 推奨実行順

```bash
python scripts/task_gate.py --task real_3d_video --config configs/acceptance_policy.yaml
blender --background --python scripts/blender_city_camera_rv6_prep.py
python scripts/esrgan_ncnn_batch.py --input renders --output renders_upscaled
python scripts/watchdog_repair_gate.py --command "python your_task.py"
```

## 文字化け対策

- 全ファイル UTF-8
- 改行 LF
- 日本語ファイル名は docs のみに限定
- 実行スクリプト名は英数字のみ
