# INC-140 / [T046] V50 修復ツール一式

2026-07-02〜03 の V50「胴/肩脱離・左前腕手脱離・左脚破損」修復で使用したスクリプトと最終レポートの保全コピー。
経緯・教訓の正本は `data/workspace/memory/trouble_history.md` の **[T046]** セクション。

| ファイル | 役割 |
|---|---|
| `v50_weld_apply.py` | 未溶接メッシュ(胴/骨盤/両脚)の検出+Merge by Distance+法線再計算。`blender -b <src> -P v50_weld_apply.py -- --input <src> --output <dst> --report <json>` |
| `dump_orig_matrices.py` | 正解参照(KEEP_ORIGINAL V50)の全メッシュworld行列/中心/寸法をJSONダンプ |
| `v50_arm_reattach.py` | 腕14メッシュをオリジナル姿勢へ復元+**両方の**アーマチュアの腕ボーン/マーカー/SHARED_COREを解剖学的ピボットへ移動 |
| `joint_gate_armfix4.json` | 強化版接合ゲート(rest 6% + 直接接触チェック + unhide修正)の最終 **PASS_JOINT_ATTACHMENT** レポート |
| `orig_compare_armfix.json` | オリジナル比較ゲート最終結果。component比 7.27→**1.12**(分離問題解消)。残課題 motion比 0.17=参照モーション品質(Stage A担当) |

成果blend: `scratch/v50_armature_builder_smoke4/robot_walk_v50_armature_build_WELDED_ARMFIX.blend`
(原本バックアップ: 同ディレクトリ `*.PRE_WELD_BACKUP_20260702.blend`)

次フェーズ(30体×5スキル)の設計判断: `docs/troubleshooting/fable5_mecha_multirobot_scaleup_decision_20260703.md`

**ローカルAI向け再現手順(QC三点セット):** `../qc/` — `mecha_rig_qc_process_chart.md`(工程表) / `mecha_rig_fmea.md`(FMEA・全行実インシデント由来) / `mecha_rig_checksheet.md`(コマンド+数値基準の実行チェックシート)。本フォルダのスクリプト群はこのQC工程の実行ツール。
