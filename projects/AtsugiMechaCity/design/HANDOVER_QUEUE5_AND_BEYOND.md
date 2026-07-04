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
| ⑤ 骨格+マニフェスト+スキル拡張設計 | ✅ 完了・**骨格v1.0凍結済(2026-07-03ユーザー承認)** | 本フォルダの4文書 |
| Stage A(歩行トラッキング学習) | 🟡 **実装完了・学習ラン実行中** | `rl_integration/stage_a/train_v50_walk_tracking.py` / 進捗: `C:\v50_work\stage_a_run1\status.json`(10イテレーションごと更新, 1200予定) / 独立プロセス(セッション非依存) |

**Stage A 最終結果(2026-07-04, run1〜10で終結):**
- **達成**: GPU学習パイプライン完全実証 / 隠れバグ7件を発見・修正・記録([T047]罠#1〜#7: アクチュエータ衝突・スポーン高・座標系・**get_vel計器死**・目標到達性・**歩行軸誤り(X=横軸、前方は-Y)**・**報酬ハック(ダイブ&這い)**) / **2秒間の本物の二足歩行**(run8、レンダー目視確認済み)
- **未達**: 8秒間の持続歩行。run8(速すぎて2秒で転倒・vx0.4)⇔run9/10(保守化してほぼ静止・vx0.05)の振り子から抜けられず
- **結論**: 合成sin歩容はバランス動力学(制御された前方転倒・重心移動)を含まず、安定化はRL任せになり本質的に難しい。**チューニング打ち切り、Stage B(100STYLES実モーション参照への置換)へ移行**(2026-07-04ユーザーへ提案済み)
- **チェックポイント**: 最良の歩行方策=`C:\v50_work\stage_a_run8\latest.pt`(2秒歩行)。トレーナはそのまま流用し`gait_reference()`をリターゲット済み実モーションに差し替えるのがStage Bの中核作業
- **可視化コンバータ**(qpos軌跡→ARMFIX blend)は未作成のまま。Stage Bの成功後に作成(bd `1wr`クローズ条件: 比較ゲートmotion比>0.55)

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

## 4.4 Stage B-1 実装計画(2026-07-04 ユーザーB案承認 — 中断時はここから再開)

**背景**: Stage B(実モーション参照)3サイクル自律実行→エスカレーション。ペース追従は完璧(vx=クリップ値一致)だが必ず数秒で完全転倒。**根本原因仮説: 12DOF矢状面のみ=hip/ankle rollロックで横バランス制御が物理的に不可能**。

**B-1スコープ(1セッション)**: hip_L/R_roll + ankle_L/R_roll の4DOF解錠(12→16DOF)。
実装箇所(すべて `rl_integration/stage_a/train_v50_walk_tracking.py` と関連):
1. Env内XML書換に**roll関節追加**: upper_legボディに `<joint name="hip_?_roll" axis="0 1 0" range="-20 20">`、footボディに `<joint name="ankle_?_roll" axis="0 1 0" range="-15 15">`(既存書換=アクチュエータ除去/足向き/かかと、と同じ場所)
2. `DOF_NAMES` 末尾に4DOF追加(末尾追加ルール)、KP/KV拡張(roll: hip 400/40, ankle 200/20)
3. `gait_reference`/`_sin_gait`: 12列出力の末尾にゼロ4列をパディング(rollの参照は0=直立中立、バランスはRLが使う)
4. `OBS_DIM` 38→46(q-ref 16 + qd 16 + 既存14)、`ACT_DIM` 12→16
5. **旧チェックポイント(run1-10, cycle1-3)は次元非互換で再利用不可** — フレッシュ学習。playbook.yaml の best_walker を空にする
6. devラン(5it)→supervisor経由でtier1サイクル起動(--ref-json ref_neutral_fw.json)

**B-2(後日)**: マニフェスト駆動カノニカルエクスポータ(29DOF+ロックマスク、肩3DOF) — canonical_skeleton_spec.md v1.0準拠。

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
