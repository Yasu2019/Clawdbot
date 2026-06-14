# Quality Analysis Protocol — Clawstack Unified

## 適用範囲
**IATF 動画生成**および**ユーザーからの全指示**に対して、実装・生成開始の前に本プロトコルを実施すること。

**強制力の単一真実:** 方針だけでは不十分。必ず `docs/iatf_gate_enforcement_protocol.md` と `pipeline/gate_registry.py` を参照し、コードで `raise` すること（T018 / INC-101 / PROMISES P024）。

## 7ツール実施手順（動画パイプライン）

| # | ツール | JSONキー | 最低要件 |
|---|--------|----------|----------|
| 1 | QC工程表 (PMP) | `qc_process_chart` | 2行以上 |
| 2 | FMEA | `fmea` | 2行以上 |
| 3 | FTA | `fta_top_event`, `fta_root_causes` | 頂上1 + 根因1以上 |
| 4 | なぜなぜ分析 | `why_why` | 1行以上 |
| 5 | Fishbone | `fishbone` | problem + 4M1E |
| 6 | ロジカルツリー | `logical_tree` | top_event + nodes 2以上 |
| 7 | リスク要約 | `key_risks`, `recommended_emphasis` | 各1件以上 |

## 過去トラチェック（必須入力）
自動で以下を LLM プロンプトへ注入:
- `data/workspace/memory/trouble_history.md`
- `data/workspace/iatf_generation_lessons.json` (`lessons_learned`, `fmea_log` 直近)

## パイプライン組み込み（fail-closed）

| 段階 | 処理 |
|------|------|
| PDF抽出後 | `run_host.quality_preflight_gate()` |
| 台本生成前 | `quality_preflight.json` 必須。不合格なら **停止** |
| resume | `quality_preflight.json` 未検証なら PDF テキストから再実行 |
| Golden短尺 | `scripts/iatf_golden_short_v1.py` → minimal gate |

成果物: `{video_dir}/quality_preflight.json`（`_validation` フィールド付き）

### 環境変数
| 変数 | 既定 | 意味 |
|------|------|------|
| `IATF_VIDEO_QUALITY_PREFLIGHT_REQUIRED` | `1` | `0` でのみデバッグ用スキップ |
| `IATF_QUALITY_PREFLIGHT_TIMEOUT_SEC` | `90` | LiteLLM タイムアウト |

### 実装ファイル
- `clawstack_v2/apps/iatf_video_factory/pipeline/quality_preflight.py`
- `clawstack_v2/apps/iatf_video_factory/run_host.py` (`quality_preflight_gate`)

## Claude / Cursor セッションでの適用
エージェントは動画生成タスク開始時に:
1. 上記7分析の要約を確認（または `quality_preflight.json` を読む）
2. 過去トラを `trouble_history.md` から確認
3. 分析なしで台本・レンダを開始しない

## 制作レイアウトゲート（出演者・背景・照明・カメラ・2026-05-31）

| 工程 | 内容 |
|------|------|
| LLM事前分析 | `quality_preflight.json` の `production_design` + `production_fmea` |
| コード検証 | `production_design.json`（CHAR_MAP/FBX/scene_ctx/camera/light） |
| 静止画 | 既存フレームがあれば Visual QA checklist (`production_still_qa.json`) |
| 動画 | interim QA (frame~100) + final `visual_qa` |

設定: `config/iatf_production_design_qc.json`  
実装: `pipeline/production_design_gate.py`  
環境変数: `IATF_VIDEO_PRODUCTION_DESIGN_REQUIRED=1`, `IATF_PRODUCTION_STILL_QA_REQUIRED=1`

## Script QA ゲート（fail-closed・2026-05-31）

| 条件 | 動作 |
|------|------|
| `overall != PASS` | **TTS/レンダ停止**（API・時間の無駄を防止） |
| `overall == ERROR` | 同上（FAIL と同扱い） |
| 再生成 | 最大 `IATF_SCRIPT_QA_MAX_REGENERATIONS` 回（既定2） |
| Telegram | PASS 時のみ合格通知。FAIL は停止通知 |

| 変数 | 既定 |
|------|------|
| `IATF_VIDEO_SCRIPT_QA_REQUIRED` | `1` |
| `IATF_SCRIPT_QA_MAX_REGENERATIONS` | `2` |

実装: `pipeline/script_qa_gate.py`

## CAE 試行の失敗解析（fail-closed 蓄積・2026-06-01）

| 工程 | 内容 |
|------|------|
| 毎試行後 | `scripts/cae_failure_analysis.py` -- QC/FMEA/FTA/5Why/Fishbone/ロジックツリー/DOE |
| 蓄積 | `data/workspace/cae_failure_analysis.jsonl` + `universal_growth.db` 表 `cae_failure_analyses` |
| 成功率改善 | LAVIE は `resin_flow` のみ、OF-REAL-001 帯、best_params リセット、`suggest_params` クランプ |

環境変数: `CAE_FAILURE_ANALYSIS_LLM_MODE=failed`（24/365 既定）、`CAE_FAILURE_ANALYSIS_MODEL=google/gemini-2.5-flash`

詳細: `docs/cae_failure_analysis_protocol.md`

## DXF2STEP 試行の品質ゲート（fail-closed 蓄積・2026-06-13）

| 工程 | 内容 |
|------|------|
| 試行前 | `scripts/dxf2step_quality_gate.py` → QC工程表 + FMEA + FTA/5Why/Fishbone/ロジックツリー |
| 試行後 | 失敗時フル post-mortem；SUCCESS も DB 記録 |
| 蓄積 | `thinkpad_dxf2step_quality_analysis.jsonl` + `universal_growth.db`（`dxf2step_trial_analyses`, `dxf2step_fmea_registry`） |
| FCStd | 各 job の `quality_preflight.json` / `quality_postmortem.json` + `*.FCStd` アーカイブ |

環境変数: `DXF2STEP_QUALITY_PREFLIGHT_REQUIRED=1`, `DXF2STEP_QUALITY_LLM_MODE=failed`, `DXF2STEP_QUALITY_LLM_MODEL=local_fast`

詳細: `docs/dxf2step_quality_gate_protocol.md`  
組み込み: `scripts/k10_thinkpad_dxf2step_loop.py`

## メカリグ品質ゲート（関節分離防止・fail-closed・2026-06-14 T033）

剛体メカリグは「関節でパーツが分離しない」ことを保証しないと、腕脱離・腿割れが起きる。

| 工程 | 内容 |
|------|------|
| ビルド後 | `qc_joint_separation.py` → 各関節を可動域スイープし親子セグメント最小距離の成長を計測。`gap_growth > 4%×model_height` で **FAIL** |
| 目視（必須） | `qc_multiview.py --every 5` → **5フレーム毎 × 前/横/後** をサンプリング目視。**hero1枚での合格判定は禁止**（腕脱離・腿割れを見落とした再発防止） |
| 設計ルール | ①pivot=実形状の関節中心 ②オーバーラップ・ジョイントコア ③可動域=無隙間レンジ ④分離QCゲート（本表）|

**FMEA 追記（メカリグ）**
| 故障モード | 影響 | 対策 |
|---|---|---|
| 関節回転でパーツ分離（脱離/割れ） | 動画破綻 | ①〜④（pivot算出/コア/可動域/分離ゲート） |
| **目視をhero1枚で済ます** | **欠陥見落とし** | **5フレーム毎×前/横/後サンプリング目視を必須化** |

実装: `projects/AtsugiMechaCity/mecha_rig_builder.py`, `qc_joint_separation.py`, `scenes/qc_multiview.py`  
記録: bd `mecha-rig-joint-integrity-t033` / `trouble_history.md` T031・T032・T033

## 関連ゲート（別工程）
- OpenCodeGo HTTP preflight (`[0/6]`)
- Slide preflight / Visual QA
