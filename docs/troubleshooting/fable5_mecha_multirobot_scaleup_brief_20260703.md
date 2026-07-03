# Fable5 相談ブリーフィング: メカ・リギング → 30体同時・複数スキルRL学習へのスケールアップ

作成日: 2026-07-03 JST
対象: `projects/AtsugiMechaCity` (V50 mecha rig + RL統合) / ブランチ `feat/mecha-autorig`
想定読者: Fable5(トークン単価が高いため、本ドキュメントで事前検証済みの事実は再調査せず、判断・設計に集中してください)

---

## 0. Fable5への依頼事項（先に読むこと）

このドキュメントは「調査済み事実」と「未解決の意思決定」を分離してあります。

- **§1〜4は検証済みの事実。再調査・再検証は不要です。** 各項目にファイルパス/コミットを付与済み。
- **§5が本題の依頼**です。以下4点について、判断・設計方針を出してください（探索的な対話ではなく、結論とその根拠を簡潔に）:
  1. 30体×5スキル同時学習に対するシミュレータ/RLフレームワークの選定（単一GPU前提）
  2. マルチスキル方策のアーキテクチャ（スキル条件付き単一方策 vs スキル毎個別方策）
  3. 現行パイプラインを「機体名ハードコード」から「機体非依存」に直す設計（後述の技術的負債）
  4. 着手前に片付けるべき残課題の優先順位
- 出力形式の希望: 各項目「結論 → 根拠1〜2行 → 次の具体アクション」の順。長い比較表よりも結論優先。

---

## 1. 目標（北極星）

ユーザー原文の要求: 3Dメカモデルにリギングを行い、**自然な歩行・立つ・座る・走る・ドアを開く**などの動作を機械学習(RL)で獲得させる。**一度に約30体**を使って学習を回す。

現状は歩行(walk)1スキル・1機体(V50)のみが対象。「30体×5スキル同時」は今回新たに追加されたスコープで、既存の実装はこの規模を想定していない（§4で詳述）。

---

## 2. 現在の検証済み状態

### 2.1 リグ基盤（今セッションで修正済み）

- **[T046]/INC-140** (`data/workspace/memory/trouble_history.md` 該当セクション): V50の胴体・骨盤・両脚メッシュが未溶接(頂点マージ未実施)だった。Merge by Distanceで溶接済み・検証済み(境界エッジ11.5万→数百に収束)。溶接後blend: `scratch/v50_armature_builder_smoke4/robot_walk_v50_armature_build_WELDED.blend`。原本は非破壊バックアップ済み。
- **同インシデントで判明: 両腕が肩から脱離**。腕メッシュがボーンから X約0.3外・Y約0.7後ろにオフセットして浮遊。胴体・脚は健全。**未修正・要再接合**。ユーザー指定の正解参照: `D:\AI\PartPacker\output\KEEP_ORIGINAL_flow_big_parts_strict_pvae_20260628_025827_v50_BASELINE\robot_walk.blend`。
- **接合ゲートを修正済み** (`projects/AtsugiMechaCity/v50_joint_attachment_gate.py`): 許容値を身長12%→6%に厳格化し、マーカー非依存の直接親子接触チェック(`parent_child_meshes_detached_at_rest`)を新設。修正前は同一クラスの脱離を**2回連続で誤PASS**させていた(`rl_integration/quality_incident_report_v50_arm_lock_visual_regression_20260701.md` = 2026-07-01の1回目、[T046]/INC-140 = 2026-07-02/03の2回目)。**この再発パターンは、単発バグではなくゲート設計の構造的欠陥だったことを意味する**。

### 2.2 RLアーティファクト生成（Phase 1完了・Phase 2未着手）

`projects/AtsugiMechaCity/rl_integration/HANDOVER_TO_CODEX.md` に詳細。要点:

- 既存: `v50_urdf_exporter.py` / `v50_mjcf_builder.py` / `v50_reference_motion_exporter.py` / `v50_pipeline_runner.py`（V50単機体・walkスキル専用、ワンコマンドでURDF/MJCF/AMP JSON/BVH生成）。
- `v50_amp_config.yaml`: Genesis backend想定、`num_envs: 4096`（**同一機体の並列環境数**であり、機体多様性ではない点に注意）。reference_motionは**sin波1本のみ**（walk専用、他スキルなし）。
- 実RL学習（DiffMimic/Genesis/Isaac Lab）は**未着手**。bd issue `Clawdbot_Docker_20260125-q00`（DiffMimicスモークテスト、open）。

### 2.3 GPU実行パス（ブロック中）

`rl_integration/HANDOVER_TO_CLAUDECODE_GPU_20260702.md` に詳細。要点:

- GPU: **RTX 5060 Ti 16GB 単体**（クラスタ・マルチGPUなし）。
- Docker+NVIDIA GPUパススルーは動作確認済み(`nvidia-smi`成功)。
- **WSL Ubuntuが起動不能**(`WSL_E_USER_NOT_FOUND`, `getpwnam(yasu) failed 5`)。Windows側JAXはCPUのみ。
- 推奨次善策(未検証): WSL経由ではなく **Docker + NVIDIA JAX Toolbox公式イメージ** (`https://github.com/NVIDIA/JAX-Toolbox`) でGPU JAX/MJXを動かす。
- **既存のCPU版V50自律ループは維持したまま**、GPU検証は別経路で進める方針が既に採用されている（安全側の判断、変更不要）。

### 2.4 調査済み外部リソース（再調査不要・優先順位付き）

`rl_integration/HANDOVER_TO_CODEX.md` §3 より抜粋。フルリストは同ファイル参照。

| 種別 | 名称 | ライセンス | 備考 |
|---|---|---|---|
| モーションDB | 100STYLES | CC BY 4.0 | 4M+フレーム・100歩行スタイル、**最優先候補** |
| モーションDB | PHUMA | Apache-2.0 | 物理検証済ヒューマノイド、足滑りなし設計 |
| RLフレームワーク | DiffMimic | Apache-2.0 | 既存キーフレーム→物理valid、最速始動 |
| RLフレームワーク | Genesis | Apache-2.0 | 43M FPS(RTX4090)、`pip install genesis-world`、現在の既定backend |
| RLフレームワーク | Isaac Lab + AMP/ASE | BSD-3 | 最高品質、URDF/MJCF/USD対応 |
| マルチスキル手法 | **ASE (Adversarial Skill Embeddings)** | BSD-3 (NVIDIA) | `bd memories` 記録済み(`amp-ase-siggraph2021-2022`)。**スキル埋め込み+単一方策**で複数動作を扱う手法。今回の「歩く/立つ/座る/走る/ドアを開く」5スキル要求と直接合致する可能性が高い |
| モーション生成 | MoMask / CLoSD | MIT | テキスト→モーション→物理トラッキング。座る/ドアを開く等の非歩行スキルの参照モーション調達に有用 |

---

## 3. 今回のスコープ拡大で新たに生じる課題（技術的負債の可視化）

現行パイプラインは**V50という1機体専用にハードコード**されている。以下は全て機体名・部位名を直接埋め込んだ実装で、30機体への展開時にそのままでは動かない:

- `v50_armature_builder.py` / `v50_final_walk_preview.py` / `v50_joint_attachment_gate.py` / `v50_original_compare_gate.py` 内の `TORSO`, `UPPER_ARM_L`, `geometry_0.005` 等の固定オブジェクト名リスト。
- `v50_amp_config.yaml` の `dof_order` は12DOF・V50固有の関節順序を直書き。
- 参照モーションは1本(walk)のみ。stand/sit/run/door-openの参照モーション・報酬設計が存在しない。
- 並列化(`num_envs: 4096`)は**同一機体のコピー**を前提とした設計であり、**異なるメッシュ・異なるボーン構成を持つ30機体**を同一バッチで扱う設計ではない。

これは「バグ修正」ではなく**アーキテクチャ選定が必要な新規設計課題**である。

---

## 4. 未解決の前提確認（推測せず、ここで明示）

- 「30体」の意味: (a) 同一V50機体の物理パラメータ違いバリエーション30種、(b) PartPacker等で生成した**異なるメッシュ形状**30種、のどちらか未確定。設計難度が大きく変わる（(b)は機体非依存パイプラインが必須、(a)は現行アーキテクチャの延長で対応可能）。
- 「一度に」の意味: 同時に学習ジョブとして走らせる（GPU/CPUリソース同時消費）のか、それとも学習カリキュラムとして順次・自動で回すのかが未確定。
- ハードウェアはRTX 5060 Ti 16GB 1枚のみ。30機体×5スキルの同時実物理シミュレーションは、機体ごとに独立したMJX/Genesis環境を要求すると VRAM上厳しい可能性が高い。

---

## 5. Fable5への依頼（§0の再掲・本題）

以下4点について結論と根拠を出してください。前提が不明な点(§4)は、複数前提での場合分け回答で構いません。

1. **シミュレータ/フレームワーク選定**: 単一RTX 5060 Ti 16GBで30機体×5スキルを扱うなら、Genesis / Isaac Lab / MuJoCo-MJX+DiffMimicのどれを基盤にすべきか。
2. **マルチスキル方策設計**: ASE的なスキル埋め込み単一方策 vs スキル毎個別AMP方策のどちらが、この規模・このGPUで現実的か。
3. **機体非依存パイプラインへの改修方針**: `v50_*.py` 群のハードコードされたパーツ名リストを、PartPacker出力ごとに変わる命名に耐える形（スキーマ駆動のボーン/メッシュマッピング等）へ改修する設計案。
4. **着手順序**: 腕再接合・カメラ修正等のV50単機体の残課題(§2.1)を先に完了させてから拡張すべきか、並行で機体非依存化に着手すべきか。

---

## 6. 運用制約（変更不要・参考情報）

- モデルルーティング: 軽タスク→`local_fast`(qwen3:8b)、通常→`google/gemini-2.5-flash`、Fable5は戦略判断のみに予約(コスト理由)。
- 変更方針: CLAUDE.md「Surgical Changes」原則により、広範囲リファクタは事前承認必須。Fable5の設計提案は「Plan」として出し、実装は承認後に別セッションで行う。
- 環境: D:ドライブが直近ほぼ満杯(空き数GB)になり、F:ドライブへ静的データ退避で応急対応中。恒久対策は別issue。V50作業自体は継続可能な状態まで復旧済み。

---

## 7. 参照ファイル一覧（Fable5がこれ以上探索しなくて済むように）

```
projects/AtsugiMechaCity/rl_integration/HANDOVER_TO_CODEX.md
projects/AtsugiMechaCity/rl_integration/HANDOVER_TO_CLAUDECODE_GPU_20260702.md
projects/AtsugiMechaCity/rl_integration/quality_incident_report_v50_arm_lock_visual_regression_20260701.md
projects/AtsugiMechaCity/rl_integration/v50_amp_config.yaml
projects/AtsugiMechaCity/v50_joint_attachment_gate.py
projects/AtsugiMechaCity/v50_final_walk_preview.py
data/workspace/memory/trouble_history.md  ([T035][T033][T045][T046]セクション)
D:\AI\PartPacker\output\KEEP_ORIGINAL_flow_big_parts_strict_pvae_20260628_025827_v50_BASELINE\robot_walk.blend
```
