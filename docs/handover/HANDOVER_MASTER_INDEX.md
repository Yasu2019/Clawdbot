# 引き継ぎ資産マスターインデックス（単一の入口）

> 作成: 2026-07-05 Fable5 | 根拠: `docs/handover/FABLE5_CONTINUATION_PROTOCOL_V2.md` §8
> **新セッションのAIはまずこのファイルを読むこと。** 資産は新規作成せず、ここに列挙された既存文書を更新する（重複作成禁止 = 検索見落とし教訓）。

## 0. 最初に読む3点（順番厳守）

1. `data/workspace/memory/trouble_history.md` — **[T019]北極星・意味ゲート最優先**。全障害履歴
2. `data/workspace/PROMISES.md` — **P025** ほか最重要制約
3. `projects/AtsugiMechaCity/design/HANDOVER_QUEUE5_AND_BEYOND.md` — メカRLの現在地・復帰手順（§4.6）

> **直近セッション差分**: `docs/handover/MECHA_STAIRS_CLIMB_CORRIDOR_HANDOVER_20260727.md`（2026-07-27 corridor Phase2完了4/5地形 + T079訂正=階段昇段は実は一度も未達成だった + climb_progress報酬追加で再学習中）  
> （直前）`docs/handover/LAVIE_OF_C_WORKER_AND_FILL_TELEGRAM_QUARTERBOX_20260728.md`（2026-07-28 Lavie C: worker :5683 / OF SUCCESS / Telegram 1/4-box viz fix）  
> （参考・Fable5最終日）`docs/handover/FABLE5_FINAL_SESSION_HANDOVER_20260707.md`

タスク一覧の単一情報源は **bd**（`bd prime` → `bd ready`）。Markdown TODOの複製は禁止。

## 1. システム全体

| 資産 | 所在 | 状態 |
|---|---|---|
| 全体構成レポート | `docs/clawstack_system_report.md` / `CLAWSTACK_SYSTEM_ANALYSIS.md` | 既存 |
| ポートマップ | `docker-compose.yml`（**必ず実ファイル確認** = T008）| 既存 |
| エントリポイントマップ | `docs/canonical_entrypoint_map_20260416.md` | 既存 |
| 運用ガバナンス | `GOVERNANCE.md` / `PROTECTED_PATHS.md` / `INCIDENT_RUNBOOK.md` | 既存 |
| 品質分析プロトコル | `docs/quality_analysis_protocol.md`（QC工程表/FMEA/FTA 全タスク必須）| 既存 |
| **死活再チェック** | `docs/dead_project_recheck_protocol.md` + `scripts/dead_project_recheck.py` + 登録簿 `data/workspace/heartbeat_manifest.json`（毎日実行・常駐追加時は登録必須）| **2026-07-07新設** |
| **成長ループ品質** | `docs/growth_loop_quality_protocol.md` + `scripts/growth_loop_audit.py` + 登録簿 `data/workspace/growth_loop_manifest.json`（T&E蓄積系は登録必須・G1物理妥当/G2情報増加/G3基準相関/G4学習反映の4ゲート・**判定へのLLM禁止**）| **2026-07-07新設** |
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
| **計算エンジン(検証済2026-07-05)** | Progressive Die Hub `:8004` `POST /api/tolerance-stack`（WC/RSS/MC/Cpk — 既知解で定量検証PASS、bd `iy63` NOTES参照）|
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
| **成熟度評価(L0-L10)** | `data/workspace/commercial_benchmark_maturity.py`（2026-07-07リファクタ: 宣言的ルール`_LEVEL_RULES`+鮮度ゲート）/ テスト `data/workspace/tests/test_commercial_benchmark_maturity.py` |
| 進行中bd | `tq1`(blanking+crack TSTOP) / `b41` / `uj2` / `erw` |

### 2.5 Moldflow風 簡易解析

| 資産 | 所在 |
|---|---|
| ロードマップ(機能軸) | `docs/MOLDFLOW_CAe_ROADMAP.md` |
| **精度軸L3→L10計画** | `docs/moldflow_accuracy_l3_to_l10_te_plan.md`（2026-07-07新設・昇格ゲートは決定論のみ・L6はユーザー実測データ要）|
| Phase3実装判断 | `docs/MOLDFLOW_PHASE3_IMPLEMENTATION_DECISIONS.md` |
| アプリ本体 | `data/workspace/apps/moldflow_cae_studio/` / `moldflow_gate_studio/` |
| **成熟度評価(L0-L10)** | `data/workspace/commercial_benchmark_maturity.py`（2026-07-07リファクタ: verdict分類是正=ERROR/FAILED_*をfailed計上、直近50件残差走査）/ テスト同上 |
| 進行中bd | `3qu`(Phase 7 STEP+gate+resin_fill_cad) / `kwr`(epic v002) |
| **禁止事項** | 薄管icoFoam+2D ParaView \|U\| ループ（T019/P025） |

## 3. 未実装一覧（2026-07-05時点・bdと同期）

- **L20自律ループ動画自動送信**: L39プロモーション（昇格）時のロールアウト動画（MP4/GIF）のTelegram送信実装。現在テキスト送信のみ完了。
- **goto_targetのGenesis移植結線**: 設計・タスクロジック・テストは完了済み(`goto_target_skill_design.md`)。Env結線およびsupervisorの結合が未実装（walkゲート通過がblockedBy、Codex担当）。
- **可視化コンバータ (qpos→ARMFIX blend)**: bd `1wr`、Stage B成功後。
- **29DOFカノニカルエクスポータ+肩3DOF (B-2)**: canonical_skeleton_spec v1.0準拠、未着手。
- **左手実体メッシュ**: `manifests/v50.yaml` qa.known_gaps（右手ミラー予定）。
- **30体×5スキルRLスケールアップ**: 設計凍結済み・実装未着手。
- **Moldflow Phase 7 / resin_fill v002**: bd `3qu` `kwr`。
- **dxf2step 意味ゲート自動停止**: bd `ip4`（T048再発防止、同一failure_classでの無限ループ防止）。
- **PartPacker CUDA可視性 / flow.pt**: bd `cg2` `y37`。
- **red_lavie DOE誘導**: punch_speed≥3000mm/s側への優先探索（低速域発散のため）。
- **moldflow_golden_case.py のスケジュール実行**: 日次監査チェーンへの組み込み。

## 4. 技術的負債一覧（2026-07-05時点）

1. **ルート直下のHANDOVER/STATUS文書乱立**（3D_*_HANDOVER 5本+quality_incident_report 20本超）→ 参照はここに集約済み。物理整理は`docs/duplication_cleanup_plan_20260416.md`に従い低優先で実施
2. **D:ドライブ逼迫**（T039 WAL破損リスク連鎖）→ 作業出力は`C:\v50_work\`、D:→F:退避進行中
3. **__pycache__/.pyc・デーモン status JSON がgit管理下**で常時dirty → .gitignore整理が必要（無断で広範囲変更しないこと）
4. **旧チェックポイント次元非互換**（12DOF系 run1-10/cycle1-3）→ 16DOF以降と混用不可
5. **n8n旧ワークフロー消滅**（2026-04-10 DBリセット）→ 再構築はbd経由で個別に

## 5. 既知不具合・障害履歴

- 単一情報源: `data/workspace/memory/trouble_history.md`（T001〜T054）
- 個票: ルート `quality_incident_report_*.md` / `docs/INCIDENT_LOG.md` / 手順書 `docs/handover/T051_GATES_VERSION_MISMATCH_20260706.md`（衛星ペア配布の罠3つ+CETOL L4追記）
- 新規故障モードは FMEA行追加 → trouble_history にT番号記録 → **五層記録**（プロトコル§7.2: 過去トラ/個票/brv/Obsidian/bd — 省略禁止）

## 6. テスト資産・結果

- メカリグ検収: `projects/AtsugiMechaCity/qc/mecha_rig_checksheet.md`（1項目=1コマンド）
- 受け入れゲート実績: 各featコミットメッセージ「acceptance PASS」+ `inc140_repair/` ゲートレポート
- 成熟度評価の単体テスト: `data/workspace/tests/test_commercial_benchmark_maturity.py`（18件, 2026-07-07全PASS。実行: `cd data/workspace && python -m unittest tests.test_commercial_benchmark_maturity -v`）
- **ゲート許容値を勝手に緩めるな**（FMEA#2 RPN432）

## 7. アプリ別進捗クロスチェック（2026-07-09・Beads/ByteRover/Obsidian/過去トラDB 4ソース照合）

> 知識ソースの所在: Beads=`bd list`/`bd memories`(482件) / ByteRover=`.brv/context-tree/`(cae・dxf2step・design配下) / Obsidian=`data/state/Obsidian Vault/60_PC_Logs/`(PCログ・障害個票) + `data/workspace/obsidian_vault/`(トラブルシューティング・API_Summaries) / 過去トラ=`data/workspace/memory/trouble_history.md`(T001〜T054)
> **brvルール `atsugi-mecha-joint-gate-preflight`**: メカ系ジョブは Beads・ByteRover・Obsidian 60_PC_Logs・trouble_history・INCIDENT_LOG の事前照合必須（本節はその全アプリ版）

### 7.1 3Dロボット機械学習 — 🟢 稼働中（自律ループ進行中）
- **bd**: in_progress 12件超（`e6h` Stage B実モーション化 / `dot` MJX PPO AMP / `x4o` 30体ビューア / `qao` 自律ハーネス 等）
- **brv**: `robot-walk-part25-thigh-split-inc133.md` / `robot-walk-v50-joint-attachment-gate-inc136.md`。bd memories に100STYLES(4M+フレームCC BY)/AMP/MoMaskのデータセット・手法調査済み
- **Obsidian**: `20260628_cube_disappearance_incident.md`(T045) / `20260628_mlagents_setup_incident.md`
- **過去トラ**: T031(false-PASS) T044〜T047(INC-133/134/140/141)
- **現在**: **Robot L20 自律サイクル88完了（Running）**。1分（60秒）間隔でループ稼働を継続。最高スコア `100` (L20_CANDIDATE / task_floor `93.4`) をキープして進行中。
- **死活監視**: `robot_l20_watchdog_status.json` および `robot_l20_autonomous_status.json` が K10 共通監視に統合され、常時稼働中。

### 7.2 CETOL 6σ風 公差解析 — 🟠 知識蓄積は進行・**bd追跡ゼロ（ギャップ）**
- **bd**: open/closedとも専用issueなし → `bd memories cetol`にマッピング知識のみ
- **brv**: `cae/cetol_progressive_die_freecad_mapping_20260617.md` — **成熟度L1→L10マップ**、Progressive Die Hub(:8004)`/api/tolerance-stack`にWC+RSS+モンテカルロ+簡易Cpk実装済、FreeCAD `tolerance_analysis`エンジン(antigravityコンテナ`/work/freecad/tolerance_analysis/`)
- **知識**: `clawstack_v2/docs/knowledge/Cetol_Knowledge.md` 継続更新中（セミナー事例: 04富士ゼロックス/03東芝ITC/U2Uクライスラー）
- **現在地**: L1-L2+Hub連携済み / L4(STEP PMI)・L10(FreeCAD 3Dループ)未完 → bd `azrr`配下でissue化(2026-07-05)

### 7.3 DXF→3Dモデル生成 — 🟠 S1系統復旧済み・再発防止(ip4)未完
- **bd**: `ip4`(P1 bug **未着手**: T048意味ゲート自動停止・3度目の暴走) / `0wf`(P2 INC-131監査修正) / `5yk`(S1偽FAIL 6層修正・7/6完了)
- **brv**: `dxf2step/dxf2step-s1-false-fail-6layer-fix-5yk-20260706.md`(**T053完結編**) / `dxf2step_p20_closed_loop_qc_inc132.md` + context-tree直下にINC-124/130/131個票
- **過去トラ**: **T040〜T043の偽SUCCESS4連発 + T048暴走(D:毎分1GB消費) + T053偽FAIL6層構造(7/6解決)** — 品質ゲート系が最大の負債
- **Obsidian**: `60_PC_Logs/DXF2STEP_5yk_S1_6layer_false_fail_fix_20260706.md`
- **現在**: worker稼働(:8003)。**T053解決によりS1実務図面 SUCCESS(`tp-dxf-c3ff67e0`)・目視QC PASS**（6/27以降の実務図面全滅は解消）。残る最優先は `ip4`（暴走時の意味ゲート自動停止）

### 7.4 OpenRadioss せん断加工 — 🔴 red_lavie停止中（2026-07-05検証で判明・要人間介入）
- **bd**: `tq1`(**P0** blanking+crack TSTOP完走・**red_lavie停止でブロック中**) / `cttj`(**bug** red_lavie復旧・要人間) / `b41` `uj2` `erw`
- **brv**: `cae/inc094_openradioss_continuous_te_deck.md`(T020デック構文教訓)
- **過去トラ**: T020 / T037(tri-track: OpenRadioss=red_lavie担当)
- **K10実績**(`k10_openradioss_te_state.json` **6/13時点の歴史値**): 総3069サイクル。press_blanking n=2903 avg_reward 0.973（成熟）/ stripper・bending 各n=83 avg 0.15（未成熟）
- **2026-07-05検証結果**: ①red_lavieは**7/1の2連続TIMEOUT以降CPU100%+クロック597MHz固着**、echoジョブすら完了不能=4日間実質停止（孤児エンジン残存疑い・実機での掃除+電源プラン確認が必要 → bd `cttj`） ②ローカルコンテナは消失していたが**7/5にイメージキャッシュから再作成済み**（starter/engine/デッキ健在・`docker exec ... bash /work/start_engine.sh <N>`可） ③run37「10hチューニング実行中」表記は4/30の古いstatusで**現在は動いていない**

### 7.5 Moldflow風 簡易解析 — 🔴 自動レポート停止中（当日インシデント）
- **bd**: `3qu`(Phase7) / `kwr`(epic v002) / `3z1`(**P0** T019意味ゲート)
- **brv**: `cae/inc089_lavie_fill_video_k10_pull.md`
- **過去トラ/個票**: `quality_incident_report_20260705_moldflow_reports_stopped.md`（当日）
- **現在**(`k10_tri_track_cae_status.json` 21:14時点): **openfoam_lavie = SKIP_OFFLINE fail_streak 43**（LAVIE計算サービスプレーン:8111/:5682停止、Tailscale ping自体は生存）。K10フォールバックタスクの0x80070002は修理済みだがLAVIE実機側は**人間による起動が必要**

### 7.5.1 2026-07-07 追記（Fable5最終日）

- **メカRL**: supervisor は `walk_auto` cycle2 学習中（08:57時点、cycle1は転倒でdefault_stall適用）。§7.1のwalk_tier1c cycle3とは別ラン
- **OpenRadioss tri-track**: red_lavie 本日 press_blanking_assy **fail_streak=5**（09:59時点）— 原因調査済み(Fable5 7/7):
  - **直接原因=物理発散(既知の支配的故障モード)**: 接触不安定→要素破断カスケード(≈31k〜33k件)→NODAL VELOCITY停止。全件 t≈0.95〜1.04ms で停止(ゲート要求18.13msに遠く未達)、ERR≈-99.5%、付加質量DM/M 36→59(=3600〜5900%、質量スケーリング暴走)。5月DOEでも109/187が同モード
  - **連敗の背景**: ①DOEが低速域(1851〜2709mm/s)を抽選中 — 7/1のSUCCESS 2件は4602/6096mm/s(高速はt≈1msの爆発前に工程完了) ②T050/T051で意味ゲート厳格化(t_final≥18.13ms+TSTOP必須) → 従来より成功率が下がり連敗が出やすい ③7/6〜7/7未明のERROR 4件はT051版数不整合の偽ERROR(ペア配布で解消済み、04:33以降は正しくFAILED+run_metrics付き)
  - **red_lavie実機は健全**: 各試行1〜1.6h完走・returncode 0・温度正常。インフラ対応不要
  - **推奨**: 約80分/試行ペースで**14時頃に8連敗自動停止+Telegram**が発火見込み。(a)DOEサンプラをpunch_speed≥3000mm/sへ誘導(bd起票要) (b)低速域はデッキ対策(質量スケーリング目標DT・INTERFACE 1接触・破断基準)とセットで再開 (c)ゲート緩和は禁止(FMEA#2)
  - T051文書の「punch_speed低め優先」推奨は撤回済み(同文書に追記)
- **樹脂充填 tri-track**: openfoam_lavie 復旧済み・SUCCESS継続（n=91, fail_streak=0）— **ただし監査(同日)でKPI非物理+学習不在が判明**: SUCCESSの50%が充填率>110%（VOF発散をSUCCESS扱い）、パラメータは一様乱数再抽選のみ。個票 `quality_incident_report_20260707_resin_fill_kpi_nonphysical_no_learning.md`。成熟度評価は物理妥当性連動に是正済み（精度L4→L3に自動降格）。**エンジン側物理ゲート+最小学習機構+ゴールデンケースが次の必須作業**（bd起票要）
- **成熟度評価リファクタ**: `commercial_benchmark_maturity.py` を宣言的ルール+鮮度ゲート化（CHANGELOG 2026-07-07参照）。**bd起票は未実施**（本セッションからbd実行不可）— 次セッションで `bd create` すること
- **注意**: `cae_te_log.json` は全体書き換え方式。別プロセスから読む場合は必ずリトライ読込（`_read_json_tolerant` 参照実装）を使う

### 7.5.2 2026-07-06 フリート障害と復旧（T051〜T054・全五層記録済）

- **[T051]** red_lavie gates版数不整合の偽ERROR → hasattrガード+**ペア配布ルール恒久化**（プロトコル§7.1）。ペア配布は7/7未明完了。手順書 `T051_GATES_VERSION_MISMATCH_20260706.md` / brv `cae/t051-red-lavie-pair-deploy-traps-20260706.md` / bd `tq1`
- **[T052]** ThinkPad L590 xrdp真っ黒（3重原因: 資格情報AUTHFAIL+max_bpp+Wayland残留）→ 解決。Obsidian `60_PC_Logs/T051_T052_fleet_recovery_and_deploy_20260706.md`
- **[T053]** DXF2STEP S1偽FAIL 6層構造の完全解決 → §7.3参照。bd `5yk`
- **[T054]** K10本体が1日3回クラッシュ(Kernel-Power 41)・GPU学習高負荷相関 → supervisor U5 26hデッドロック等の二次被害と復旧2点セット手順を記録。**T039(WAL破損)再発→pg_resetwal×2で復旧、reindexdb未完(要再実行)**。熱/電源/メモリ調査は未完
- **bd差分**: 更新 `tq1`/`5yk`/`ip4`、新規 `9tgj`/`7c62`（iy63/ip4含む起票は最終日引継ぎ§0-5で完了済）

### 7.6 横断アラート
- **fem_impact_thinkpad**: ~~FAILED_NO_EVOLUTION streak 4~~ → **2026-07-05夜 T049として根治**（pipefail+ls無言即死・詳細はtrouble_history [T049]）。QC実測値KPI化・意味ゲート自動停止(全track・連続8失敗で停止+Telegram)実装済。bd `e3dn`
- CETOLのbd未追跡は解消済み → bd `iy63`(L4/L10実装。**7/7: L4 AP242セマンティックPMIパーサ実装完了** — 手順書T051追記参照。残: L10 FreeCADループ実機確認)
- **K10ハード安定性(T054)**: 熱(NUCBOX)/電源/メモリ(mdsched)の切り分け未完・学習中の温度監視推奨 — 再発時はEvent 41/6008/1074を最初に確認

## 8. ロードマップ

- CAE北極星: プレス部品3D → Moldflow級充填 + CETOL 6σ級公差 + OpenRadioss曲げ/打ち抜き → **順送金型開発**（T019/P025）
- メカRL: walk習得 → run/stairs_climb（`skill_requests.json`投入待ち・U5自動）→ 30体×5スキル
- Moldflow: `docs/MOLDFLOW_CAe_ROADMAP.md`
- AI体制: 2026-07-07 Fable5終了 → ChatGPT 5.5(新機能)/Opus 4.8(設計・レビュー)/Codex(実装)/ローカルLLM(定型) 分担 = プロトコル§4〜6
