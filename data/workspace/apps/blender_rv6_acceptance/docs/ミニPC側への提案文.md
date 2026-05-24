# ミニPC側への提案文

本提案は、UE5を無理に導入せず、既に満足水準に達している Blender + RV6 ルートを主軸として安定化・高品質化するものです。

採用理由:

1. 既存成果を壊さない
2. UE5 headless / EditorFramework 問題を回避できる
3. 追加工数が少ない
4. 視覚改善効果が高い順に実装できる
5. DXF→STEP、停止監視、自動修復限界判定まで同じゲートで扱える

提案する標準ルート:

- 3D動画: Blender → RV6 strength 0.65 → ESRGAN NCNN Vulkan
- CAD変換: FreeCADCmd DXF→STEP
- 長時間処理: watchdog_repair_gate 経由
- 実行前判定: task_gate.py

UE5は完全禁止ではなく、今回のミニPC標準ルートでは「保留・非推奨」とします。
