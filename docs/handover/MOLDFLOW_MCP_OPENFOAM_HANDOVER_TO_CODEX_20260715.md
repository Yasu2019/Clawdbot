# 引継ぎ: Dynabook Moldflow MCP操作 + メインLAVIE OpenFOAM操作 + 比較評価 (Fable5/Cowork → Codex)

作成: 2026-07-15 Fable5 (Cowork session)
北極星: T019/P025 — プレス部品3D → Moldflow級充填 + Cetol6Sigma級公差 + OpenRadioss曲げ/打ち抜き → 順送金型開発。
**作業前必読**: `data\workspace\memory\trouble_history.md` (T019最優先, **T065新規**, T064, T060, T058, T056, T055, T051) / `data\workspace\PROMISES.md` (P023/P025) / `AGENTS.md` / `docs\LOCAL_LLM_CODING_PLAYBOOK.md` / `data\workspace\memory\success_cases.md`

---

## 0. 経路制約(最重要・実測済)

- **Cowork(Claude)サンドボックス → Tailscale網(100.x)は到達不可**(2026-07-15 再実測: connect_ex=101)。
- **Codex/CLIはK10ホスト上で動くため到達可能** — 本引継ぎ作業はCodexが適任(2026-07-12引継書の判断を踏襲)。
- ネットワーク疎通は `Test-NetConnection` 禁止(INC-147)。5秒バウンドのTcpClient/socketを使用。
- Cowork併走時の注意: サンドボックスのマウントはキャッシュ不整合あり(T055。本日再確認: 編集直後のファイルが行途中で切れて見える)。git/実行はホスト側で。

## 1. Dynabook Moldflow MCP — 現在地

### 1.1 実機情報(確定値)

| 項目 | 値 |
|---|---|
| Host | DESKTOP-UOVCG4T (Dynabook) / user: mec21 |
| Tailscale IP | 100.98.133.40 |
| satelliteワーカー | http://100.98.133.40:5683 (POST /jobs, type=shell/cae_trial, max_timeout 180s) |
| Moldflow MCP | http://100.98.133.40:8765/mcp (streamable HTTP, DNS-rebinding保護あり=Host必須一致) |
| MCP設置先(Dynabook) | G:\moldflow_bridge (venv: G:\moldflow_bridge\.venv) |
| Synergy | C:\Program Files\Autodesk\Moldflow Insight 2010\bin\synergy.exe (v09.03.4.0) |
| COM ProgID | **synergy.Synergy** (32bit cscriptでPASS済 2026-07-12) |
| solver | C:\Program Files\Autodesk\Moldflow Insight 2010\bin\runstudy.exe (未実行・存在未確認) |
| License | NLM 27000@DESKTOP-UOVCG4T UP / adskflex UP / feature 77700MFS_2010_0F |
| 注意 | C:空き約13GB。生成物はG:へ。RDP黒画面残件(fEnableWddmDriver=0+再起動 未実施) |

### 1.2 検証済み vs 未検証(正直な現在地)

- 検証済み: MCP initialize/list-tools、COM CreateObject(32bit)、ライセンス稼働 — **通信層のみ**。
- 未検証: `moldflow_new_study`(メッシュ)・`moldflow_configure_study`(材料/ゲート)・`moldflow_start_analysis` 等のwrite系COM呼び出しは**実機未実行**。2010実APIと差異の可能性(FullKit警告どおり、実機付属API Referenceと `data\commands` サンプルを一次仕様書とする)。
- 本日時点で到達性未確認(bat未実行のまま引継ぎ)。まずSTEP0疎通から。

### 1.3 K10側の実装資産(本日作成、フルパス)

| ファイル | 役割 |
|---|---|
| D:\Clawdbot_Docker_20260125\scripts\RUN_MOLDFLOW_DYNABOOK.bat | ワンクリック: 段階1-5自動実行→コマンド受付ループ(15s poll, 最大6h, STOPファイルで終了) |
| D:\Clawdbot_Docker_20260125\scripts\k10_moldflow_dynabook_runner.py | 段階式ランナー(標準ライブラリのみ/全段バウンド/fail-fast)。生MCPクライアント(urllib, SSEパース, Mcp-Session-Id)内蔵 |
| D:\Clawdbot_Docker_20260125\scripts\k10_moldflow_runner_dispatch.py | ループ用ディスパッチャ(inbox\command.json → ランナーのみ実行可のホワイトリスト) |
| D:\Clawdbot_Docker_20260125\scripts\moldflow_runner_inbox\ | command.json投入口(書式: {"args":["--stage","auto"]}) / STOP / 実行ログ |
| 結果出力 | D:\Clawdbot_Docker_20260125\data\workspace\moldflow_bridge\runner_results\<timestamp>\stage*.json + run_summary.json |

ランナーの段階: 1 preflight(TCP/MCP/COM/readiness) → 2 enable_write(必要時: write版server.py配布+`MOLDFLOW_ENABLE_WRITE_OPERATIONS=1`でkill-by-port再起動) → 3 upload_cad(Moldflow.stl→G:\moldflow_bridge\work\cad\) → 4 new_study(CLAW_SCRATCH_20260715/fill_01, 3mm) → 5 export_materials(PP候補抽出)→停止。個別: `--stage configure_analyze --manufacturer <M> --trade-name <T> --node <N> --study-path <G:\...sdy>`。

- ブリッジ本体(K10マスタ): D:\Clawdbot_Docker_20260125\data\workspace\moldflow_bridge\moldflow_mcp_server.py(write系ツール実装済・SHA256照合配布が前提)。Dynabook側G:\moldflow_bridgeのserver版数は**未確認**(段階1のtools/listで判定)。
- CAD: D:\Clawdbot_Docker_20260125\data\cae_te_workspace\runs\TRIAL_CUSTOM_STL_SNAPPY\constant\triSurface\Moldflow.stl (27,684 bytes, SHA256 5EFE696D83B277FA7BEC80987F5E7E6A85F67626DCFC85CFFA561A1E6D89C3AD)

### 1.4 ユーザー承認済み事項(2026-07-15本セッション)

1. write解禁OK — ただし**使い捨てStudy限定**(G:\moldflow_bridge\work配下の新規プロジェクトのみ。既存SDY非破壊)+readiness_gate PASS後。
2. 材料はDB一覧→PP系候補提示→確認後に設定(**商用材料カードの複製・転記は禁止のまま**)。
3. 残課題: injection node(ゲート節点)照会ツール未実装。メッシュ後の節点特定方法は2010 API Reference(`data\commands`)で確認してから実装(推測COM実装禁止)。

### 1.5 禁止事項(HANDOVER_20260711継承)

Autodesk_NLM_Restart.batの安易な実行 / License正常時のサービス再起動 / PID未確認kill / 全LAN向けHost許可 / DNS rebinding保護の無効化 / COM未確認の解析API実装 / dry-runを実Moldflow成功と表示 / 無制限リトライ / 「Moldflow同等精度」の主張(L6相関未達のため)。

## 2. 秘密鍵・トークンの**場所**(値は本書に書かない)

| 対象 | 場所 |
|---|---|
| satelliteワーカートークン(X-Satellite-Token) | 正: 各ノードの .env(Dynabook: C:\dynabook_satellite\.env の SATELLITE_JOB_TOKEN)。K10側の取得実装: scripts\k10_satellite_dispatch.py の load_token()。既存値のハードコード例: scripts\deploy_dynabook_lhm.py / scripts\deploy_dynabook_monitor.py / scripts\k10_moldflow_dynabook_runner.py(環境変数SATELLITE_JOB_TOKEN優先) |
| OpenClaw Gateway token | D:\Clawdbot_Docker_20260125\CLAUDE.md 内(Critical Constraints節) |
| Dynabook RDP資格情報 | K10のmstsc保存済(TERMSRV/100.98.133.40, user mec21)。不調時は `cmdkey /delete:TERMSRV/<ip>`→手入力(T052) |
| SSH鍵(FullKit経路・現在未使用) | 生成スクリプト: projects\Moldflow2010_Remote_MCP_FullKit\powershell\07_generate_ssh_key.ps1(鍵は%USERPROFILE%\.ssh)。現行はHTTP(worker/MCP)経路のためSSH不要 |
| Moldflow MCP自体 | トークン無し。防御はTailscale網+Host/Originアローリスト(100.98.133.40:8765/127.0.0.1:8765のみ) |
| K10配布サーバ | :8123 = scripts\ を配信(scripts\start_k10_fleet_script_server.ps1)。配布前ゲート: scripts\verify_fleet_script_server_gate.ps1 |

## 3. メインLAVIE OpenFOAM側 — 現在地

- 直近状態: `tri-lavie-resin_fill_cad` は**連続SUCCESS**(2026-07-14 cae_te_log.json実測)。
- ノード情報・割当の正: docs\cae_tri_track_dispatch_policy.md / docs\fleet_job_allocation_20260613.md(CAEは Main LAVIE + Red LAVIE + ThinkPad のみ)。
- 主要スクリプト(すべて D:\Clawdbot_Docker_20260125\scripts\):
  - cae_te_engine.py (5100行, proxy solver本体。L5質量収支KPIコード実装済・LAVIE配布待ち)
  - cae_te_remote_trial.py (単発試行CLI) / k10_satellite_cae_dispatch.py (--host lavie で1試行ディスパッチ)
  - moldflow_step_case_builder.py (T064恒久対策入り: keep点レイキャスト/mm→m/部品表面ゲート/体積比>1.5停止)
  - moldflow_doe_real_trials.py (S001: 実測RSM-DoE, 連続3失敗停止+state.json再開)
  - moldflow_cavity_mesh.py / moldflow_closed_cavity.py / moldflow_gate_advisor.py / resin_fill_param_learner.py
- ワークスペース: D:\Clawdbot_Docker_20260125\data\cae_te_workspace\(runs/ results/cae_te_log.json experiments/)
- 板状部品は blockmesh_bbox 経路(CI実績)を優先。snappy経路はT064の3層罠(locationInMesh外部連通/単位/ゲート位置)に注意。
- 実解析の正道: scripts\run_custom_stl_fill_video.bat(interFoam再実行→実VOF動画→Telegram)。演出レンダ(_render_weldline_fast.py)の配信は禁止(T063)。

## 4. 比較評価(Moldflow実機 vs OpenFOAM proxy)

- 目的: Dynabook実Moldflowの結果を**ゴールデンリファレンス**としてK10 CAE Studioへ供給し、proxy(OpenFOAM)のL6実測相関を進める。
- 受け口: scripts\moldflow_cae_studio_api.py (**:8776**, /api/golden-case, /api/maturity, /api/golden-error-trend)。UI: data\workspace\apps\moldflow_cae_studio\ (portal :8088)。ポートは docker-compose.yml 実測値を確認してから使う(T008)。
- 精度計画: docs\moldflow_accuracy_l3_to_l10_te_plan.md — 現在地L3。**最大ボトルネック=L6(実測相関1件、ユーザーデータ待ち)**。
- 比較記録の必須項目(AGENTS.md CAE規定): 形状寸法/メッシュ統計/材料同定/ゲート数・座標(節点)/成形条件/solver版/収束・有界性証跡/結果ファイルパス/**商用リファレンスとのKPI表**。物理境界・完走・再現性・宣言誤差内をすべて満たすまで「validated」と呼ばない。
- KPI例(bridgeのexport_resultsが返す): fill_time_sec / max_injection_pressure_MPa / max_clamp_force_ton + 充填画像PNG(G:\moldflow_bridge\work\results\)。

## 5. 併走中の別件(状況共有)

- OpenRadioss T065 Phase1完了(gates誤検知修正・テスト5件PASS)。**Phase1検証bat未実行**: scripts\RUN_OPENRADIOSS_T064_PHASE1.bat(T051ペア配布→手動1試行)。合格基準=失敗理由がshear_kpi_parametric_onlyのみ。Phase3(実KPI抽出)完了までループ再開禁止。
- gatesバックアップ: scripts\cae_self_growth_gates.py.bak_t064gates_20260715。検証テスト: scripts\_t064_gates_verify_test.py(引数にgatesパス)。

## 6. 記録・トラッキング(必須運用)

- **Beads(bd)**: タスク管理はすべてbd(TodoWrite/markdown TODO禁止)。`bd prime`→`bd ready`→claim→close→**`bd dolt push`+`git push`まで**がセッション完了条件。起票すべき項目: ①Moldflowブリッジ段階1-5実行と結果記録 ②injection node照会ツール(API Reference確認後) ③T065 Phase2(FAILURE START 4223件調査) ④Phase3(実KPI抽出) ⑤L6実測データ受領待ちフォロー。北極星の想起: `bd remember --key cae-north-star-t019`
- **ByteRover(brv)**: 高価値知見は `brv curate`。参照実績キー例: `t055-cowork-mount-git-traps-20260710` / `dxf2step-s1-false-fail-6layer-fix-5yk-20260706`。本引継ぎも要curate(推奨キー: `moldflow-mcp-codex-handover-20260715`)。
- **Obsidian**: 実稼働に影響する修正はインシデント完全ノートを `D:\Clawdbot_Docker_20260125\data\state\Obsidian Vault\60_PC_Logs\` へ(QC工程表/FMEA/FTA/5Why/Fishbone込み、stub禁止。規定: .cursor\rules\obsidian_incident_recording.mdc)。T065のObsidianノートは**未作成=Codex側で作成要**。
- **INCIDENT_LOG**: docs\INCIDENT_LOG.md へINC-XXX形式(最終番号を確認して採番)。T065分も未記載。
- **trouble_history**: data\workspace\memory\trouble_history.md — T065まで記録済(2026-07-15)。
- **success_cases**: 難問解決時は data\workspace\memory\success_cases.md へ5項目型で追記(義務)。

## 7. 最初の一手(推奨手順)

1. `bd prime` → 上記①〜⑤を起票・クレーム
2. K10から疎通(5秒バウンド): 100.98.133.40 の 8765/5683 → 全滅ならユーザーへDynabook電源/Tailscale確認依頼(推測で進まない)
3. RUN_MOLDFLOW_DYNABOOK.bat 実行(または runner を直接 `--stage auto`)→ runner_results\ を確認
4. 段階5のPP候補をユーザーへ提示→材料確定
5. 2010 API Reference(Dynabook実機 `data\commands`)で節点照会COMを確認→ツール追加→configure_analyze
6. golden-case登録→OpenFOAM proxy同条件試行→KPI表で比較→L6相関へ
7. 各段階の結果を bd/brv/Obsidian/INCIDENT_LOG へ記録し、git push で完了

---
*本書に秘密の値は含まない(場所のみ)。トークン値をログ・チャット・コミットメッセージへ出力しないこと(P023/AGENTS.md)。*
