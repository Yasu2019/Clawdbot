# Visual Inspection AI 展開+実用化改修 (2026-07-10)

> ChatGPT生成の土台(ZIP_Group/visual_inspection_ai)をFable5が監査・改修し `projects/visual_inspection_ai/` へ展開。
> 入口: README.md / QUICKSTART_JA.md / **RUN_VERIFICATION_JA.md**(ホスト検証手順) / agent_protocol/(AI引継ぎ規約同梱)

## 監査結果(サンドボックス実走)

- ZIP SHA256一致。参照差分検知は合成デモで良品0.001 vs 不良0.006-0.016と分離=**土台は本物**
- **致命的発見**: 出荷時しきい値(review 0.008/ng 0.045)は誤校正 — バリ(0.006)がOK素通り
- **最大リスク**: 画素単位差分は治具ズレ数pxで偽NG量産(6pxズレで良品0.001→0.262)

## Fable5改修(3点)

1. **ECCアライメント前段** `src/inspection_ai/detection/alignment.py` — 並進補正+3重安全ゲート(不収束/上限超シフト/相関<0.5で無補正フォールバック=REVIEW側に倒れる)。recipe `model.alignment: "ecc"`。実測: 6,-5pxズレ良品 0.262→0.0011(シフト推定誤差0)・不良検出力維持
2. **しきい値校正CLI** `scripts/calibrate_thresholds.py` — 決定論(max良品+3MAD)×1.1マージン切上げ+幾何中点。分離不足時は適用拒否(--force要)。demo適用済み: review **0.001199** / ng **0.006574**(全不良種がNG域へ)
3. **寸法スケール校正CLI** `scripts/calibrate_scale.py` — 既知長2点→mm_per_pixel算出・recipe適用(mm_per_pixel配線は既存で健在)

## テスト

- 新規 `tests/test_alignment_and_calibration.py` 6件(シフト回復/良品維持/分離維持/誤収束フォールバック/しきい値分類/スケール解析解)
- サンドボックス実走: 新規6+既存アルゴリズム層4+pipeline E2E = PASS。**API層(test_api)はホストでpytest要**(RUN_VERIFICATION_JA.md §2)

## 未解決・次フェーズ

- ホストE2E(§1-4)は未実施 → ユーザー実行待ち
- 実部品パイロット: 実カメラ画像・MSA・p95処理時間測定が必要(受入基準 docs/08)
- 校正時の一時モデルとChampion運用モデルの版一致管理(現状は独立学習) — 実運用前に要整理
- bd起票要: 本展開の記録+ホストE2E結果の追記

## 教訓(ChatGPT→Fable5連携の型)

土台生成(ChatGPT)→実走監査で誤校正・脆弱性を定量特定(Fable5)→決定論校正・安全ゲートで実用化、の分担が機能した。「しきい値はデータで校正するまで飾り」
