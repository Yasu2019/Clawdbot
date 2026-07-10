# Visual Inspection AI 展開+実用化改修 (2026-07-10 Fable5)

- ChatGPT土台(ZIP 244KB/2553行/FastAPI+参照差分+Champion/Challenger)を実走監査→projects/visual_inspection_ai/へ展開
- **発見**: 出荷しきい値誤校正(バリ0.006<review0.008=素通り) / 6pxズレで良品スコア238倍(偽NG)
- **改修**: ①ECC並進アライメント+3重安全ゲート(不収束/上限シフト/相関<0.5→無補正=REVIEW側) ②決定論しきい値校正CLI(max良品+3MAD×1.1切上げ、分離不足は適用拒否) ③mm/pixel校正CLI
- demo校正適用: review 0.001199 / ng 0.006574。テスト: 新規6+既存5層+pipeline E2E PASS(API層はホストpytest要)
- ポータルカード追加(:8000)。手順: projects/visual_inspection_ai/RUN_VERIFICATION_JA.md / 引継ぎ: docs/handover/VISUAL_INSPECTION_AI_DEPLOY_20260710.md
- 教訓: **しきい値はデータで校正するまで飾り** / 画素差分は位置合わせ前段が実用の生命線
