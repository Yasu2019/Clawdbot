# 引継ぎ文書: メカ30体×スキル拡張RL — キュー⑤設計完了時点

作成日: 2026-07-03 | 作成: Claude (Opus 4.8) | 想定引継ぎ先: **任意のAIモデル**(Claude/Gemini/Codex/ローカルLLM)
bd issue: `Clawdbot_Docker_20260125-6li`(キュー⑤) / 前提知識ゼロで再開できるよう書く

## 1. 现在どこにいるか（実行キューの進捗）

| 項目 | 状態 | 証跡 |
|---|---|---|
| ① V50腕再接合 | ✅ 完了 | commit `0d2c90f0c`, gate PASS全12関節 |
| ② カメラ修正 | ✅ 完了 | `v50_final_walk_preview.py`(sensor_fit=VERTICAL) |
| ③ 強化ゲートPASS | ✅ 完了 | `inc140_repair/joint_gate_final_full_restore.json` |
| ④ Genesis GPUスモーク | ✅ 完了 | `rl_integration/genesis_smoke_report.json`(5,605 env-steps/s) |
| ⑤ 骨格+マニフェスト+スキル拡張設計 | ✅ **設計文書完了・ユーザー凍結承認待ち** | 本フォルダの4文書 |
| Stage A(DiffMimicトラッキング) | ⬜ 未着手 | 次の実装対象 |

## 2. ⑤の設計文書(このフォルダ)— 読む順序

1. `canonical_skeleton_spec.md` — **29DOF固定レイアウト+機体別DOFロックマスク+Tier制**。凍結前ドラフト。最重要
2. `mecha_rig_manifest.schema.yaml` — 機体別YAMLスキーマ(ハードコード全廃)
3. `manifests/v50.yaml` — マニフェスト第1号(全数値INC-140実測)
4. `skill_acquisition_pipeline.md` — ユーザー依頼→Web先生データ→学習→登録の9ステージ設計(S5ライセンス/S9検収は人間必須)

**設計の核となる決定3つ**(変更するなら全体を読み直すこと):
- 全機体同一の29DOFレイアウト+ロックマスク → 異形状30機体が同一行動空間で混在バッチ可能
- スキル条件付けはone-hot禁止、64次元学習埋め込みテーブル → 後からのスキル追加が「行追加+ファインチューン」で済む
- ピボット/部品名のハードコード禁止、全てマニフェスト経由(INC-140教訓8)

## 3. 次にやること（優先順）

1. **ユーザーに骨格仕様の凍結承認をもらう**(canonical_skeleton_spec.md §7のチェック項目)
2. Stage A実装: Genesis上のDiffMimic式トラッキング
   - venv: `C:\v50_work\genesis_venv`(genesis 1.2.1 + torch 2.11.0+cu128, RTX 5060 Ti動作確認済み)
   - 入口コード: `rl_integration/genesis_v50_smoke.py`(7段階スモーク、これを土台に拡張)
   - 参照: `rl_integration/v50_ref_motion.json`(現sin波。まず低motion問題 bd `1wr` をこれで解消)
3. MJCFエクスポータの29DOF+ロックマスク対応(`v50_mjcf_builder.py`改修) → 肩3DOF化
4. リターゲッタ(100STYLES BVH→カノニカル29DOF) = パイプラインS6

## 4. 環境・制約(ハマりどころ)

- **Blender**: `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe` -b 必須
- **Python(RL)**: `C:\v50_work\genesis_venv\Scripts\python.exe`(D:に置くな — D:は空き1割)
- **Python(cv2)**: `D:\Clawdbot_Docker_20260125\.venv\Scripts\python.exe`
- **D:ドライブ逼迫**(T039 WAL破損リスク連鎖): 作業出力は`C:\v50_work\`へ。D:→F:退避が進行中
- **正解基準**: `D:\AI\PartPacker\output\KEEP_ORIGINAL_..._v50_BASELINE\` は**読み取り専用扱い・上書き厳禁**
- **検収済みblend**: `scratch/v50_armature_builder_smoke4/robot_walk_v50_armature_build_WELDED_ARMFIX.blend`
- 文字化け: `PYTHONIOENCODING=utf-8` 推奨(cp932絵文字ログエラー回避)
- **ゲート許容値を勝手に緩めるな**(FMEA#2, RPN432)。緩和は正解基準での校正+人間承認+記録

## 4.5 API燃費の運用ルール(2026-07-03 ユーザー承認・全AI遵守)

1. **Tier1を完全に終えてからTier2へ**。並行着手禁止(デバッグの掛け算でAPI燃費悪化)。
2. **Tier2実装時**: 定型的なコード生成はcodex/ローカルLLM(無料)へ回す。Claude等の有料APIは**設計と、詰まった時の診断のみ**(CLAUDE.mdモデルルーティングの徹底)。
3. **1セッション=1目標**。複数目標を1セッションに詰めない。セッション開始時に目標を1つ宣言してから着手する。

## 5. 品質プロトコル(全AI共通・省略禁止)

- 機体検収は `qc/mecha_rig_checksheet.md` を上から実行(1項目=1コマンド、❌=停止・報告)
- 新しい故障モード発生時: `qc/mecha_rig_fmea.md` に行追加 → `data/workspace/memory/trouble_history.md` にT番号記録
- 数値PASSでも**目視確認は省略禁止**。ユーザー目視指摘 > ゲート判定
- セッション終了時: 自分が変更したファイルのみ git add → commit → **push必須**

## 6. 主要記録の所在

| 内容 | パス |
|---|---|
| 30体化のアーキテクチャ判断(Fable5回答) | `docs/troubleshooting/fable5_mecha_multirobot_scaleup_decision_20260703.md` |
| INC-140修復の全経緯・8教訓 | `data/workspace/memory/trouble_history.md` [T046] |
| 修復ツール+最終ゲートレポート | `projects/AtsugiMechaCity/inc140_repair/` |
| QC三点セット(工程表/FMEA/チェックシート) | `projects/AtsugiMechaCity/qc/` |
| RL統合の前提知識(データセット/フレームワーク調査) | `rl_integration/HANDOVER_TO_CODEX.md` |
| 未解決: 歩行モーション量不足 | bd `Clawdbot_Docker_20260125-1wr`(Stage Aで解消予定) |
| 未解決: 左手実体メッシュなし | `manifests/v50.yaml` qa.known_gaps(右手ミラーで生成予定) |
