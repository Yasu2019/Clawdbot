# 引き継ぎ資産マスターインデックス（単一の入口）

> 作成: 2026-07-05 Fable5 | 根拠: `docs/handover/FABLE5_CONTINUATION_PROTOCOL_V2.md` §8
> **新セッションのAIはまずこのファイルを読むこと。** 資産は新規作成せず、ここに列挙された既存文書を更新する（重複作成禁止 = 検索見落とし教訓）。

## 0. 最初に読む3点（順番厳守）

1. `data/workspace/memory/trouble_history.md` — **[T019]北極星・意味ゲート最優先**。全障害履歴
2. `data/workspace/PROMISES.md` — **P025** ほか最重要制約
3. `projects/AtsugiMechaCity/design/HANDOVER_QUEUE5_AND_BEYOND.md` — メカRLの現在地・復帰手順（§4.6）

タスク一覧の単一情報源は **bd**（`bd prime` → `bd ready`）。Markdown TODOの複製は禁止。

## 1. システム全体

| 資産 | 所在 | 状態 |
|---|---|---|
| 全体構成レポート | `docs/clawstack_system_report.md` / `CLAWSTACK_SYSTEM_ANALYSIS.md` | 既存 |
| ポートマップ | `docker-compose.yml`（**必ず実ファイル確認** = T008）| 既存 |
| エントリポイントマップ | `docs/canonical_entrypoint_map_20260416.md` | 既存 |
| 運用ガバナンス | `GOVERNANCE.md` / `PROTECTED_PATHS.md` / `INCIDENT_RUNBOOK.md` | 既存 |
| 品質分析プロトコル | `docs/quality_analysis_protocol.md`（QC工程表/FMEA/FTA 全タスク必須）| 既存 |
| 北極星・意味ゲート | `docs/cae_north_star_and_meaning_gate_protocol.md` | 既存 |
| モデルルーティング | `CLAUDE.md` §Model Routing / `data/workspace/model_router.py` | 既存 |
| 変更履歴 | `CHANGELOG.md`（2026-07-05新設）| **運用開始** |

## 2. アプリ別資産マップ（プロトコル§2の5アプリ）

### 2.1 3Dロボット機械学習（完全ローカル・API非依存）

| 資産 | 所在 |
|---|---|
| 現在地・復帰手順 | `projects/AtsugiMechaCity/design/HANDOVER_QUEUE5_AND_BEYOND.md` |
| 骨格仕様(凍結v1.0) | `projects/AtsugiMechaCity/design/canonical_skeleton_spec.md` |
| マニフェストスキーマ | `projects/AtsugiMechaCity/design/mecha_rig_manifest.schema.yaml` + `manifests/v50.yaml` |
| スキル獲得パイプライン設計/実装仕様 | `design/skill_acquisition_pipeline.md` / `design/skill_pipeline_implementation_spec.md`（U0〜U8 PASS済） |
| RL前提知識 | `projects/AtsugiMechaCity/rl_integration/HANDOVER_TO_CODEX.md` |
| QC三点セット | `projects/AtsugiMechaCity/qc/`（工程表/FMEA/チェックシート） |
| 学習実行環境 | `C:\v50_work\genesis_venv`（D:に置くな）/ 進捗 `data/workspace/apps/mecha_motion_lab/supervisor_status.json` |

### 2.2 CETOL 6σ風 公差解析

| 資産 | 所在 |
|---|---|
| 理論知識ベース | `clawstack_v2/docs/knowledge/Cetol_Knowledge.md` |
| GD&T設計 | `docs/fable5_gdt_l10_design.md` / `data/workspace/apps/gdt_overlay_studio/` `gdt_step_face_viewer_v2/` |
| 理論パック | `ZIP_Group/moldflow_cetol_theory_pack_20260602.zip` |

### 2.3 DXF→3Dモデル生成

| 資産 | 所在 |
|---|---|
| ワーカー本体 | `data/workspace/apps/dxf2step/dxf2step_worker.py`（port 8003） |
| 品質ゲート | `docs/dxf2step_quality_gate_protocol.md` |
| 既知不具合系譜 | trouble_history [T048]/INC-142（暴走ループ）、INC-125/130/131/132 各 quality_incident_report_*.md |

### 2.4 OpenRadioss せん断加工解析

| 資産 | 所在 |
|---|---|
| エンジン操作 | `docker exec clawstack-unified-openradioss-1 bash -c "bash /work/start_engine.sh <N>"` / `kill_engine.sh`（kill -9必須） |
| チューニング記録 | `data/workspace/openradioss_10h_tuning_report.md` / `openradioss_10h_tuning/` |
| 衛星ノード運用 | `docs/SATELLITE_CAE_ONE_SHOT_RUNBOOK.md` / `docs/LAVIE_K10_INTEGRATION.md` |
| 進行中bd | `tq1`(blanking+crack TSTOP) / `b41` / `uj2` / `erw` |

### 2.5 Moldflow風 簡易解析

| 資産 | 所在 |
|---|---|
| ロードマップ | `docs/MOLDFLOW_CAe_ROADMAP.md` |
| Phase3実装判断 | `docs/MOLDFLOW_PHASE3_IMPLEMENTATION_DECISIONS.md` |
| アプリ本体 | `data/workspace/apps/moldflow_cae_studio/` / `moldflow_gate_studio/` |
| 進行中bd | `3qu`(Phase 7 STEP+gate+resin_fill_cad) / `kwr`(epic v002) |
| **禁止事項** | 薄管icoFoam+2D ParaView \|U\| ループ（T019/P025） |

## 3. 未実装一覧（2026-07-05時点・bdと同期）

- 二足歩行の持続(8秒): walk_tier1c cycle3学習中。エスカレーション時処方は HANDOVER_QUEUE5_AND_BEYOND §4.6-2
- 可視化コンバータ(qpos→ARMFIX blend): bd `1wr`、Stage B成功後
- 29DOFカノニカルエクスポータ+肩3DOF(B-2): canonical_skeleton_spec v1.0準拠、未着手
- 左手実体メッシュ: `manifests/v50.yaml` qa.known_gaps（右手ミラー予定）
- Moldflow Phase 7 / resin_fill v002: bd `3qu` `kwr`
- dxf2step 意味ゲート自動停止: bd `ip4`（T048再発防止・P1 bug）
- PartPacker CUDA可視性 / flow.pt: bd `cg2` `y37`
- 30体×5スキルRLスケールアップ: 設計凍結済み・実装未着手（メモリ: project_mecha_rl_scaleup_30robot）

## 4. 技術的負債一覧（2026-07-05時点）

1. **ルート直下のHANDOVER/STATUS文書乱立**（3D_*_HANDOVER 5本+quality_incident_report 20本超）→ 参照はここに集約済み。物理整理は`docs/duplication_cleanup_plan_20260416.md`に従い低優先で実施
2. **D:ドライブ逼迫**（T039 WAL破損リスク連鎖）→ 作業出力は`C:\v50_work\`、D:→F:退避進行中
3. **__pycache__/.pyc・デーモン status JSON がgit管理下**で常時dirty → .gitignore整理が必要（無断で広範囲変更しないこと）
4. **旧チェックポイント次元非互換**（12DOF系 run1-10/cycle1-3）→ 16DOF以降と混用不可
5. **n8n旧ワークフロー消滅**（2026-04-10 DBリセット）→ 再構築はbd経由で個別に

## 5. 既知不具合・障害履歴

- 単一情報源: `data/workspace/memory/trouble_history.md`（T001〜T048+）
- 個票: ルート `quality_incident_report_*.md` / `docs/INCIDENT_LOG.md`
- 新規故障モードは FMEA行追加 → trouble_history にT番号記録（省略禁止）

## 6. テスト資産・結果

- メカリグ検収: `projects/AtsugiMechaCity/qc/mecha_rig_checksheet.md`（1項目=1コマンド）
- 受け入れゲート実績: 各featコミットメッセージ「acceptance PASS」+ `inc140_repair/` ゲートレポート
- **ゲート許容値を勝手に緩めるな**（FMEA#2 RPN432）

## 7. ロードマップ

- CAE北極星: プレス部品3D → Moldflow級充填 + CETOL 6σ級公差 + OpenRadioss曲げ/打ち抜き → **順送金型開発**（T019/P025）
- メカRL: walk習得 → run/stairs_climb（`skill_requests.json`投入待ち・U5自動）→ 30体×5スキル
- Moldflow: `docs/MOLDFLOW_CAe_ROADMAP.md`
- AI体制: 2026-07-07 Fable5終了 → ChatGPT 5.5(新機能)/Opus 4.8(設計・レビュー)/Codex(実装)/ローカルLLM(定型) 分担 = プロトコル§4〜6
