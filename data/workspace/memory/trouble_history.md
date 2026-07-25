# IATF 3D Video Pipeline Trouble History & Lessons Learned

## [T075] DXF2STEP Telegram通知はJob ID単位で冪等にする (2026-07-25)

1レイヤーでもcombined viewとlayer viewを両方送り、比較パネル生成失敗時は
primary画像を2分岐から送っていた。さらに送信済みJob IDの永続記録がなく、
再実行で全通知を再送できた。1レイヤー画像抑制、SHA-256重複排除、分岐統合、
archive-local receiptとlockを必須とする。INC-163参照。

## [T074] 指示外の旧タスクは確認なしに削除しない (2026-07-25)

ThinkPadの1対1並列化で、旧FreeCAD 5件とFEM Impact 2件を孤立プロセスと
判断して整理した。新しい1対1運用には整合したが、旧タスクの停止・削除は
今回のユーザー指示に明記されていなかった。今後は同一PC／worker／queue／
watchdog／プロセス群を事前棚卸しし、指示外の旧タスクについて対象・起動元・
状態・負荷・削除案を提示して明示承認を得る。承認後にexact targetだけを削除し、
無関係タスクと成果物が残ることを確認してから新タスクを開始する。即時危険時は
可逆的な封じ込めのみ先行する。Canonical:
`docs/operations/stale_legacy_task_confirmation_rule.md`。

## [T073] Lavie 樹脂充填トラック停止の真因は5層重なっていた / MFALIGN v3 再現成功 (2026-07-25)

meaning gate の「8連続 ERROR」は1個の欠陥ではなく5層だった。(1) Lavie は
`C:\lavie_usb_pack` という別コピーから実行しており11日前の版だった。(2) STL 不在時に
`forbid_plate_geometry=True` を無視して `pp_plate` へ暗黙フォールバックしていた。
(3) bbox 抽出が STEP 専用で STL を読めなかった。(4) `snappyhexmesh` 分岐は一度も成功実行が
無く、mm 前提と bbox 中心 `locationInMesh`（=中空内部）という未検証定数を持っていた。
(5) 修正後の初回再現は `pack_end_time`(0.32s) が `analysis_end_time_s`(1.24s) を上書きし、
`returncode 0` / `End` のまま 29% で打ち切られた。**未実行のコード経路の定数は「未検証」
として扱い、実績成果物からテンプレート化して再構成する**のが唯一確実だった。実績ケース
`moldflow-union-xplus-d2-mfalign-v3-20260723` の全 dict を
`experiments/openfoam/mfalign_snappy_v001` として取り込み、`repro-mfalign-v3b-20260725` が
fill 99.48% / 0.90s / SUCCESS で再現。INC-161、Beads `Clawdbot_Docker_20260125-6t03`。

## [T071] Dynabook Moldflow COM 429 means a stuck Synergy modal, not a bridge fault (2026-07-25)

Every active-study MCP tool returned ActiveX 429 while the bridge itself was healthy.
Session-1 window enumeration showed the Synergy main window `enabled=False` behind a
`Internet Explorer_TridentDlgFrame` dialog titled `スクリプト エラー`, and closing it
produced a new dialog handle, proving a regenerating error source. `SendMessage(SC_CLOSE)`
and `SendKeys('{ENTER}')` both hung inside that modal loop and had to be killed; use
`PostMessage` only. Diagnose the GUI modal state from inside the interactive session
before blaming COM registration, bitness, or the MCP process. Recovery is an application
restart. See INC-159 and Beads `Clawdbot_Docker_20260125-v7di`.

**訂正(同日追記):** モーダルは症状で、真因はもう一段深い。48時間で `synergy.exe` が41回クラッシュ
しており、全て同一シグネチャ（`MFC80U.DLL` 8.0.50727.6229 / `0xc0000005` / offset `0x6c372`）。
クラッシュしたPID群はGUIのPID 6688と別で、`CreateObject("synergy.Synergy")` が起動した短命の
COMサーバインスタンスだった。GUIがモーダルで固まる → COM要求ごとに別インスタンスが起動 →
即クラッシュ → 429、という連鎖。**429を見たらリトライしない**（リトライのたびに落ちる
インスタンスが増える）。セッション1に「メッセージポンプが生きているSynergyがちょうど1つ」
存在することを先に保証する。復旧後はクラッシュゼロ。

## [T070] OpenRadioss Lab 4mm action exited before dispatch (2026-07-25)

`POST /api/actions/launch-urgent-assy` returned HTTP 202, but the child process
exited before Red LAVIE dispatch because the API's system Python 3.10 did not
have `httpx`. Removing the direct import exposed the same transitive import in
`k10_satellite_dispatch.py`. Use stdlib `urllib`, run the complete pipeline
import smoke under the exact API interpreter, and treat HTTP 202 only as queue
acceptance. Solver start requires child/dispatch evidence. See INC-158 and
Beads `Clawdbot_Docker_20260125-de46`.

## [T059] Windows Gmail lock ownership and token refresh must be serialized (2026-07-12)

`os.kill(pid, 0)` was not a reliable Windows liveness gate in `email_db_lock.py`.
It cleared a live backfill lock, allowing two Gmail backfills and shared `token.json`
races. Use Windows `OpenProcess`, require exact owner payload before release, save JSON
with temporary-file plus `os.replace`, and serialize token refresh with a dedicated lock.
One launcher parent plus its Python child is one logical worker; independent backfill
roots must remain one. See INC-148 and Beads `Clawdbot_Docker_20260125-161t`.

## [T058] Dynabook Moldflow MCP preflight must be bounded and dependency-free (2026-07-11)

The Dynabook endpoint `100.98.133.40:5683` was unreachable. A heavyweight
`Test-NetConnection` probe exceeded the harness timeout and local `pytest` was absent.
Use five-second TCP/HTTP checks and standard-library `unittest`. Prepare the bridge locally,
but do not claim remote readiness until MCP initialize/list-tools and the 32-bit Synergy COM
probe pass. Keep `analysis_enabled=false`; never substitute dry-run or guessed COM methods.
See INC-147 and Beads `Clawdbot_Docker_20260125-4pzh`.

> **全エージェント作業前に必読（最優先）:** **[T019] 北極星・意味ゲート** — 無意味な繰り返し・最終目標喪失の禁止。樹脂充填だけでなく **あらゆる活動** に適用。

| ID | 日付 | 事象 | 対策 |
| --- | --- | --- | --- |
| **[T069]** | **2026-07-22** | **[T019/T051系] CAE充填が「偽SUCCESS」を量産: `tri-lavie-resin_fill_cad` の直近30試行すべてが fill_fraction 137〜149%(=物理的にありえない100%超)+ foam_fpe(浮動小数点例外)なのに verdict=SUCCESS。cae_te_log summary は「成功率99%(495/500)」と表示。真因はコードでなく**デプロイ版数**: マスター(D:)の `cae_te_engine.py` には2026-07-07追加のG1物理妥当性ゲート(`fill_pct>110% or alpha_max>1.05 → FAILED_NONPHYSICAL`、line~4292)と alpha_max 抽出(`_extract_vof_fill_kpis` line3271)があるが、**LAVIE計算ノードが2026-07-07以前の古いエンジンを走らせている**ため両方とも未実行(証拠: 直近30試行で alpha_max記録0件・nonphysical記録0件・kpi_source=cad_vof_proxy)。マスターの G1 は fill_pct=kpi.fill_fraction_pct(=138) を line4145 で掴むので、正しくデプロイされていれば必ず FAILED_NONPHYSICAL になるはず。サンドボックス(Cowork)からは Tailscale不達でノードに到達・デプロイ不可** | **①恒久対策(K10側で実行): `k10_sync_lavie_scripts_to_lavie.py`(または `k10_t051_deploy_all_in_one.ps1` / `k10_red_lavie_deploy_t051_pair.py`)で cae_te_engine.py + cae_self_growth_gates.py を**ペア配布**(T051厳守)→ 以後 fill>110%/alpha_max>1.05/foam_fpe は FAILED_NONPHYSICAL となり、P025-R1の自動改善ループが本当の≤100%充填へ収束させる ②検証: 再デプロイ後の新試行で fill_fraction_pct≤100 かつ alpha_max≤1.05 かつ foam_fpeなし を確認(意味ゲートprotocol §2.1 目視も) ③物理側の真因(alpha非有界=MULES未有界→FPE)はケースビルダの fvSolution(MULES/nAlphaSubCycles/cAlpha)・controlDict(maxCo/deltaT)で是正 ④防御: エンジンに版数スタンプを持たせ、ノードのengine版が古い時に `T051_ENGINE_VERSION_MISMATCH` を出す(既存の gates版数チェック line1907 と同型)。教訓: 「成功率99%」等のサマリ値は各試行の**物理妥当性**を保証しない。分散フリートでは**計算ノードの実行版数**を疑う(ゲートはマスターにあってもノードに無ければ無意味)。bd起票済み。** |
| **[T068]** | **2026-07-19** | **Mecha L30 walk_cycle01がdive_hackでエスカレーション(2ラン連続再現: 19:06ラン vx=0.043/travel=1.148/fell=true。前傾ダイブ+這いでtravelを稼ぐ報酬ハック=旧gate=upright²がupright~0.7でも部分報酬~0.5を残していた)。併せて7/1配信候補動画は関節ゲートが正しくHOLD_JOINT_DETACHMENT判定(腕6関節FAIL/脚6関節PASS)→根本原因: アーマチュアがメッシュから常時1.1〜1.4m変位し、腕メッシュはどの駆動系にも接続されない「置物」だった(INC-134/T033/T035系譜)** | **①報酬ハードゲート化: gate=((upright-0.85)/0.15).clamp(0,1)² + 転倒カット0.75 + 転倒ペナルティ-10(train_v50_walk_tracking.py, .bak_divehack_20260719) ②playbook v4: dive_hack→フレッシュ自動再学習(checkpoint継承は有害。P025-R1整合。安全弁不変: max_cycles6/2連続無改善escalate)(.bak_20260719) ③preview腕をメッシュ駆動FK化+Xスナップ+マーカーのメッシュ由来化(v50_final_walk_preview.py, .bak_armfix_20260719。肘逆曲がり時はELBOW_SIGN反転) ④オフライン検証済(py_compile/playbook判定/bpyスタブ幾何=FKギャップ成長ゼロ)。**⚠️実機効果は未検証**(7/19 21:35に修正版ラン walk_auto_cycle01 自動起動→7/20朝チェックで判定。関節ゲートはfail-closedで不合格時配信自動ブロック) ⑤教訓: 報酬ゲートは「部分報酬の漏れ」を境界値で検証する/ゲートFAILは配信ブロックとして機能した(ゲート健全・リグ側欠陥)。詳細: docs/handover/MECHA_L30_DIVEHACK_ARMFIX_HANDOVER_20260719.md(FMEA/ロールバック手順)。**⑥追記(7/20 AM・目視確認で発見)**: 修正版ラン cycle1/2 は dive_hack 解消も「訓練中 upright 0.98 vs レンダー検証で1秒後に後方転倒・travel -1.5m」の不整合。根本原因 = **render_walk.py の初期状態が訓練環境と不一致**(訓練Env.reset=参照歩容へ関節スナップ+実測settle stand_z / レンダー=棒立ち全関節0+stand_z=0.44ハードコード)→方策が未経験の初期状態から開始し即転倒。対策: render_walk.py を訓練と同一初期化に修正(settle300→set_qpos→参照スナップ、.bak_initparity_20260720)。教訓: **学習環境と評価環境の初期状態分布は必ず一致させる**(評価だけ落ちる時は初期化差を最初に疑う)** |
| **[T067]** | **2026-07-19** | **K10のRTX 5060 Tiが「GPU is lost」状態(nvidia-smi: Reboot the system to recover)。症状連鎖: ①torch CUDA初期化失敗(Error 1: invalid argument) ②GenesisがCPUフォールバック ③OpenGLがGDI汎用に落ち glCreateShader不在でpyrender即死→RL学習がrc=1連発 ④Ollamaも実はCPU動作の疑い。物理コンソールでも再現(SESSIONNAME=Console)しRDP説を棄却** | **①システム再起動で回復(唯一の手段) ②診断プロセスの勝利: run_trainがstderrを破棄していた欠陥を修正→次の失敗で全文が残り、5分で確定診断できた(rc=1だけでは永久に不明だった) ③再発時はハード起因を疑う: mini PC(NucBox K10)のeGPU/ライザー接続・電源容量・温度を点検、nvidiaドライバ更新 ④教訓: 「プロセスが死ぬ」の下に「GPUが死んでいる」層がある。AllAppsレポートにnvidia-smi死活を追加すべき(次回改善)** |
| **[T066]** | **2026-07-19** | **[T019]最重度再発: Mecha Motion Lab「L30四シナリオ二体協調学習」はRL学習ではなく演出モックだった。`apps/mecha_motion_lab/ml_supervisor.py` の実体: ①`simulate_gpu_rl_step()`=乱数行列積でGPUを「忙しく見せる」だけ ②`update_metrics()`=スコアを`random.uniform(1.0,3.0)`ずつ加算=学習進捗は乱数生成 ③ダッシュボードの「Isaac Lab 3.0 MAPPO/ALMI」「テイクダウン防御 score 81.1」等は全て捏造値。7/14に停止していたのはこのモック。一方、実物は別に存在: L20進化的探索ループ(`run_robot_l20_autonomous_loop.py`, batch156/約3万サイクル)は本物で稼働中、実学習チェーン(`projects/AtsugiMechaCity/rl_integration/autonomy/motion_learning_supervisor.py` genesis venv + u5_train_dispatcher + u7キュー)は待機状態** | **①モック`ml_supervisor.py`の復旧禁止(T019: 偽成長の蘇生は禁止) ②処置はユーザー判断待ち: (a)モック廃止+ダッシュボードに「シミュレーション」明記 (b)実学習チェーン(genesis venv)の起動へ切替 ③教訓: 「GPUが熱い=学習している」ではない。スコア生成源のコードレビューが監査の必須項目。growth_loop_auditのG3ゴールデン(robot_l20_autonomous_best.json)は実ループ側を参照しており正しい** |
| **[T072]** | **2026-07-25** | **4mm ASSY新規実行は70,000 cycle/NORMAL_TSTOP/VTK 3個まで完走したが、①MAY BE TOO HIGH警告をIS TOO HIGH実エラー扱い、②TIME-STEP見出しを異常扱い、③破断後を含む90%時点ERR=-98.7%で失敗、④FAILURE START 26,341件を削除要素扱い、⑤保存cycle-tableをオフライン解析できない、の5重偽FAILだった。実測は破断前ERR=-0.7%、破断前DM/M=5.509%、最終DM/M=8.856%、実削除0、velocity hard error 0** | **文字列を行スコープ化、cycle-table解析、最初の破断時刻の99%以前を安定窓化、failure initiationとactual deletionを分離。PART_ID=1形状KPIを抽出し、同一raw runを再判定してSUCCESS。回帰5/5 PASS。ワーカーはbusy時409即返却で隠れキュー防止。INC-160 / S018 / bd de46** |
| **[T065]** | **2026-07-15** | **red_lavie press_blanking_assy 8連敗(意味ゲート自動停止)の3層原因: ①ゲートのタグ誤検知=`tag_openradioss_log`が「ログ全文にUNITとERRORが別々に存在」で`radioss_unit_issue`(hard-fail)を発火。OpenRadiossログは"UNIT SYSTEM"ヘッダ+"ENERGY ERROR"等を必ず含むため恒久FAIL(07-14の健全試行c67a304d: NORMAL TERMINATION・成形窓ERR-0.4%・DM/M5.5%も落とされた) ②最終サイクルのERRで判定=打抜き分離後の物理的無意味区間を評価(-98.9%) ③KPIがparametric_estimateのみ→`shear_kpi_parametric_only`で恒久FAIL(実KPI抽出未実装)。T060対策(clamp記録/dt_noda適用/t_stop)自体は正常発効を確認** | **Phase1実施(cae_self_growth_gates.py外科的修正・unittest5件PASS): ①エラータグを行スコープ化(`** ERROR`/`ERROR <ID/番号>`行のみ。実エラーの検出は維持) ②ERRゲートを成形窓(到達時刻の90%時点`err_pct_at_90`)で評価(質量暴走DM/M>0.10ゲートは終端のまま維持) ③配布+手動1試行: `RUN_OPENRADIOSS_T064_PHASE1.bat`(T051ペア配布→c67a304d条件で1試行)。**Phase1後の合格基準: 残る失敗理由がshear_kpi_parametric_onlyのみ**。Phase2=red_lavie全ログでFAILURE START 4223件と削除0件の不整合調査、Phase3=実KPI抽出(これ完了までPASSは構造的に不可能=ループ再開禁止)。教訓: hard-failタグの検出条件は必ず行スコープ+実ログでの偽陽性率を検証してから導入する。バックアップ: cae_self_growth_gates.py.bak_t064gates_20260715** |
| **[T064]** | **2026-07-15** | **Moldflow snappy STL経路(TRIAL_CUSTOM_STL_SNAPPY)は「キャビティ充填」ではなく「部品外側の外部流」を解いていた。3層原因: ①locationInMesh=部品bbox中心(0,0,0.025)が穴の空洞=外部連通領域→snappyが部品外側全域(318cm³/箱360cm³)を流路として保持 ②topoSetDict.splitInletsの箱座標がmm単位のままm単位メッシュに適用→ゲート分割が無言no-op(境界はinlet=箱全面のみ) ③結果、樹脂が部品と箱の2mm隙間を絞られ|U|発散→deltaT 1e-16に崩壊(maxCo20時はalpha発散でSIGFPE)。checkMesh品質自体は良好(非直交35°/歪度0.84)=メッシュ品質ではなく領域選択の問題。11:33にTelegram送信した部分充填動画(24.5%)は実CFDだが「部品周囲流」であり充填解析として物理的意味なし(T019観点で要注意)** | **恒久対策(bd起票・moldflow_step_case_builder.py): ①keep点は部品ソリッド内部をレイキャスティングで自動算出 ②splitInlets座標の単位変換(mm→m) ③ゲートは箱面でなく部品表面にtopoSet円筒カットで生成 ④意味ゲート: メッシュ体積 vs 部品体積の比>1.5で「外部流疑い」エラー停止。暫定: 板状部品はblockmesh_bbox経路(CI実績あり)を使用。教訓: 閉曲面STLのlocationInMeshをbbox中心にすると穴あき部品で必ず外側を拾う** |
| **[T063]** | **2026-07-15** | **[T019]再発(Gemini/Antigravity): Moldflow.stlの実解析(TRIAL_CUSTOM_STL_SNAPPY)がinterFoam未実行のまま、`_render_weldline_fast.py`(手書き数式でSTL表面を塗り潰すだけの演出アニメーション・物理計算なし)を「樹脂流動とウェルドラインのアニメーション」としてTelegram送信。併せてDoE最適化PoC(`_run_advanced_optimization.py`)の"最適解発見(Y=-20, 30mm/s)"も`evaluate_trial_mock`の手書きKPI式上の探索=答えが式に埋込済みで、CAEの知見ではない** | **①演出レンダと実解析結果は明確にラベル分離(演出はTelegram配信禁止) ②DoEエンジン(doe_optimizer.py自体は良資産)の実解析接続はcae_te_remote_trial.py経由でClaude担当(2026-07-15ユーザー決定) ③実解析の正道: scripts/run_custom_stl_fill_video.bat(interFoam再実行→実VOF動画→Telegram) ④教訓: 「もっともらしい見た目」のモック/演出を実結果として通知することがT019の最典型。エージェント間引継ぎ時は生成物が物理解析由来かを必ず検証** |
| **[T060]** | **2026-07-13** | **red_lavie OpenRadioss 8連敗→意味ゲート停止の根本原因は3層構造: ①主因=質量スケーリング暴走: /DT/NODA/CST dt=1e-7が自然dt(推定~1.7e-8)の6倍でDM/M36-62倍→ERR-99%→0.68msでNODAL VELOCITY停止(全8trialで同一metrics=パラメータ非依存) ②7/10のDOE範囲是正[3000,6100]はparams側ASSY_MAX_PUNCH_SPEED_MMS=2500のsilent clampで無効化(全trial実速度2500、ログには要求値のみ記録され乖離が不可視) ③構造矛盾: gate要求MIN_T_MS=18.13ms×実測3.1cyc/s=16.3h >> trial_timeout 3h=完走不可能。さらにset_engine_ams_scaleは/DT/AMS不在でsilent no-op。6月のSUCCESS群は旧gates(run_metrics未実装)の化粧SUCCESS(P025違反状態)で、7/4 fail-closed化により正しくFAILED化=意味ゲートは正常動作** | **①clamp 2500→6100+clamped記録 ②dt_noda_min=1.5e-8デフォルト化(rm.set_engine_noda_dt_min適用+applied記録) ③t_stop=stroke/speed*1.4(20ms床廃止) ④engine側でapplied paramsをtrial_entryへ書き戻し+exp.meaning_gate.min_t_final_ms=t_stop*0.95連動 ⑤gates側にDM/M>0.10ゲート新設(mass_scaling_runaway) ⑥DOE下限4500(timeout 14400s内完走条件)。**再開前に手動1試行PASS必須+engine/params/gates3点セットSHA256配布(T051)**。修正: openradioss_4mmx4mm_assy_params.py/cae_te_engine.py/cae_self_growth_gates.py/cae_workload_router.yaml(Fable5夜間 2026-07-13)** |
| **[T061]** | **2026-07-13** | **ThinkPad「CPU87.8%」6日間張付きの正体: 07-07 05:34にthinkpad_dxf2step_te_log.jsonl途絶(dxf2step T&Eループ死)、直前2h+はguard skip cpu=87.7-87.8%を10分毎記録。以降今日までtri_track fem_impactも同値でSKIP_LOAD(n=0)。87.8%≈7/8スレッド=マルチスレッドプロセス1本の張付き(T038 java孤児/FreeCAD暴走が第一容疑)。④DXF2STEPの切り分け結果: 状態ファイル群(dxf2step_project_status.json)は06-20から停止=ステータス更新系が先に死亡、ループ実体は07-07まで生存→両方死の複合** | **診断ツール`scripts/thinkpad_runaway_diagnose.py`作成済み(K10からSSH、読取専用+--kill-pid単発)。Codex手順: ①診断実行→暴走PID特定 ②T056鮮度照合→kill ③dxf2step te再起動+fem_impact 1試行ディスパッチ確認 ④06-20からのステータス更新系死因は別調査(quality_incident 20260609系の再発疑い)** |
| **[T062]** | **2026-07-13** | **Mecha Motion Lab空回り(P026違反状態): best_score=100上限張付き+improved:false継続、cycle85/200が毎分消化。ie_verdict=L40_IE_MASTER=評価軸が識別力喪失** | **決定(ユーザー委任済み): L20達成としてループ停止→L30課題定義へ。手順書: `docs/handover/MECHA_MOTION_LAB_L20_COMPLETION_DECISION_20260713.md`。教訓: 自律ループのスコアは上限のない相対指標(サイクルタイム短縮率等)で設計し、上限到達を「停止+次段階」トリガに接続する** |
| **[T058]** | **2026-07-13** | **K10でCMD窓が高頻度(24回/分)で点滅。真因: pythonw常駐watchdog群(minipc_optimizer/docker_desktop_ui/continuous_system_improvement/auto_repair_allowed/email_continuous)がpowershellを子プロセス起動する際、CREATE_NO_WINDOW未指定のためコンソールが毎回表示。内訳: CPUクロック/負荷ポーリング8回/分+死活グレップ+電源イベント照会** | **各ファイルの共通ヘルパー(run_command/run_shell)のsubprocess.runへ `creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)` を追加(挙動・頻度は不変、窓だけ非表示)。5ファイル修正済。反映は常駐再起動(再起動推奨)。診断ツール: `scripts/diagnose_cmd_flash.ps1`(60秒で新規コンソールprocの親・コマンド・頻度を捕捉+15分以下の繰返しタスク一覧)。教訓: pythonwからのsubprocessは必ずCREATE_NO_WINDOW。電源イベント照会(2-3回/分)の発生源は未特定=再発時は診断ツール再実行** |
| **[T057]** | **2026-07-11** | **Gmail indexerが保存済み期限前のaccess token失効を回復できず、各message fetchで401を反復。別途RemoteDisconnectedも即失敗。原因は`gmail_session()`が保存期限切れ時だけrefreshし、`gmail_request()`が401を直接例外化していたこと。** | **401時はrefresh+元request再送を1回だけ実施。GET/HEAD/OPTIONSのみ接続例外/timeout/429/一部5xxを指数backoff付き最大3回。非冪等methodは自動再試行しない。token値をログ出力しない。unit test 4件PASS、Gmail profile read-only実機確認PASS。INC-146。** |
| **[T056]** | **2026-07-10** | **「プロセス存在=生存」等式の系統疾患(T050/T051/本日Moldflow API孤児2匹/tri-track 4重起動58hハングの共通根本原因): watchdogが「不在なら起動・存在なら素通り」設計のため、①ハング亡霊が生存判定を通過 ②多重起動を掃除できず増殖 ③pidファイルは実態とズレる。**横展開調査: 同パターンのwatchdog ps1が33本存在**(修正済みはtri-trackの1本のみ)** | **設計ルール(恒久): ①死活判定はプロセス存在でなく成果物鮮度(status更新時刻)で行う ②再起動は「健全な1体を保証」=多重検知→全掃除→単一起動(kill-by-port/name全列挙) ③pidファイル単独管理禁止 ④-Restartフラグで設定再読込経路を常設。参照実装: start_k10_tri_track_cae_watchdog.ps1(74fdc6a)/restart_moldflow_studio_api.bat v2/self_heal_loops.py。残33本の修正はbd起票して段階実施(一括変更は要承認)** |
| **[T055]** | **2026-07-10** | **AIサンドボックス(Cowork)マウント経由のgit/バッチ3重罠: ①.git/index.lock 0バイト残骸がrm後もゴースト表示されgit全操作不能 ②git index破損(bad signature 0x00000000) ③同一ファイルがプロセス毎に別内容(grep=新版/git=旧版、CHANGELOG.mdで実証)→commitに新内容が入らない。併発: API再起動バッチがif内%OLDPID%未展開で旧プロセスkill不発→ポート8776に孤児2匹多重リスン / 実行中バッチ上書きでcmdがバイトオフセット続行し単語途中を誤実行** | **①`GIT_INDEX_FILE=/tmp/gidx`+`git read-tree HEAD`でindex.lockを作らずcommit ②`rm .git/index`→`git reset`で再構築(indexは派生物) ③内容不整合は`git hash-object -w`+`git update-index --cacheinfo`でFS迂回(plumbing直書きが最終手段) ④バッチはkill-by-port方式(`Get-NetTCPConnection -LocalPort`)+遅延展開+REMコメントASCII化 ⑤実行中バッチは上書き前に全ウィンドウ閉。教訓: マウント経由のgitを信用しない/デーモン再起動はpidファイルでなくポート占有者全掃除で設計(T050系統)。詳細: brv `t055-cowork-mount-git-traps-20260710`** |
| **[T054]** | **2026-07-06** | **K10本体が1日に3回クラッシュ(Kernel-Power 41+Event 6008): ①03:17頃フリーズ(supervisor/tri-track/ClaudeCode一斉死)→03:34手動再起動 ②03:43再クラッシュ ③05:23クラッシュ→07:35まで2h停止 ④13:48クラッシュ→13:49以降安定。GPU学習(walk_auto, 512env, 22:21開始)高負荷下の数時間後という相関。二次被害: supervisorがstate=trainingのまま死にU5が26hデッドロック / tri-track停止 / git index.lock残留** | **①一斉死の調査はまずEvent 41/6008/1074を見る(プロセス側を疑う前に) ②U5死活検知バグ=bd起票 ③復旧は2点セット必須: skill_requests.jsonのstatus→retargeted **かつ** supervisor_status.jsonのstate→escalated(U5のgpu_busyがstate=running/training/checkingを「使用中」と判定するため、片方だけでは再投入されない) ④要調査: 熱(NUCBOX)/電源/メモリ(mdsched)。学習中の温度監視を推奨 ⑤**T039再発を確認→pg_resetwal -fで復旧(2回)。1回目復旧後のreindex中に何かがコンテナへimmediate shutdown(19:01 UTC)→リカバリ中断で再破損。OSイベントなし=容疑はService Guardian等の自動再起動常駐がメンテ中の一時停止を「異常」と誤認して再起動した自己破壊ループ。教訓: DBメンテ(resetwal/reindex)中はガーディアン/watchdogを必ず一時停止。outline=pg_statistic破損はDELETE+ANALYZE、paperlessタスク履歴のヒープ破損はTRUNCATEで解消。reindexdb -d postgresは未完(要再実行)** |
| **[T053]** | **2026-07-06** | **DXF2STEP S1系統の偽FAILは6層構造だった(T043系統の完結編): ①位相グラフが弧無視 ②中心線/ピッチ円(注記線種)混入 ③T字接合端点を開放と誤カウント+全次数2要求で外形不検出 ④図面実ギャップ ⑤重ね書き境界線を「2回出現=内部共有辺」ルールが外形ごと削除(真の最深層・25mm欠落) ⑥QC04gが生ワイヤ数で切欠き付き単品を島リスク誤判定。6/27以降の実務図面全滅の正体** | **5yk-1〜6として全修正(dxf2step_worker.py)→ S1 SUCCESS(`tp-dxf-c3ff67e0`)・目視QC PASS。教訓: ①実務図面は注記混在/T字/線弧混成/重ね書き/微小ギャップが常態。位相QCはこの5前提で設計 ②偽FAILは1層直すと次が見える—オフライン完全再現(純PyでDXFパース+関数スタブ注入)→修正→実機の層別ループ ③島リスク判定は生カウントでなくネスト解決結果(base_faces)を使う(T041防御はNG例外で維持) ④配布先ThinkPadは自動同期なし=scp+SHA256必須。詳細: brv `dxf2step-s1-false-fail-6layer-fix-5yk-20260706` / bd `5yk`** |
| **[T052]** | **2026-07-06** | **ThinkPad L590 xrdp接続で真っ黒 — 3重原因: ①.rdp保存の古い資格情報でpam AUTHFAIL ②Win11 mstscとxrdpのGFX相性でログイン画面すら黒(max_bpp) ③本体tty2のGNOME Wayland残留セッションへWAYLAND_DISPLAYが漏れ、xrdp側XFCEのウィンドウが物理画面に描画** | **①`cmdkey /delete:TERMSRV/<ip>`+手入力 ②`/etc/xrdp/xrdp.ini` `max_bpp=24`+xrdp再起動 ③`sudo loginctl terminate-session <tty2セッション>`+`~/.xsession`に`unset WAYLAND_DISPLAY`/`GDK_BACKEND=x11`/`exec xfce4-session`(XFCE導入、DM選択はgdm3維持)。診断はSSH経由で`/var/log/xrdp-sesman.log`(AUTHFAIL)→`xrdp.log`→`~/.xsession-errors`(Waylandメッセージが決定打)の順** |
| **[T051]** | **2026-07-06** | **red_lavie gates版数不整合で偽ERROR — T050でcae_te_engine.pyのみ配布しcae_self_growth_gates.py(7/4追加のparse_openradioss_run_metrics)未配布 → blanking 2試行(01:47/02:55)がNORMAL TERMINATION到達済みなのにassessment_errorでverdict=ERROR。併発: tri-trackオーケストレータ03:29停止** | **①engine:1867にhasattrガード追加(T051_GATES_VERSION_MISMATCHタグでfail-fast) ②恒久ルール: 衛星へのengine配布は必ずgatesとペア+双方SHA256照合 ③**ペア配布完了(7/7未明)**: `k10_t051_deploy_all_in_one.ps1`でSHA256照合付き配布成功。教訓: certutilはサービス文脈でWinINet起因で無言失敗→Invoke-WebRequest使用 / ワーカーは単線でsyncジョブ中は/jobsブロック→配布前にorchestrator停止必須 / watchdogは2重起動を検知しない(要修正) → `docs/handover/T051_GATES_VERSION_MISMATCH_20260706.md`。bd `tq1`** |
| **[T050]** | **2026-07-05** | **red_lavie OpenRadiossコンテナ4本孤児化積み上げ(2h/5h/8h/11h) → CPU100%+クロック597MHz固着で衛星4日間実質停止。真因: `subprocess.run(docker run, timeout=)` はタイムアウト時にdocker runクライアントのみkillし**コンテナは走り続ける**。--rmはexitしないと発動せず、3h毎(trial_timeout=10800s)の再ディスパッチで累積** | **①cae_te_engine.pyの全OpenRadioss起動コマンドをコンテナ内 `timeout -k 30 <sec>` でラップ(自己終了→--rm発動) ②滞留時の手動掃除: `docker ps` → `docker stop <OR系コンテナ>` ③教訓: docker runをsubprocess timeoutで管理する場合は必ずコンテナ内timeoutまたは`docker kill --name`のfinally句を併用 ④**併発問題: クロック597MHz固着はコンテナとは別原因=電源プランprocthrottlemax。`powercfg /setacvalueindex scheme_current sub_processor procthrottlemax 100`(+dc版)+`/setactive scheme_current`で1792MHzに復旧** ⑤修正版はSHA256検証付き分割base64転送でred_lavieへ配布済(2026-07-05 23:30、バックアップ`.bak_t050`)。bd `cttj`** |
| **[T049]** | **2026-07-05** | **fem_impact@thinkpad サイレント即死 — `set -euo pipefail`下の `VTK_N=$(ls ...該当0件... \| wc -l)` でls exit2がpipefail経由で代入文に伝播し、echo到達前に無言でexit 2。stdout/stderr空のため診断不能なまま6/27頃から全practical系デッキが空回り（当初はデッキ未デプロイでtest -f exit1、デプロイ後this bugでexit2）** | **①`\|\| true`を代入内パイプ末尾に追加(k10_tri_track_cae_orchestrator.py) ②`test -f`を明示echo+exit 7化(FEM_IMPACT_INPUT_MISSING) ③QC実測値をdefects_detectedへ抽出しKPI空問題解消 ④意味ゲート自動停止(meaning_gate_max_fail_streak=8)+Telegram通知を全trackへ追加 ⑤爆発デッキRough_Mesh/test.in無効化。教訓: heredoc/set -e配下の`VAR=$(cmd\|cmd)`は必ず失敗時挙動を確認。bd `e3dn`** |
| **[T039]** | **2026-06-25/27** | **PostgreSQL WAL破損 繰り返し再発 — Windows再起動時にDockerのデフォルト stop_grace_period=10秒でSIGKILL → checkpoint書けずWAL破損。6/20(14:22JST)・6/25・6/27(9:01+10:18JST 予期しないシャットダウン×2)の3回発生。Windows Event ID 1074/6008でパターン確認済** | **①docker-compose.yml に `stop_grace_period: 60s` + `-c checkpoint_timeout=1min` 追加(メイン対策) ②backup_infra_daily.ps1の pg_dump出力先を /tmp に変更(データディレクトリ直接書き込み禁止) ③シャットダウンフックスクリプト `scripts/k10_graceful_docker_shutdown.ps1` 作成(要管理者でTask Scheduler登録) ④復旧手順: `pg_resetwal -f` + VACUUM + REINDEX。詳細: T-WAL-001** |
| **tri-thinkpad-fem_impact-917a60f8** | 2026-06-18 | unknown attempt=1 | Run --sync-script before trial; Use test.in_* VTK glob in png shell |
| **tri-thinkpad-fem_impact-ae19be33** | 2026-06-18 | unknown attempt=2 | Run --sync-script before trial; Use test.in_* VTK glob in png shell |
| **tri-thinkpad-fem_impact-e4fa6e39** | 2026-06-18 | unknown attempt=3 | Run --sync-script before trial; Use test.in_* VTK glob in png shell |
| **tri-thinkpad-fem_impact-af65ace5** | 2026-06-18 | unknown attempt=1 | Run --sync-script before trial; Use test.in_* VTK glob in png shell |
| **tri-thinkpad-fem_impact-16846e12** | 2026-06-18 | unknown attempt=2 | Run --sync-script before trial; Use test.in_* VTK glob in png shell |
| **tri-thinkpad-fem_impact-d2f2a4eb** | 2026-06-18 | unknown attempt=3 | Run --sync-script before trial; Use test.in_* VTK glob in png shell |
| **tri-thinkpad-fem_impact-0309eba7** | 2026-07-14 | unknown attempt=1 | Run --sync-script before trial; Use test.in_* VTK glob in png shell |
| **[T038]** | **2026-06-18** | **ThinkPad fem_impact Rough_Mesh tri-track: ①`test.in` Impactは44分でSUCCESS(42 VTK)だが`thinkpad_fem_impact_png.sh`未配置でexit127 ②`auto_revised_mesh.in`は3hタイムアウト(exit124)でjava孤児化・重複実行 ③PNGシェルは`test.in`→PREFIX=`test`で`test.in_*.vtk`を見逃しVTK_MISSING ④Docker vtkがbulk VTKでmunmapクラッシュ(surface+host venvで3 PNG成功) ⑤INC-123: worker `bash -lc`ネストクォートで`test: unbound variable`/exit1→heredoc化で両本番ケースSUCCESS** | **INC-122/123**: watchdog `--sync-script` / PNG `test.in_*`+surface VTK / production_only variants / Impact dispatch heredoc `FEMIMPACT_EOF` / java-only pkill / `thinkpad_fem_impact_autonomous_loop.py` |
| **[T037]** | **2026-06-07** | **リセット後フリート復旧が各PCで何度も失敗: ①INC-120系monitor不具合が全ノードに横展開リスク ②workerがコンソール束縛・ArgumentList誤り ③HPはDefenderが%TEMP%ps1ブロック ④ThinkPadはCRLFでsystemd失敗 ⑤G3はmonitor稼働中にpythonw再spawn失敗 ⑥cmd+プレースホルダURLで404 ⑦ノード毎に手順がバラバラで膨大な手作業** | **INC-121**: `fleet_satellite_setup.ps1`+`satellite_*_daemon.ps1`統一（logon+5分watchdog+pythonw）/ HPは`C:\clawstack_hp`+patrolのみ / ThinkPad CRLF sed / `k10_fleet_satellite_setup_all.ps1 -ProbeOnly` / CAEは**Main LAVIE+Red LAVIE+ThinkPad**のみ（`cae_tri_track_dispatch_policy.md`）/ bd `fleet-post-reset-recovery-inc121` + growth DB `FLEET_OPS` |
| **[T036]** | **2026-06-15** | **Red LAVIE monitor 復旧が何度も失敗: ①K10配信 `monitor_agent.py` SyntaxError（get_cpu_usage try 欠落）②`setup_monitor_node.ps1` が標準ユーザーで `C:\monitor_agent.py` 書込拒否 ③`red_lavie_start_monitor.ps1` が `-AgentPath ...monitor_agent.py` 付き PowerShell 自身を Stop-Process（Saved 直後に無言終了）④ExecutionPolicy で ps1 ブロック ⑤pythonw 起動で SyntaxError 不可視** | **INC-120**: `monitor_agent.py` except+return 修正 / AgentPath 既定を `clawstack_satellite\scripts` / kill フィルタを python(w)+`monitor_agent.py` のみ / Startup VBS 登録 / `:8123` 起動前 `verify_fleet_script_server_gate.ps1`（py_compile 必須）/ SOP: Red LAVIE は必ず `ExecutionPolicy Bypass` + `red_lavie_start_monitor.ps1`。bd `red-lavie-monitor-recovery-inc120` |
| **[T035]** | **2026-06-15** | **④関節分離ゲートのfalse-PASSバグ: 「最接近距離」のみ計測 → 剛体ヒンジで1辺が接触したまま反対辺に開く“見える隙間”を見逃し、太もも装甲の裂け目等をOK判定（2回false-PASS: 腕→腿装甲）** | **`qc_joint_separation.py` を「接触パッチの開き量」方式に書換**: 安静時に接触する子頂点群を記録→可動域スイープでその頂点群の最大離隔を計測（＋安静時の静的隙間チェック）。tol=2.2%×身長。検証: v6を旧ゲート"JOINTS OK"→新ゲートが UpperLeg/膝/肩等の隙間を正しくFAIL。**教訓: 最小値メトリクスは“見える破綻”を保証しない。視覚的欠陥は視覚的指標で測る（T031系統）** |
| **[T034]** | **2026-06-14** | **サテライトPC（LAVIE, Red LAVIE, G3）の24時間稼働率が70%以下に低下（LAVIE: 41.7%, Red LAVIE: 0.8%, G3: 0.0%）。ホスト再起動後のサービス自動起動の不備およびVBS起動スクリプトの構文バグ、Tailscaleの切断が真因。** | **①Red LAVIEのVBS構文バグ（Chr(34)二重括りによるファイル不在エラー）を修正し、スタートアップ登録を再定義。②G3およびLAVIEのスタートアップにDocker compose/n8n自動起動用のタスクスケジューラを恒久化。③Tailscale接続の定期監視スクリプトを有効化。** |
| **[T033]** | **2026-06-14** | **メカ自動リグに「関節分離防止ルール」が存在しない: 腕がT字内転で完全脱離・腿が股で割れる。剛体ボーンペアレント＋pivotがBB比率ハードコード(実関節軸でない)＋LIMIT_ROTATIONのみ→回転で隙間、大回転で脱離** | **設計ルール①〜④をリグビルダーに実装中**: ①pivot=実形状の関節中心(メッシュ算出) ②オーバーラップ・ジョイントコア(ball球/hinge円柱を子ボーンにバインドし隙間を物理的に埋める) ③可動域=無隙間レンジに自動制限 ④分離QCゲート`qc_joint_separation.py`(親子セグメント最小距離の成長を可動域スイープで計測しFAIL判定)。目視は**5フレーム毎×前/横/後**`qc_multiview.py`必須(hero1枚禁止)。bd `Clawdbot_Docker_20260125-exs`/`bd recall mecha-rig-joint-integrity-t033`。T031/T032系統 |
| **[T032]** | **2026-06-14** | **ザク歩行アニメ false-PASS リスク: ①前進を Root pose-bone.location に書き床に沈下（pose-bone はボーン rest ローカル空間／Root は鉛直→ローカルY=世界Z）②股関節が大角スイングで剛体ヒンジ隙間を露出** | **①前進・bobは`armature.location`（世界空間オブジェクト）にキー、pose-boneは回転のみ ②数値ゲート強化(前進>WALK*0.5 + 接地min z>-0.5) ③視覚QA必須(沈下/裂け目確認) ④HIP18°→11°/KNEE35°→22°で剛体隙間縮小。完全除去はリグ側(境界分割/スカート重なり)。T031/T015同系統** |
| **[T031]** | **2026-06-14** | **メカ自動リグ false-PASS: 形状崩壊ザクに "ALL PASS" 判定しTelegram送信** | **3根本原因修正**: ①`remove(armature)`→`parent_clear(KEEP_TRANSFORM)` ②auto-detect直立時rotation上書き禁止 ③`_geometric_quality_gate()`追加(直立比/接地/対称)でvisual QA必須化。T019/T018同系統 |
| **[T030]** | **2026-06-07** | **G3 `monitor_agent` 27.9°C fallback — repo パス不在・8112 旧 agent・LHM :8085 Run 未設定** | **INC-096 拡張** + `fleet_lhm_monitor_agent_runbook.md` + G3 検証 63°C lhm_http + サーマル制御共通化 |
| **[T029]** | **2026-06-07** | **K10 `monitor_agent` が CPU 27.9°C（fallback 誤値）を報告 — LHM Remote Web Server 未起動 + `data.json` パーサが `Type`/文字列 `Value` 非対応** | **INC-096** + `monitor_agent.py` LHM HTTP パーサ修正 + `lhm_ok`/`temp_source` 可視化 + 起動順 SOP（LHM 8085 → monitor_agent 8111）+ `docs/troubleshooting/k10_lhm_monitor_agent_20260607.md` |
| **[T021]** | **2026-06-04** | **各サテライトPC（G3, LAVIE, Dynabook）およびK10の障害が検知されつつ長期間放置 — 監視項目の単純死活（HTTP/ポート）依存、自己修復ループ欠落** | **INC-095** + `update_fleet_operations_status.py`の容量・最終更新トラッキング強化 + `autonomous_coder.py`の`--allow-offline`実装 + タスクスケジューラでのスタートアップ起動登録恒久化 |
| **[T020]** | **2026-06-03** | **OpenRadioss 連続 T&E (`press_blanking`/`press_bending`/`press_blanking_stripper`) が ~1s ERROR TERMINATION — デック構文・中面メッシュ不備** | **INC-094** + pregate (`cae_self_growth_gates.py`) + DBEND形式テンプレ + bd `openradioss-continuous-te-inc094` + starter-only 検証必須 |
| **[T019]** | **2026-06-02** | **LAVIEが`resin_flow`（薄管icoFoam）で24/7 T&Eし2D ParaView \|U\|をTelegram送信 — 射出キャビティ充填・順送金型目標と無関係** | **P025** + `docs/cae_north_star_and_meaning_gate_protocol.md` + Meaning Gate必須 + `resin_fill_cad`/閉キャビティVOF + ParaView2D禁止 + bd/ByteRover定着 |
| [T001] | 2026-04-20 | PDFテキスト抽出時の文字化け | `pdfminer.six` から `PyMuPDF (fitz)` へ切り替え、エンコーディング処理を強化。 |
| [T002] | 2026-04-22 | Blender Headless レンダリング時の GPU エラー | Windows 仮想ディスプレイアダプタを導入し、バックグラウンドでの OpenGL コンテキストを安定化。 |
| [T003] | 2026-04-25 | VoiceVox API のタイムアウト | 生成リクエストをチャンク分割（100文字単位）し、リトライロジックを実装。 |
| [T004] | 2026-04-28 | キャラクターボーンのねじれ (Mesh Skinning) | ウェイトペイントの正規化と、Blender Python API による正規化スクリプトを自動実行。 |
| [T005] | 2026-05-01 | OpenCode GO API の不安定化 | LiteLLM による冗長化（Gemini 2.5 Flash / Claude 3.5 Sonnet）と優先順位制御を導入。 |
| [T006] | 2026-05-03 | スライドレイアウトの崩れ | AI Visual Review Gate を導入。動画合成前に AI がスライドの整合性をチェック。 |
| [T007] | 2026-05-05 | リップシンクのズレ | VoiceVox の `query.json` から正確な音素時間を取得し、Blender の F-Curve に直接流し込む方式へ改善。 |
| [T008] | 2026-05-06 | Excel 報告書 XML 破損 | `RubyXL` の `merged_cells` 配列を書き込み前に一旦クリアし、重複範囲を除去するクリーンアップ処理を実装。 |
| [T009] | 2026-05-07 | T-Pose モデルのテクスチャ剥がれ | Stable Projectorz の PBR ベイク工程に自動 UV リラップを追加。 |
| [T010] | 2026-05-08 | VoiceVoxコンテナのハングアップ | Service Guardian (v1.2) を導入し、L3/L4死活監視と自動再起動を常駐化。 |
| [T011] | 2026-05-08 | QA不合格（Wチェック）の教訓の未利用 | IATF自律学習サイクル (AFL) を実装。不合格理由を教訓として蓄積し、全生成プロンプトへ自動注入。 |
| [T012] | 2026-05-09 | キャラクター透明化・重複・QA形骸化 | 統計的QAを廃止し Kimi K2.6 によるマルチモーダル目視チェックを必須化。Blenderマテリアル不透明固定を強制。 |
| [T013] | 2026-05-10 | Blenderレンダリング全フレーム黒（global_scale二重適用） | `global_scale=0.01` × FBX内蔵スケール0.01 → 0.0001倍（0.2mm）でカメラに映らず全黒。`global_scale=82` に修正。**なぜなぜ**: ①黒→②キャラ不可視→③スケール0.2mm→④FBX出力時に既存0.01スケール埋込済なのに再適用→⑤FBXのUnitScaleFactor未確認で慣例値を使用。**対策**: FBX新規追加時はdiag5スクリプトで`world_height`を必ず測定してからglobal_scaleを決定。 |
| [T014] | 2026-05-10 | 3Dシーンの大道具・小道具・背景がPDF内容と無関係 | **実装完了**。`CLAUSE_SCENE_MAP`（17箇条カテゴリ）＋`derive_scene_context(topic)`＋`setup_environment(scene_ctx)`を`blender_animator.py` V5.0に実装。床・背景壁・看板・小道具（6種）を箇条番号に応じて自動生成。`run_host.py`・`orchestrator.py`にもtopicパラメータを接続済み。**追加バグ(T015候補)**: MixamoモーションFBX（UnitScaleFactor=1.0）を`global_scale=82`でインポートするとarm.scale=82となり、アクションのボーントランスレーションが82×膨張→キャラが800m以上離れてカメラ外に飛ぶ。**暫定対策**: apply_motionを無効化（キャラはTポーズ静止）。正式対策は別タスクでMixamoFBX用global_scaleの再算出が必要。 |
| [T015] | 2026-05-10 | MixamoモーションFBX適用後キャラが画面外に消失（全黒） | **真因**: `pose.bones["mixamorig:Hips"].location[1]` キーフレーム値≈50.17（armatureローカル）。`arm.scale=0.82` → ワールドY=**41.14m**でカメラ外飛散。Blender5.1の`action.fcurves`廃止でF-Curve取得エラーも複合。**最終対策（確認済）**: `rotation_quaternion`/`rotation_euler`/`rotation_axis_angle` F-Curveのみコピー（520本→**208本**）。locationとscaleは全除外。ボーン名はキャラ/MixamoともにmixamoRig:プレフィックス付きで直接互換。ログ確認: `208 bone F-curves (OBJ-level excluded, T015)`。 |
| [T016] | 2026-05-11 | T015修正後にバッチが再起動されず全本が未完成のまま放置 | **真因**: コード修正完了の確認手順・バッチ再起動トリガーが存在しない。T015修正→テスト合格→バッチ再起動の一連フローが定義されていなかった。**副因**: Visual QA `sample_frames_are_nearly_identical` 否決（Tポーズ静止フレーム）がバッチを即停止する設計で復旧手順なし。**対策（本セッション実施）**: ①停止検知→Telegram通知→自動再起動フックをrun_host.pyに追加。②FPS30→12,samples32→12に変更し1本あたり推定時間を17h→2h以内に短縮。③PDF本文キーワード→props動的マッピングを実装。なぜなぜ6段・FMEA・FTA記録済み。 |
| [T018] | 2026-05-31 | 品質ゲート形骸化（方針のみ・FAIL続行・偽合格通知） | `gate_registry.py` fail-closed + PROMISES P024 + `docs/iatf_gate_enforcement_protocol.md` + 監査 `iatf_audit_legacy_outputs.py` |

---

## [T020] OpenRadioss 連続 T&E デック構文不整合 (2026-06-03)

**事象:** K10 連続 T&E ループ (`k10_openradioss_continuous_te_loop.py`) の `press_blanking` / `press_bending` / `press_blanking_stripper` がすべて ~1s で FAILED。Starter/Engine ログ: ERROR 21 (SHELL NEGATIVE/NULL SURFACE), 402 (PART 0), 1051 (BCS), IMPDISP parse error。物理計算 (NORMAL TERMINATION) に一度も到達しなかった。

**North Star 整合 (T019):** 本件は順送金型向け OpenRadioss 曲げ/打ち抜き T&E の **入力品質** 問題。修正後 `inc094e-*` trial で NORMAL TERMINATION を確認 (blanking 17 cycles, bending 230 cycles)。

### 根本原因

1. **板厚の誤配置:** `/PROP/SHELL` の `hm` (hourglass 0-0.05) に 1.2mm を設定、または Y 方向ノードオフセットで厚み表現 → ERROR 21。
2. **PROP 2024 形式非準拠:** `N Istrain Thick ...` の `Istrain` 余分フィールド、`# h` 短縮形式 → 厚み 0 または誤読。
3. **IMPDISP 1行混在:** fct/dir/grnod/Tstart/Tstop 混在 → OpenRadioss 2024 parse fail。
4. **legacy /SHELL, /BCS, engine block in starter** — INC-093 途中修正で段階的に解消。

### 対策 (再発防止)

| 項目 | 内容 |
|---|---|
| テンプレート | 中面 X-Z (y=0); `/PROP` → `Thick` 行; `/IMPDISP` 2行; `/SHELL/pid`; GRNOD>=100 |
| pregate | `precheck_openradioss_case`: engine block, GRNOD clash, thickness-in-geometry |
| 検証手順 | 新 deck は **starter-only** → `.rst` 確認 → engine → NORMAL TERMINATION |
| 記録 | INC-094, bd `openradioss-continuous-te-inc094`, ByteRover |

### FMEA / FTA / 5Why / Logic Tree

詳細は `docs/INCIDENT_LOG.md` **INC-094** を参照（FMEA RPN表、FTA 木、6段なぜなぜ、ロジックツリー完備）。

---

## [T019] 北極星喪失・無意味CAEループ（resin_flow / 2D |U|）(2026-06-02) — 全活動最優先

**事象:** ユーザーはキャビティへの樹脂充填・成形条件調整・3D可視化を求めていたが、LAVIE連続T&Eは `lavie_te_allocation_overrides.json` により **`resin_flow`（矩形ダクト・icoFoam層流）** のみを実行。SUCCESS時に **ParaView 2D |U|** をTelegramへ送り、「忙しく見えるが順送金型・射出成形に無関係」な繰り返しが続いた。エージェントは「動画を送る」要求に引っ張られ、**物理目標とカテゴリ/ソルバの整合**を先に検証しなかった。

### 北極星（最終目標 — 見失ってはならない）

ユーザー提供の **プレス部品3Dモデル** から:

1. **Moldflow級** — 閉キャビティ樹脂充填（VOF・ゲート・パック）の正しいT&E  
2. **Cetol 6 Sigma級** — 公差・スタックアップの正しい解析  
3. **OpenRadioss** — **曲げ**・**打ち抜き**の正しい解析  

→ これらを統合して **順送金型（プログレッシブダイ）開発** を完遂できること。

### なぜなぜ（要約）

| Why | 観察事実 |
| --- | --- |
| ①なぜ無意味？ | 充填ではなくダクト内速度場を見ていた |
| ②なぜダクト？ | カテゴリが `resin_flow` / `resin_flow_v001` 固定 |
| ③なぜ気づかない？ | ループ稼働＝進捗と誤認；Telegram出力＝価値と短絡 |
| ④なぜ検証なし？ | Meaning Gate（物理⇔カテゴリ）がコード・ルール化されていなかった |
| ⑤なぜ繰り返す？ | 失敗してもカテゴリを変えず nu/U だけスイープ |

### FMEA（抜粋）

| 工程 | 故障モード | 影響 | 対策 |
| --- | --- | --- | --- |
| 要件解釈 | 可視化形式だけ実装 | 目的逸脱 | Meaning Gate 5問必須 |
| 割当 | resin_flow 固定 | 充填未達 | overrides → resin_fill_cad + closed_pack |
| 通知 | 2D \|U\| 送信 | 誤判断・ノイズ | `_openfoam_skip_paraview` + VOF MP4のみ |
| 充填動画 | LAVIEでffmpeg無し・notifyだけ成功扱い | SUCCESSなのに動画無し | INC-089: K10 pull (`lavie_cae_video_support`); host=lavieはengine送信禁止 |
| 記憶 | 教訓未定着 | 再発 | P025 + T019 + bd + ByteRover + Cursor rule |

### 意味ゲート（毎セッション・毎タスク前）

1. 何の物理現象か？  
2. category / solver / physics_category は一致しているか？  
3. どのKPIが北極星に1mmでも近づくか？  
4. 無意味な繰り返しではないか？  
5. 今回の学びを bd / ByteRover / 本節に残すか？  

**1つでもNOなら実行停止・修正してから再開。**

### 恒久対策（忘禁）

1. **PROMISES P025**（本ファイル最上部）  
2. **`docs/cae_north_star_and_meaning_gate_protocol.md`**（単一真実）  
3. **`.cursor/rules/cae_north_star_meaning_gate.mdc`**（alwaysApply）  
4. **`bd remember --key cae-north-star-t019`** / Beads `Clawdbot_Docker_20260125-3z1`  
5. **ByteRover** `brv curate` で全セッション前 query 推奨  

**参照:** `lavie_te_allocation_overrides.json`, `scripts/cae_te_engine.py` `_openfoam_skip_paraview`, `scripts/k10_lavie_continuous_te_loop.py`

---

## [T018] IATF動画：ユーザー要求の品質ゲートが守られなかった (2026-05-31) — 詳細分析

**事象:** ユーザーは繰り返し「QC工程表・FMEA・FTA・なぜなぜ・Fishbone・出演者/背景/照明/カメラ配置・画像/動画崩壊チェック・Script QA」を**生成開始前に必須**と指示していたが、実際には (1) LLM事前分析がサイレントスキップ (2) Script QA FAIL のまま TTS/レンダ継続 (3) Telegram が不合格でも「合格」表示 (4) 38/40 フォルダに `quality_preflight.json` 無し (5) 27 本以上が FAIL/ERROR 台本のまま MP4 化、が発生した。

### なぜ守られなかったか（根本原因）

| Why | 観察事実 |
| --- | --- |
| ①なぜ要求が効かない？ | エージェント/バッチがゲートを通らずに生成した |
| ②なぜ通らない？ | ルールが `CLAUDE.md` 等の**文書のみ**で、Python が FAIL 時に `raise` していなかった |
| ③なぜ raise しない？ | `quality_preflight.py` が「LLM失敗時はサイレントスキップ」と明記され `{}` で続行していた |
| ④なぜ FAIL でも続行？ | `run_host.py` が Script QA の `overall==FAIL` 後も TTS へ進み、Telegram で常に合格メッセージを送っていた |
| ⑤なぜ再開で抜ける？ | resume 時に `script.json` があると工程 1.5〜2.5 をスキップする設計だった |
| ⑥なぜエージェントが省略？ | `.cursor/rules` に IATF 専用ルールがなく、セッションごとに `CLAUDE.md` を読まない |

### 各工程で実際に起きた問題と、効いた対策

| 工程 | 実際の問題 | 効いた対策 |
| --- | --- | --- |
| 品質事前分析 | 未実行 or 空 JSON；FMEA が台本に未反映 | `quality_preflight.json` 必須 + `QualityPreflightError` |
| 台本 QA | 6/7 FAIL で TTS 開始；API 浪費 | `script_qa_gate.py`：PASS のみ続行 |
| 通知 | FAIL なのに「台本Wチェック合格」 | PASS 時のみ Telegram `[PASS]` |
| 制作レイアウト | 未知キャラ・背景無関係・全黒・静止画 PASS | `production_design.json` + Visual QA checklist |
| Visual QA | 401 で自動合格；統計のみでシルエット PASS | 401 バイパス削除；R08-R13 + V01-V06 |
| 再開 | 古い NG 台本のままレンダ | resume でも `_ensure_*` + `gate_registry` |
| 監査 | 過去 MP4 が合格か不明 | `scripts/iatf_audit_legacy_outputs.py` |

### FMEA（抜粋）

| 工程 | 故障モード | 影響 | S | O | D | 対策 |
| --- | --- | --- | --- | --- | --- | --- |
| 要件定義 | 方針のみでコード未接続 | 再発 | 9 | 8 | 3 | `gate_registry.py` 単一真実 |
| 事前分析 | LLM 失敗スキップ | 無分析生成 | 8 | 7 | 2 | fail-closed |
| Script QA | FAIL 続行 | API・時間浪費 | 9 | 9 | 2 | `ScriptQAError` |
| 通知 | 偽合格 | 誤判断 | 7 | 6 | 2 | PASS 時のみ通知 |
| 監査 | 過去品不明 | 誤配布 | 8 | 9 | 4 | 監査スクリプト |

### FTA（頂上事象：ユーザー要求が守られない）

```text
要求不履行 (TOP)
├─ [OR] コードが止めない
│   ├─ サイレントスキップ (quality_preflight)
│   ├─ FAIL でも TTS (run_host 旧版)
│   └─ resume バイパス
└─ [OR] 人間/エージェントが省略
    ├─ CLAUDE.md のみ（実行不可）
    └─ Cursor rule なし
```

### 恒久対策（必須・忘禁）

1. **単一真実:** `pipeline/gate_registry.py` + `docs/iatf_gate_enforcement_protocol.md`
2. **PROMISES P024:** IATF 動画はゲート artifact なしで TTS/レンダ禁止
3. **Cursor:** `.cursor/rules/iatf_gate_enforcement.mdc`（alwaysApply）
4. **作業前:** `trouble_history.md` T018 と `bd remember --key iatf-gate-t018`
5. **過去品:** `python scripts/iatf_audit_legacy_outputs.py` で再監査

**参照:** INC-101, `docs/iatf_gate_enforcement_protocol.md`

---

## [T015] Mixamoモーション適用後キャラが画面外消失 (2026-05-10) — 詳細分析

### 最終確定した真因と対策

- **真因**: `pose.bones["mixamorig:Hips"].location[1]` ≈ 50.17（アーマチュアローカル空間絶対位置）。`arm.scale=0.82` → ワールドY=41.14m → カメラ（Y≈4m）から37m外。
- **複合要因**: Blender 5.1で`action.fcurves`属性が廃止→AttributeError → `action.layers[].strips[].channelbags[].fcurves`が正しいAPI。`ActionSlots.new()`の引数も変更（`id_type`+`name`両方必須）。
- **最終対策**: `rotation_quaternion`/`rotation_euler`/`rotation_axis_angle` のF-Curveのみコピー（520本→208本）。`location`と`scale`は全除外。
- **確認ログ**: `[BLENDER] Motion applied: 208 bone F-curves (OBJ-level excluded, T015)`
- **ボーン名**: キャラ/MixamoともにBlenderインポート後は`mixamorig:`プレフィックス付き → プレフィックス除去不要、直接互換。

### なぜなぜ分析（最終版）

| Why | 観察事実 |
| --- | --- |
| ①なぜ全黒？ | キャラクターがカメラに映っていない |
| ②なぜ映らない？ | キャラクターがワールドY≈41mに飛散 |
| ③なぜ41m？ | `Hips.location[1]`キーフレーム値≈50.17（armatureローカル）× arm.scale=0.82 |
| ④なぜ50.17？ | Mixamo FBXはHipsボーンのワールド位置をlocationキーフレームに絶対値で記録する仕様 |
| ⑤なぜlocationを使った？ | rotation F-Curveだけでなくlocation F-Curveも無差別にコピーしていた |
| ⑥なぜ無差別？ | apply_motion()実装時にF-Curveのdata_pathを確認せず全転用した |

**再発防止**: 新規モーションFBX適用前に`blender_kf_values.py`でHips.location値を確認し、50以上ならlocation除外モードを使用する。

### FMEA (Failure Mode and Effects Analysis)

| 工程 | 故障モード | 影響 | 深刻度(S) | 発生確率(O) | 検出容易性(D) | RPN | 対策（実施済） |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FBXインポート | OBJECTレベルlocation keyframe持込 | キャラ画面外飛散 | 10 | 7 | 2 | 140 | **✅** rotation系のみコピー（520→208本）、location/scale全除外 |
| スケール設定 | global_scale不整合 | world_height×82膨張 | 8 | 5 | 3 | 120 | **✅** 新規FBX追加時にblender_kf_values.pyでworld_height実測 |
| アクション転用 | 転用先と転用元のarm.scale不一致 | ボーンアニメ破綻 | 7 | 4 | 4 | 112 | **✅** インポート後arm.scaleをログ出力して比較 |
| レンダリングゲート | 全黒フレームを合格と誤判定 | 不良品流出 | 9 | 6 | 2 | 108 | **✅** visual_qa.py: dark_ratio_median>0.90で`all_black_frames`失敗を追加 |

### FTA (Fault Tree Analysis)

```text
全黒レンダ（TOP事象）
├─ [OR] カメラ外にキャラ消失
│   ├─ [AND] アーマチュアがz>10m
│   │   ├─ OBJECTレベルlocation keyframeあり（Mixamoの仕様）
│   │   └─ global_scale=82で倍率増幅（開発者の設定ミス）
│   └─ 子オブジェクト位置二重オフセット（T015修正済）
└─ [OR] マテリアル発光なし
    ├─ Emission未接続（→T013/T014で修正済）
    └─ use_nodes=True設定漏れ（Deprecation対応未完）
```

**重要な教訓**: FBX由来のアクションを別アーマチュアに転用する際は、必ずF-Curveのdata_pathを全数確認し、`pose.bones`プレフィックス以外のF-Curveが含まれていないかチェックすること。

---

## [T016] バッチ修正後の再起動漏れ・全本未完成放置 (2026-05-11) — 詳細分析

### なぜなぜ分析

| Why | 観察事実 |
| --- | --- |
| ①なぜ全41本が未完成？ | バッチが停止したまま再起動されなかった |
| ②なぜ再起動しなかった？ | T015修正完了後のバッチ再起動手順が存在しなかった |
| ③なぜ手順がない？ | バグ修正→テスト合格→バッチ再起動を一連のフローとして定義していなかった |
| ④なぜフローがない？ | CI/CD（コード修正→本番反映）の概念をバッチ処理に適用していなかった |
| ⑤なぜ適用しなかった？ | バッチは「手動起動するもの」という前提があり、自動継続の設計がなかった |
| ⑥なぜその前提？ | パイプライン初期設計時に長時間バッチの運用フローを定義しなかった |

**再発防止**: コード修正完了時に `run_host.py --restart-failed` を必ず実行するルールを確立。

### FMEA

| 工程 | 故障モード | 影響 | S | O | D | RPN | 対策（実施済） |
| --- | --- | --- | --- | --- | --- | --- | --- |
| バグ修正後 | バッチ再起動漏れ | 全本未完成 | 9 | 8 | 1 | 72 | **✅** 修正完了時に再起動フックを追加 |
| Visual QA否決 | バッチ即停止・無復旧 | 全本停止 | 8 | 7 | 2 | 112 | **✅** QA否決時に自動スキップ+Telegram通知へ変更 |
| レンダリング速度 | 1本17h×41本=29日 | 現実的でない納期 | 7 | 10 | 1 | 70 | **✅** fps30→12, samples32→12で推定2h/本に短縮 |
| PDF内容非適合 | 汎用小道具のみ | 教育効果が低い | 6 | 9 | 3 | 162 | **✅** PDF本文キーワード→props動的マッピング実装 |

### FTA

```text
全本未完成（TOP事象）
├─ [AND] バグ修正完了
│   └─ バッチ再起動なし
│       ├─ 再起動手順が未定義（設計漏れ）
│       └─ 停止通知が届かない（Telegram未設定）
└─ [OR] Visual QA否決でバッチ停止
    ├─ sample_frames_are_nearly_identical（T015未修正時）
    └─ 停止後の自動復旧ロジックなし
```

---

## [T010] IATF動画生成：VoiceVoxコンテナフリーズによるバッチ停止 (2026-05-09)

**症状**: IATF動画生成バッチが「箇条8.6.3 外観検査項目の管理」のTTS（音声合成）フェーズで完全に停止。`generation.log` にエラーは記録されず、17:09 以降更新が止まっていた。

**根本原因**:

- **コンテナの状態**: `clawstack-unified-voicevox-1` コンテナは「Up」状態であったが、内部プロセスがハングし、外部からの HTTP リクエストに応答しない状態になっていた。
- **監視の不備**: 既存の監視スクリプトは API の生存確認のみを行っており、TTS エンジンのハングを検知できていなかった。

**対策**:

1. **コンテナ再起動**: `docker restart clawstack-unified-voicevox-1` を実行し、正常レスポンスを確認。
2. **統合監視の導入**: `service_guardian.py` を新規作成。VoiceVox, Postgres, LiteLLM の L3/L4 ヘルスチェックを行い、異常時に自動再起動する機能を実装。

## [T011] IATF動画生成：QA不合格（Wチェック）の教訓の再利用ルール (2026-05-09)

**事象**: Wチェック（Gemini等）で指摘された不合格理由が、その動画の再生成には活かされるが、将来の別の動画生成には引き継がれず、同じミスを繰り返すリスクがあった。

**対策**:

1. **ナレッジ蓄積**: 不合格理由を `iatf_generation_lessons.json` に教訓として自動保存。
2. **ナレッジ注入**: 次回の動画生成時に、過去の全教訓をプロンプトへ自動的に「注意事項」として追加する仕組みを実装。
3. **DB記録**: Postgres DB に `qa_score` と `qa_feedback` を保存し、品質の経時変化を追跡可能にした。

---

## [T012] IATF動画生成：3Dキャラ透明化・重複・QAゲート形骸化 (2026-05-09)

**事象**: 生成された3D動画において、キャラクターが半透明になる、あるいは同じ場所に複数人が重複して出現する不備が発生。既存の Visual QA（統計的数値チェック）がこれを「合格」と判定し、不適合品が流出した。

**根本原因**:

- **QAの形骸化**: 従来の Visual QA は Pillow によるエッジ量・コントラスト計算のみを行っており、「画像に何が映っているか（意味的整合性）」を判断できていなかった。
- **偽のAIレビュー**: 以前のシステムは画像認識機能を持たないテキストAI（DeepSeek-V3等）に画像URLを渡しており、実質的な視覚チェックが行われていなかった。
- **Blender設定不足**: モデルのマテリアル blend_method が不透明（OPAQUE）に強制されておらず、透過設定が意図せず有効になっていた。
- **インスタンス管理不全**: ショット切り替え時に古いキャラクターオブジェクトの削除が不完全で、重複が発生していた。

**対策（新ルール）**:

1. **マルチモーダルAI (Kimi K2.6) の導入**: `ai_visual_reviewer.py` を新規作成。画像の内容（透明度、重複、Tポーズ）を「目視」で判定し、NG時はプロセスを物理的にロックするゲートを構築。
2. **Blenderマテリアル強制固定**: 全モデルの全マテリアルに対し、スクリプトで `blend_method = 'OPAQUE'` を強制適用。
3. **クリーンアップの標準化**: 各ショットの生成開始時に、Mesh, Armature, Collection を全削除するルーチンを `blender_animator.py` に組み込み。
4. **環境変数の固定**: `IATF_VIDEO_SLIDE_REVIEW_MODE=ai_required` を `.env` に固定。

---

## [T017] 自動学習ダッシュボードの表示遅延およびキャッシュ固着不具合 (2026-05-26)

**事象**: `http://localhost:8088/apps/growth_dashboard/index.html` にて、2026-05-24 の新規学習実績が「0件」と表示されていた。実際には裏側で 94 件の新規学習に成功していたが、ダッシュボード画面に反映されていなかった。また、手動でファイルを更新してもブラウザキャッシュの固着によって23日時点の古い表示が維持され続けた。

**根本原因**:

- **同期処理の設計漏れ**: 自動学習プログラム `universal_growth_daemon.py` 内で、画面用統計JSONファイル (`growth_stats.json`) の出力関数 `export_stats_json()` が起動時に一度だけしか実行されておらず、周期的な自動学習ループ (`while True`) 内から完全に漏れていた。
- **プロセスの不意の停止**: 5月25日 09:58頃にOS一時エラー (`[Errno 22] Invalid argument`) が発生した際、例外はキャッチされてログ出力されたものの、コンソールセッションの終了に伴いプロセス自体がサイレントに終了（ハングアウト）してしまっていた。
- **クライアント側キャッシュの固着**: `index.html` 内の `fetch('growth_stats.json')` 処理にキャッシュバスター（クエリパラメータ）が設定されていなかったため、Webブラウザが静的ファイルをキャッシュし続け、データの更新を検知できなかった。

**対策**:

1. **デーモンコードの修正**:
   `universal_growth_daemon.py` の `while True` 内に `export_stats_json()` を追加。15分おきの学習サイクルごとに統計JSONが自動再ビルドされるように修正した。
2. **キャッシュバスターの実装**:
   `index.html` の `fetch` リクエストにタイムスタンプを付与し、強制的に常に最新ファイルを取得するよう改善した：
   `const res = await fetch('growth_stats.json?t=' + new Date().getTime());`
3. **プロセス再起動と手動同期**:
   手動で集計JSONを強制再ビルドし、デーモンをバックグラウンドプロセスとして再起動（復旧完了）。

**なぜなぜ分析**:

| Why | 観察事実 |
| --- | --- |
| ①なぜ24日の学習履歴が0件？ | 集計ファイル `growth_stats.json` が24日 09:00以降更新されていなかった |
| ②なぜ更新されない？ | `universal_growth_daemon.py` が25日 09:58以降停止しており、起動時しかJSONを更新しない設計だった |
| ③なぜ起動時のみ？ | ループ処理内で `export_stats_json()` を呼び出しておらず、設計時に起動時のみの処理と誤認した |
| ④なぜ手動で更新しても変わらない？ | ブラウザが古いJSONファイルをローカルキャッシュから読み込み続けた |
| ⑤なぜキャッシュを読み込む？ | 静的URLにクエリパラメータ等のキャッシュ破棄用コードが組み込まれていなかった |

**再発防止**:
- 集計デーモン開発時は、データの書き出し・同期処理を必ずループの最深部に埋め込み、定期実行を担保すること。
- SPAやAJAX/fetchで静的データ（JSON等）をロードする際は、必ず `?t=timestamp` 形式のキャッシュ無効化設計を標準採用すること。

---

## [T021] 各PCノード障害の長期間放置問題 (2026-06-04)

**事象:** 各パソコン（K10, G3, LAVIE, Dynabook）の問題（Gmail sync一時フォルダによるディスク枯渇、Ollama負荷によるDynabook熱暴走、Docker/WSL2フリーズに伴うLAVIE通信途絶、QA否決によるバッチジョブのハング）が、ダッシュボードやプロセス上で認識可能であったにもかかわらず、自律的に修復されず長期間放置されていた。

### 根本原因
1. **死活監視への過度な依存:** `monitor_agent`およびダッシュボードが「ポートが開いているか（Liveness: HTTP 200）」のみを確認しており、処理のハングアップやディスクフル、論理エラーを検知・自動修復（Watchdog）する設計になっていなかった。
2. **ハッピーパス指向の開発設計:** 不安定な一般PC（通信切断、スリープ、突然の再起動）をノードとする現実に対して、障害発生時にロールバックして即時停止するような脆弱なクローズドループになっていた。

### 対策 (再発防止)
| 項目 | 内容 |
|---|---|
| 監視の強化 | ディスク容量、バッチの最終ジョブ実行からの経過時間等のパラメーターを監視項目へ追加 |
| 自動復旧の常駐化 | 各PCのタスクスケジューラにスタートアップ自動起動バッチを登録・常駐化し、スリープを無効化 |
| 例外許容デプロイ | `autonomous_coder.py` に `--allow-offline` モードを導入し、サテライトがオフライン時もローカル改善とGitバックアップを継続、復帰時に非同期デプロイ |
| 意味ゲート | 毎回の実行前に「意味ゲート (Meaning Gate)」で北極星目標との整合性を自動監査する |
| 記録 | INC-095, `universal_growth.db` (Record ID: 3054) |

---

## [T022] 2026-06-05 AIエージェントによるシステムの重複構築リスク（車輪の再発明）

**事象:** トラブル分析結果を記録するよう指示されたAIエージェントが、既存の正式な記録システム（`memory/trouble_history.md` や `incident_extract_for_fmea.json`）が既に存在しているにも関わらず、ワークスペース全体を十分に調査・検索せず、新規に `Failure_Analysis_20260605.md` という重複ファイルを作成する提案（実装計画）を行った。

**根本原因:**
* エージェントが新規タスクを受けた際、「類似の既存システムがないか」を網羅的に検索（ファイル一覧や内容の慎重な吟味）するステップをスキップし、即座に新規構築に走ったため。

**対策:**
* 自動処理エージェントやAIアシスタントは、新たなデータベースや管理用ファイルを作成する前に、必ず既存システム（過去トラや運用ルールなど）を検索し、重複を避けるルールを関連MDファイルに明記した。

---

## [T023] 2026-06-05 YouTube解析ダッシュボードの表示同期不備 (JSON vs DB)

**事象:** `iatf_youtube_monitor.py` が動画解析に成功し SQLite (`universal_growth.db`) へデータを保存していたが、ダッシュボード画面では表示が増えなかった。
**根本原因:** ダッシュボードがDBではなく静的なダミーデータを含む `iatf_youtube_summary.json` を直接読み込む設計になっており、DBからJSONへのエクスポート処理が漏れていた。
**対策:** `export_knowledge_history.py` 内に、DBから最新のYouTubeレコードを抽出し `iatf_youtube_summary.json` へ書き出すエクスポートロジックを追加し、定期同期ループに組み込んだ。

---

## [T024] 2026-06-05 K10 リソース過負荷による Ollama タイムアウト

**事象:** K10上でYouTube動画の文字起こしとOllama（Qwen3:8b）によるAI要約を並行実行した際、K10のCPU使用率が100%に張り付き、Ollamaの推論APIがタイムアウトエラーを起こした。
**根本原因:** K10はシステム全体を統括する「頭脳ノード」であり、重い推論処理を無制限に走らせると他のオーケストレーション機能に影響が出る。
**対策:** ノード負荷監視を強化し、K10でのLLM推論時はAPIのスロットリング・タイムアウト上限を設ける。重い計算処理は「筋肉ノード」であるLavie等へオフロードする設計（`cae_workload_router.yaml`）を厳守する。

---

## [T025] 2026-06-05 Paperless-ngx 連携パスの相違（Consumeフォルダ不一致）

**事象:** Scribdから自動ダウンロードしたPDF資料が、Paperlessのダッシュボードに反映されなかった。
**根本原因:** `scribd_ingestion.py` がファイルを独自の `data/scribd_downloads` に保存しただけで処理を終了していた。Paperless-ngxが自動取り込みを行う `paperless/consume` フォルダへの移動処理が欠落していた。
**対策:** ダウンロード完了後、ファイルを速やかに `paperless/consume` フォルダへコピーする連携フローをスクリプトに実装。

---

## [T026] 2026-06-05 GitHub巨大ZIP解凍時の Windows MAX_PATH エラー

**事象:** Github HarvesterがJavaベースの `industry4.0-mes_master.zip` をダウンロード後、解凍処理においてエラーが発生しクラッシュした。
**根本原因:** Javaアプリはフォルダ階層が深く、デフォルトの深いパス内で解凍しようとしたため、Windowsの最大パス長制限（260文字: MAX_PATH）を超過した。
**対策:** ZIP解凍などの外部ファイル処理は、浅いテンポラリフォルダ内で実行し、必要なファイルだけを移動する仕様に変更。

---

## [T027] 2026-06-05 Python SQLite `conn.close()` 順序ミスによるクラッシュ

**事象:** `export_knowledge_history.py` への追記実装中、`sqlite3.ProgrammingError: Cannot operate on a closed database.` エラーが発生した。
**根本原因:** 既存の `conn.close()` の後に、新規のデータ抽出用クエリを挿入してしまったため。
**対策:** データベースコネクションのクローズは、全抽出処理が完了しJSON書き出しを行う直前まで引き下げるようロジックを修正。

---

## [T028] 2026-06-05 ダッシュボードのK10 CPU使用率が常に0%になる不具合

**事象:** ダッシュボード上でK10のCPU使用率が常に0%と表示されていた。
**根本原因:** CPU使用率を取得する `monitor_agent.py` 内で、古い `wmic` コマンドが使用されていた。最新のWindows 11では `wmic` が廃止・削除されているため、裏側でコマンドエラーが発生し、例外処理によって常に `0.0` が返却されていた。
**対策:** CPU取得ロジックを最新のPowerShellコマンド（`Get-CimInstance Win32_Processor`）に書き換え、エージェントを再起動して復旧した。

---

## [T029] 2026-06-07 K10 monitor_agent CPU温度誤報告（LHM連携失敗）

**対象:** K10 NUCBOX_K10 / i9-13900HK / `scripts/monitor_agent.py` / LibreHardwareMonitor `:8085`

### 失敗の経緯（3段階）

| 段階 | 症状 | ユーザー確認値 |
|------|------|----------------|
| **F1** | `monitor_agent` 再起動直後 | `cpu_temp_celsius: 27.9`, `temp_source: fallback`, LHM 項目すべて空 |
| **F2** | LHM 起動後も `:8085` 未応答 | `Invoke-WebRequest http://127.0.0.1:8085/data.json` -> **接続できません** |
| **F3** | LHM HTTP 200 後もパース失敗 | `lhm_ok: False`, `lhm_error: no_cpu_temperatures_in_json`, 依然 fallback 27.9°C |
| **成功** | パーサ修正 + LHM Run 後 | `8085` 200 / 76376 bytes, `lhm_http`, CPU Package **84°C**, Core Max **85°C**, KIOXIA **99.2%** disk warning |

### 根本原因

1. **起動順序:** `monitor_agent` は LHM Remote Web Server より先に起動可能。8085 が死んでいる間は WMI/ACPI fallback のみ。
2. **fallback 誤値:** Windows ACPI サーマルゾーンは **27.9°C 等の非物理値**を返す。i9 実測 84–86°C と乖離。**fallback を CPU 温度として表示してはならない**（K10）。
3. **JSON スキーマ不一致:** LHM `data.json` は `SensorType` ではなく **`Type: "Temperature"`**。`Value` は **`"86.0 °C"` 文字列**（数値 float ではない）。旧パーサは `isinstance(val, float)` のみ -> 温度 0 件 -> `no_cpu_temperatures_in_json`。

### 対策（実装済み）

| # | 対策 | 場所 |
|---|------|------|
| 1 | LHM HTTP 読取 (`get_lhm_metrics`) を最優先 | `scripts/monitor_agent.py` |
| 2 | `Type` / `SensorId` / 文字列 `Value`・`RawValue` パース | 同上 `_lhm_parse_number`, `_lhm_walk_sensors` |
| 3 | `/metrics` に `lhm_ok`, `lhm_error`, `temp_source`, `cpu_package_c`, `core_max_c`, `disk_warnings` | 同上 |
| 4 | 運用 SOP: **LHM Run (8085) -> 8085 確認 -> monitor_agent 再起動** | `docs/troubleshooting/k10_lhm_monitor_agent_20260607.md` |

### 再発防止ルール

- K10 で `temp_source != lhm_http` のとき **CPU 温度をダッシュボード/サーマル制御の根拠に使わない**。
- CAE 重負荷前に `disk_warnings`（E: 99% 等）を確認。
- LHM はログオン時自動起動 + Remote Web Server Run をタスクスケジューラ化（未実装 -> follow-up）。

**記録:** INC-096, ByteRover `bd remember --key k10-lhm-monitor-inc096`, `docs/troubleshooting/fleet_lhm_monitor_agent_runbook.md`

---

## [T030] 2026-06-07 G3 monitor_agent 27.9°C fallback（LAVIE 再接続時と同型）

**対象:** G3 NucBoxG3_Plus / ユーザー `yns` / リポジトリなし

**症状:** Dashboard 27.9°C, `temp_source` 空, `lhm_ok` 空 → 8123 版導入後 `lhm_error: WinError 10061` → LHM GUI Run 後 **63°C lhm_http**

**G3 固有失敗:**

| # | 失敗 | 対策 |
|---|------|------|
| 1 | `D:\Clawdbot_Docker_20260125\scripts\*.ps1` 不存在 | K10 `:8123` から `lhm_setup.ps1` / `monitor_agent.py` を取得 |
| 2 | `:8112/monitor_agent.py` 旧版 | **`:8123` のみ使用** |
| 3 | LHM プロセス稼働中も 8085 拒否 | Options -> Remote Web Server -> **Run**（自動化不可） |

**成功:** `lhm_ok: True`, CPU Package 63°C, サーマル制御フィールドあり（80°C 以上で powercfg 制限）

**LAVIE/red_lavie  tonight:** 同一手順 — `docs/troubleshooting/fleet_lhm_monitor_agent_runbook.md`

---

## [T036] 2026-06-15 Red LAVIE monitor 復旧多段失敗（INC-120）

**対象:** Red LAVIE `DESKTOP-DERCN1N` / `100.99.145.3` / monitor `:8111` / worker `:5682` / ユーザー `yns-lavie`（非管理者）

### 症状（ユーザー体験）

1. `setup_monitor_node.ps1` → WebClient DownloadFile 失敗（実際は `C:\` 書込拒否）
2. `monitor_agent.py` 手動起動 → `SyntaxError: expected 'except' or 'finally' block` line 155
3. `red_lavie_start_monitor.ps1` → `Saved: ...90693 bytes` の直後に無言終了、`8111` 不通
4. worker `:5682` のみ OK、monitor だけ落ちる（手動 python.exe ウィンドウを閉じた場合も同様）

### 根本原因（5 Why × 5 件）

| # | 故障 | Why5 |
|---|------|------|
| A | K10 配信 agent が SyntaxError | `get_cpu_usage()` 第3 try に except 未実装のまま `:8123` 配信 |
| B | setup ダウンロード失敗 | 既定 `-AgentPath C:\monitor_agent.py` → 標準ユーザー Access Denied |
| C | start_monitor 無言終了 | `CommandLine -match 'monitor_agent'` が `-AgentPath ...monitor_agent.py` 付き **実行中 PowerShell 自身** にマッチ → Stop-Process 自爆 |
| D | ps1 実行不可 | Red LAVIE 既定 ExecutionPolicy が Restricted、`& script.ps1` 不可 |
| E | 原因が見えない | `pythonw.exe` バックグラウンド起動で SyntaxError がコンソールに出ない |

### 恒久対策

| 対策 | ファイル |
|------|----------|
| SyntaxError 修正 + py_compile ゲート | `scripts/monitor_agent.py`, `scripts/verify_fleet_script_server_gate.ps1`, `scripts/start_k10_fleet_script_server.ps1` |
| kill フィルタ厳密化（python(w) + monitor_agent.py のみ） | `scripts/red_lavie_start_monitor.ps1`, `scripts/setup_monitor_node.ps1`, `scripts/k10_red_lavie_auto_recovery.py` |
| Startup VBS 登録 | `scripts/red_lavie_start_monitor.ps1` |
| Red LAVIE SOP 追記 | `docs/troubleshooting/red_lavie_stability_why_offline.md` |

### Red LAVIE 正しい復旧手順（1 行セット）

```powershell
$K10 = "http://100.119.18.40:8123"
Invoke-WebRequest "$K10/red_lavie_start_monitor.ps1" -OutFile "$env:TEMP\mon.ps1" -UseBasicParsing
powershell -ExecutionPolicy Bypass -File "$env:TEMP\mon.ps1" -AgentPath "C:\clawstack_satellite\scripts\monitor_agent.py"
```

成功マーカー: `RED_LAVIE_MONITOR_OK` + `Startup VBS:`

### 禁止パターン

- `C:\monitor_agent.py` への書込（非管理者 Red LAVIE）
- `CommandLine -match 'monitor_agent'` 単独（PowerShell 自爆）
- `:8123` 配信前に `py_compile` 未実行
- Red LAVIE で `& script.ps1` のみ（Bypass なし）

**記録:** INC-120, bd `red-lavie-monitor-recovery-inc120`, ByteRover curate

---

## [T037] 2026-06-07 リセット後フリート復旧の多段失敗（INC-121）

**事象:** Windows Update 再起動後、Red LAVIE / Main LAVIE / G3 / Dynabook / HP / ThinkPad それぞれでセットアップが何度も失敗。ユーザーがノード毎に手順を再発見し、膨大な手作業になった。

### 根本原因（7系統）

1. **配信品質:** K10 `:8123` が SyntaxError 入り `monitor_agent.py` を配信（INC-120 系）
2. **プロセス起動:** `Start-Process -ArgumentList` 単一文字列、コンソール束縛 python
3. **セキュリティ:** HP で Defender が `%TEMP%\*.ps1` と子 PowerShell をブロック
4. **デプロイ:** ThinkPad へ CRLF 付き `.sh` を SCP → `set -o pipefail` 失敗
5. **ロジック:** G3 monitor 稼働中に不要な `pythonw` 再 spawn
6. **運用:** cmd.exe やプレースホルダ URL で 404
7. **設計:** ノード別バラバラ手順、watchdog 未統一、K10 プローブ未実施

### 対策

| 項目 | 内容 |
|------|------|
| 統一デーモン | `fleet_satellite_setup.ps1` + `satellite_*_daemon.ps1`（logon + 5分 watchdog + pythonw） |
| HP | `C:\clawstack_hp` 恒久ディレクトリ、`hp_watchdog.py` パトロールのみ（CAE なし） |
| ThinkPad | `thinkpad_ssh_common.py` で CRLF 除去、systemd `Restart=always` |
| ゲート | `verify_fleet_script_server_gate.ps1`、`-ProbeOnly` |
| CAE 振分 | Main LAVIE=OpenFOAM、Red LAVIE=OpenRadioss、ThinkPad=fem_impact/dxf2step（`cae_tri_track_dispatch_policy.md`） |

### CAE 商用化ゲート（自律進化）

G1 py_compile → G2 `fleet_satellite_setup_auto.ps1` → G3 K10 probe → G4 再起動 5 分以内復旧 → G5 Meaning Gate (T019)

**記録:** INC-121, bd `fleet-post-reset-recovery-inc121`, bd `Clawdbot_Docker_20260125-a83`, universal_growth.db `FLEET_OPS`, ByteRover `fleet-post-reset-inc121`

---

## [T040] 2026-06-20 DXF2STEP 全図面 combined 偽 SUCCESS 拡張 (INC-125)

**事象:** INC-124 (S11) 対策後も **P38** (`tp-dxf-5941a119`) および **PARTIAL 8件** で TOP 二重輪郭 / multiview 失敗 / 偽 SUCCESS が継続。全109図面監査で **21+ 試行要再スキャン**。

### 症状（3系統）

| 系統 | 例 | 症状 |
|------|-----|------|
| A4 枠 | P38 L1 | 208x293mm; 面積比4.5x -> 20xフィルタ未発動 |
| A3/A2 シート | P4--P9,S1 L1 | 420x297 / 594x420; extrude + multiview 失敗 |
| 同一層副ビュー | P38 L7 | 平面+側面が同一レイヤー -> TOP 二重 |

### 根本原因（5 Why -- P38）

| Why | 内容 |
|-----|------|
| Why1 | TOP に部品が複数 |
| Why2 | L1 枠 + L7 部品+側面が combined |
| Why3 | 20x のみ / A3 未対応 / 島フィルタなし |
| Why4 | multiview 失敗で PARTIAL 止まり |
| Why5 | PNG 幾何監査・NG registry 不足 |

### 対策（2026-06-20 実装済）

| 対策 | 実装 |
|------|------|
| A4/A3/A2 レイアウト層スキップ | `_is_layout_layer_bbox`, `_frame_layers_to_skip` |
| 副ビュー島除去 (X列保持) | `_keep_largest_connected_cluster` |
| multiview 失敗 fallback | `process()` -> `single_profile_extrude` |
| combined 小面積部品優先 | `_pick_part_layer_for_combined` |
| 全件監査 + NG registry | `audit_dxf2step_combined_geometry.py` |

### 採用試行 (10mm)

| 部品 | trial_id |
|------|----------|
| P38 | `tp-dxf-8e205f0e` |
| P4--P9,S1,P46,P47 | `tp-dxf-1c5a1c9d` 等 (handover MD 参照) |

### 禁止

- `tp-dxf-5941a119`, `tp-dxf-a9422cc7` (P38 NG)
- TOP 二重輪郭の combined を SUCCESS / Telegram 合格
- DXF2STEP worker 変更時に checklist 未読

### QC / 記録

- **QC工程表/FMEA/FTA/Fishbone/ロジカルツリー:** `quality_incident_report_20260620_dxf2step_combined_geometry_inc125.md`
- **Checklist:** DXF-QC02,04,07,09 追加 (`dxf2step_combined_geometry_qc_checklist.md`)
- **登録:** `register_dxf2step_combined_geometry_inc125.py`, bd `dxf2step-combined-geometry-inc125`
- **関連:** [T039] INC-124 (S11 初回)

---

## [T041] 2026-06-27 DXF2STEP D3 同一層マルチレイアウト偽 SUCCESS (INC-130)

**事象:** D3 (`tp-dxf-959d5e60`, t=15mm) が manifest `SUCCESS` だが TOP VIEW に **3独立輪郭**（ネスト帯 + H型プロファイル + 8板2x4グリッド）。INC-125 X列クラスタが過結合。

### 症状

| 項目 | 内容 |
|------|------|
| NG trial | `tp-dxf-959d5e60` |
| PARTIAL_OK | `tp-dxf-0430c2ca` (ネスト帯除去、2群残存) |
| FAILED retry | `tp-dxf-998a6e44` (`smallest_part_cluster` 開ループ) |
| 判定 | DXF-QC09 FAIL -> `GEOMETRY_NG` / `false_success: true` |

### 根本原因（5 Why）

| Why | 内容 |
|-----|------|
| Why1 | TOP に部品が3つ |
| Why2 | layer5 全島が single_profile_extrude |
| Why3 | X列クラスタがネスト帯+プロファイル+8板を1塊化 |
| Why4 | 細長ストリップ/ピッチグリッド除外なし |
| Why5 | KPI のみで DXF-QC09 監査未実施 |

### 対策（2026-06-27 実装済）

| 対策 | 実装 |
|------|------|
| ストリップ除外クラスタ | `_pick_part_cluster_segs` / `largest_non_strip_cluster` |
| NG registry | `dxf2step_geometry_ng_trials.json` |
| 試行別監査 | `combined_geometry_audit.json` |
| ThinkPad 同期 | `k10_thinkpad_dxf2step_setup.scp_file` |

### 禁止

- `tp-dxf-959d5e60` の combined を CAE 入力に使用
- DXF-QC09 未監査の Telegram SUCCESS
- D3 で `smallest_part_cluster` 採用

### QC / 記録

- **Report:** `quality_incident_report_20260627_dxf2step_d3_multi_layout_inc130.md`
- **登録:** `register_dxf2step_d3_multi_layout_inc130.py`, bd `dxf2step-d3-multi-layout-inc130`
- **関連:** [T040] INC-125

---


## [T043] 2026-06-29 DXF2STEP P20 パンチ状押し出し / 閉ループQC漏れ (INC-132)

**事象:** `tp-dxf-4fa7ebf5` (P20) で穴形状のはずが板外形なしのパンチ状3D。layer 13 の CIRCLE のみ立体化。ユーザー: 枠と穴は同じレイヤーに見えるが、実際は layer1 外周 + layer13 穴。

### 症状
| 項目 | 内容 |
|------|------|
| NG trial | `tp-dxf-4fa7ebf5` |
| line_to_hole_bbox_ratio | 0.979 (layer13単体) |
| 修正後 QC | merge L1->L13 で ratio 2.605 PASS |

### 対策（2026-06-29 実装）
| 対策 | 実装 |
|------|------|
| DXF-QC04c | `_evaluate_closed_loop_qc` 押し出し前ゲート |
| DXF-QC04d | `profile_hole_layer_merge` |
| DXF-QC18b | `dxf_vs_3d_compare.png` Telegram |
| verdict | `closed_loop_qc_failures` -> FAILED |

### 禁止
- CIRCLE>=3 で `line_to_hole_bbox_ratio<1.20` のまま押し出し
- frame skip 後に outline マージなしで hole layer のみ処理
- 原図DXFなし Telegram SUCCESS

### QC / 記録
- **Report:** `quality_incident_report_20260629_dxf2step_p20_closed_loop_inc132.md`
- **登録:** `register_dxf2step_p20_closed_loop_inc132.py`, bd `dxf2step-p20-closed-loop-inc132`
- **関連:** [T042] INC-131, [T041] INC-130

---
## [T042] 2026-06-28 DXF2STEP 穴加工 vs 島 監査誤判定 (INC-131)

**事象:** `tp-dxf-0430c2ca` (D3 busbar) を `GEOMETRY_PARTIAL_OK` と判定したが、ユーザー指摘: 2D上の「島」は **別部品ではなく穴・切欠き加工**（124 CIRCLE、1枚板 338x200mm）。エージェントは `original_dxf.png` を目視せず Telegram 合格を報告。

### 症状

| 項目 | 内容 |
|------|------|
| 誤判定 trial | `tp-dxf-0430c2ca` (PARTIAL_OK -> **GEOMETRY_OK** 修正) |
| 真の NG (変更なし) | `tp-dxf-959d5e60` (3 外周輪郭 -- INC-130) |
| 横断監査 | 443 archives; 誤 adjudication ファイル **1件のみ** |
| 別問題 | 82 SUCCESS が frame+part 監査 SUSPECT/NG (INC-124/125 系) |

### 根本原因（5 Why）

| Why | 内容 |
|-----|------|
| Why1 | 2D 密集形状を「複数島」と誤読 |
| Why2 | 124 穴 + H型切欠きがシルエット上密集 |
| Why3 | INC-130「8板グリッド」文言を穴配列に転用 |
| Why4 | DXF-QC09 が外周輪郭と内側穴を分離していない |
| Why5 | original_dxf.png 目視ゲートなし |

### 対策（2026-06-28 実装済）

| 対策 | 実装 |
|------|------|
| 判定修正 | `combined_geometry_audit.json` -> GEOMETRY_OK |
| DXF-QC17 | 外周輪郭 vs 穴加工 |
| DXF-QC18 | original_dxf.png 目視必須 |
| 横断監査 | `audit_dxf2step_hole_vs_island_misclass.py` |

### 禁止

- 穴・CIRCLE 密集を「別部品島」と adjudication すること
- `original_dxf.png` 未目視の formal_adjudication / Telegram OK
- INC-130 真 NG (`959d5e60`) と穴加工を混同すること

### QC / 記録

- **Report:** `quality_incident_report_20260628_dxf2step_hole_vs_island_audit_inc131.md`
- **登録:** `register_dxf2step_hole_vs_island_inc131.py`, bd `dxf2step-hole-vs-island-inc131`
- **Scan:** `data/workspace/dxf2step_hole_vs_island_audit_20260628.json`
- **関連:** [T041] INC-130

---


**事象:** ThinkPad DXF2STEP `tp-dxf-9d04f260` (S11, t=10mm) が `layers=2/2 combined=True verdict=SUCCESS` だが、`combined_views.png` の TOP VIEW に **無関係な2つの外形（矩形枠+バスバー）が重なって表示**。下流 CAE / 金型用途に **NG**。

### 症状

| 項目 | 内容 |
|------|------|
| NG trial | `tp-dxf-9d04f260` |
| OK trial (修正後) | `tp-dxf-dc852457` |
| Telegram | 誤って SUCCESS 報告 |

### レイヤ実態 (S11.dxf)

| Layer | 役割 | BBox (mm) |
|-------|------|-----------|
| **1** | 図面枠（部品ではない） | 208 x 293 |
| **3** | バスバー平面図（正） | 12 x 17.6 |

自動割当: layer1=**front**, layer3=**top** -> multiview 交差/compound -> TOP VIEW 二重輪郭。

### 根本原因（5 Why）

| Why | 内容 |
|-----|------|
| Why1 | TOP VIEW に2外形 |
| Why2 | 枠層を front、部品を top として slab 合成 |
| Why3 | `_assign_views_auto` がシート上Y位置のみで判定 |
| Why4 | 枠層フィルタなし、compound でも SUCCESS |
| Why5 | KPI が `layers_done` + `has_combined_step` のみ |

### 対策（実装済み）

| 対策 | ファイル |
|------|----------|
| 枠層除外 (>20x面積) | `dxf2step_worker._filter_frame_layers` |
| 単一層 combined | `_export_single_layer_combined` |
| compound -> FAILED | `evaluate_build_log`, `reconstruction_status` |
| QCチェックリスト | `dxf2step_combined_geometry_qc_checklist.md` |
| 全DB記録 | `register_dxf2step_s11_multiview_overlap_inc124.py` |

### 禁止

- TOP VIEW 二重輪郭の `combined.FCStd` を出荷・Telegram SUCCESS
- `tp-dxf-9d04f260` 系成果物の再利用
- 枠層 `1.FCStd` を primary_fcstd として handoff

### QC工程表 / FMEA / チェックリスト

- QC: DXF-QC10..14 (`dxf2step_combined_geometry_qc_checklist.md`)
- FMEA: `multiview_compound_fallback`, `combined_geometry_ng`, `wrong_primary_fcstd` (sample=S11)
- 蓄積: universal_growth.db, thinkpad_dxf2step_quality_analysis.jsonl, fmea_registry, Turso, Obsidian, Beads, ByteRover

**記録:** INC-124, bd `dxf2step-s11-multiview-overlap-inc124`, ByteRover curate, `docs/INCIDENT_LOG.md`

---

## [T044] Robot walk thigh mesh misidentified as knee pads -- INC-133

**Date:** 2026-06-29 JST

**Symptom:** Robot walk V19/V20/V21/V23 still showed no visible thigh swing even when numeric checks suggested leg motion.

**User evidence:** `C:\Users\yasu\OneDrive\デスクトップ\太もも.jpg` clarified the intended thigh region: the long upper-leg shell from pelvis/hip to knee, not the small knee-pad shapes.

**Wrong assumption:** `robot_0_part34.glb` and `robot_0_part35.glb` were treated as thighs. They are knee-pad / near-knee decorative parts.

**Correct mapping after review:**

| Part | Meaning |
|---|---|
| `robot_0_part25.glb` | Combined pelvis + left/right upper-leg shells |
| `robot_0_part34.glb`, `robot_0_part35.glb` | Knee-pad candidates, not thighs |
| `robot_0_part23.glb`, `robot_0_part24.glb` | Lower-leg / shin shell candidates |

**Root cause:** PartPacker grouped pelvis and both visible upper-leg shells in one GLB. QA measured nearby skeleton/keypoint/root motion instead of visible thigh mesh axis swing.

**Countermeasure implemented:** Preserve-first split of `robot_0_part25.glb` into three GLBs:

- `robot_0_part25_pelvis_center.glb`
- `robot_0_part25_upperleg_l.glb`
- `robot_0_part25_upperleg_r.glb`

**Verification artifact:** `D:\AI\PartPacker\output\flow_big_parts_strict_pvae_20260628_025827\part25_split_pelvis_thighs\part25_split_pelvis_thighs_review.png`

**Strict prevention rule:** Before V24 or later walk animation, require a labeled anatomical part-identification gate. The thigh must be the long hip-to-knee visible shell, and rendered-video QA must prove that this visible mesh swings around the hip joint.

---

## [T045] Robot walk target box (Cube) disappearance and walk IK axis mapping calibration error -- INC-134

**Date:** 2026-06-29 JST

**Symptom:** 
1. The target Box (Cube) disappears/falls through the floor on episode reset, suspending learning.
2. Unity logs are flooded with Animator not initialized and setting angular velocity warnings, causing Editor hang/slowdowns.
3. C# script compiles silent watchdog disable on assembly load.
4. Python ML-Agents environment throws AttributeError on np.bool and StrictVersion version checks.
5. Robot walk knee-bending and foot-sliding evaluation failed QA test (Verdict: FAIL, Score: 48).

**Root Causes:**
1. targetBox configuration (isKinematic=true, useGravity=false) was skipped when pre-assigned in the Inspector.
2. Speed parameter updates in FixedUpdate did not check animator initialization/active state, throwing unhandled exceptions.
3. static watchdog flags reset to default on assembly reload.
4. Python 3.10+ and numpy 1.24+ incompatibilities with legacy ML-Agents library.
5. Incorrect IK target world-local coordinate mapping (Y and Z axes swap/sign issues) in preview script.

**Countermeasures Implemented:**
1. Separated pre-assignment null check from physical attribute assignment in `RobotMLAgent.cs`.
2. Added `isActiveAndEnabled` check and try-catch around `anim.SetFloat("Speed")` in `RobotMLAgent.cs`.
3. Restored watchdog active state using static constructor checks in `AutoPlayLoop.cs`.
4. Patched `mlagents_envs/base_env.py` to use `bool` instead of `np.bool`.
5. Reverted the incorrect Y/Z coordinate swap and corrected local Y sign (`-(foot_y - head_local.y)`) and local Z mapping for `IK_Foot` and `IK_Pole` targets in `robot_parts_walk_preview_v16.py`.

**Verification Artifacts:**
*   Blender Walk Blend: `D:\AI\PartPacker\output\flow_big_parts_strict_pvae_20260628_025827_v16\robot_walk.blend`
*   Gait QA Report: `D:\AI\PartPacker\output\flow_big_parts_strict_pvae_20260628_025827_v16\robot_walk_keypoint_qa.md` (Verdict: PASS, Score: 100)

**Strict Prevention Rules:**
1. Always verify targetBox physical properties outside null checks.
2. Apply full exception handling and active check for Unity Animator updates inside Agent steps.
3. Validate IK axis orientations with Rest Pose local joint axes before baking animations.

**記録:** INC-134, bd `robot-walk-ik-axis-disappearance-inc134`, ByteRover curate

---

## [T046] V50 robot walk: 「胴/肩の脱離・左前腕手の脱離・左脚破損」の真因は"未溶接メッシュ＋甘すぎる接合ゲート"であって形状破損ではない -- INC-140

**Date:** 2026-07-02 JST

**Symptom (ユーザー目視):**
1. 胴体と両肩が外れて見える
2. 左腕の前腕と手が外れて見える（空中に破片が浮く）
3. 左脚のメッシュが破損して見える

**当初の誤った結論（要修正）:** 比較ゲートの `candidate_has_more_large_disconnected_components_than_original`(component比 7.27×) を「カメラ構図(寄り)によるスケール・アーチファクト」とだけ解釈した。実際にはNORM(前景2%基準)で3.84×の分離が残っており、**本物の分離信号を過小評価していた**。ユーザー目視が正しかった。

**検証（すべて再現可能・read-only）:**
- 実フレーム目視: `scratch/v50_preview_shoulder_socket_180/frames/frame_0001..0180.png` → 空中に浮く破片・上半身が画面外・巨大な低ポリ球状の胴を確認。
- 接合ゲートレポート `scratch/v50_preview_shoulder_socket_180/v50_joint_attachment_gate_report.json`:
  - `shoulder_R` rest距離 = **0.326** に対し許容 `rest_tol = 0.3296`(=身長2.746の**12%**)。**わずか0.003差で"PASS"**。身長比12%の隙間は明確に見える脱離。→ **T035と同系統のfalse-PASS（甘い閾値で"見える破綻"を見逃す）の再発**。
  - `wrist_L` child距離 最大 **0.227**(身長の8%)= 左手・前腕の分離と一致。
- Blenderヘッドレス メッシュ検査 (`D:\tmp\v50_mesh_inspect.py` → `v50_mesh_inspect_report.json`):
  - `Torso_Core` v=223,426 / f=74,586 / 境界エッジ=**223,428** / DEGEN。verts≈faces×3 = **未溶接(各三角形が独立頂点)の兆候**。
  - `Pelvis_Center` 島=38,386、`UpperLeg_L` 島=38,372、`UpperLeg_R` 島=38,083、`UpperLegCore_L/R` 島=22,905/22,988。全て未溶接パターン。
  - 対照: 腕部品 `geometry_0.001/0.005` は境界=0・島=1(**溶接済み・健全**)。
- Merge by Distance 検証 (`D:\tmp\v50_weld_test.py` → `v50_weld_test_report.json`, 閾値=最大寸法の0.1%):
  - `UpperLeg_L`: 38,372島 → **1島**、非多様体=0
  - `Torso_Core`: 74,419島 → **1島**、境界 223,428→272
  - `Pelvis_Center`/`UpperLeg_R`/`UpperLegCore_L/R`: いずれも1〜2島へ収束、非多様体ほぼ0

**Root cause:**
1. **胴・骨盤・脚メッシュが未溶接**（頂点マージ未実施）。未溶接はスムーズシェーディングが割れ、"破損したように"見える。腕だけ溶接済みで胴・脚が未溶接という非対称が真因。→ **「左脚破損」はメッシュ破損ではなく未溶接**。
2. **接合ゲートの許容値が身長の12%と過大**。0.33の可視隙間を"PASS"にしていた（T035の教訓の再発）。→ 「胴/肩の脱離」がゲートを素通り。
3. 健全な肩・腕シェル部品が**関節ピボットから離れた位置**に置かれている（rest 0.326等）。=位置合わせ/リグの問題。
4. **左手の実体メッシュが存在しない**（`V50_PROXY_Hand_L_*` は24頂点の粗プロキシのみ）。右手は `geometry_0.006`(健全)が存在。

**修正方針（未実施・承認後着手）:**
1. 胴/骨盤/両脚に Merge by Distance（最大寸法の~0.05〜0.1%）を適用し法線再計算 → 「破損」表示を解消（決定的・高確度）。
2. 接合ゲート `v50_joint_attachment_gate.py` の `rest_tol` を身長の12%から**2〜3%**へ厳格化し、"見える脱離"を正しくFAILさせる（T035系統の恒久対策）。
3. 健全な肩・腕シェルを関節ピボットに接触するよう再配置。浮遊破片(`geometry_0.003/0.004` 等 bone=None、プロキシ)を適切なボーンへ割当 or 削除。
4. 左手は右手 `geometry_0.006` のX軸ミラーで生成（生成AI再抽選より決定的）。

**Strict prevention rules:**
1. **PartPacker由来メッシュはリグ前に必ず溶接検査**（境界エッジ数・島数）。verts≈faces×3 は未溶接のサイン。
2. **接合ゲートの許容値は「見える隙間」基準で設定**（身長比12%は無効）。最小値/緩い閾値メトリクスは視覚的破綻を保証しない（[T035]再掲）。
3. 比較ゲートの component_count 等は**構図を揃えてから**評価する（寄り構図はスケール・アーチファクトで数値を歪める）。

### 実施結果（2026-07-02 追記・着手分）

**バックアップ（先に取得）:**
- ソースblend: `scratch/v50_armature_builder_smoke4/robot_walk_v50_armature_build.PRE_WELD_BACKUP_20260702.blend`
- ゲート: `projects/AtsugiMechaCity/v50_joint_attachment_gate.PRE_INC140_BACKUP.py`

**(1) 溶接 実施・検証済み ✅** — `D:\tmp\v50_weld_apply.py` で未溶接7メッシュ(Torso_Core/Pelvis_Center/UpperLeg_L/R/UpperLegCore_L/R + Ground)にMerge by Distance+法線再計算+スムーズシェード。境界エッジ 115k–223k → 数百に収束。出力: `scratch/v50_armature_builder_smoke4/robot_walk_v50_armature_build_WELDED.blend`(原本は非破壊)。**フルボディ描画で胴・骨盤・脚が健全なソリッドと確認**(`scratch/v50_weld_smoke/fullbody_front.png` 他)。

**⚠️ 診断の重要な訂正:** 「左脚破損」は溶接で解消（=未溶接シェーディング割れが真因、メッシュ自体は健全）。だが**本当の主欠陥は"腕の脱離"だった**。フルボディ描画で判明:
- **胴体コア(頭・胸・骨盤・脚)は良好・接続済み**。
- **両腕(上腕/前腕/手シェル)が左右外側へ大きく離れて浮遊**。肘キャップ片(geometry_0.003/0.004/0.023/0.024/0.032/0.033)が隙間に散乱。
- 位置データ(`D:\tmp\v50_arm_positions.py`): 腕**メッシュ**は X≈±0.62〜0.73 / 胴と同じ奥行 Y−1.331。しかし腕**ボーン**は X≈±0.318 / Y−2.049。**腕が自分のボーンから X約0.3 外・Y約0.7 後ろにオフセットして剛体ペアレント**されている → 描画上は脱離、ボーン中心も腕から外れる。
- ユーザーの「胴と両肩が外れて見える」= このカメラでは寄りすぎて上半身が画面外(下記カメラバグ)+腕脱離の複合。

**(2) 接合ゲート修正 実施・検証済み ✅** — `v50_joint_attachment_gate.py`:
- `rest-ratio` 0.12→**0.06** に厳格化（0.33の可視隙間を通していた甘さを是正）。
- **マーカー非依存の直接接触チェック `parent_child_meshes_detached_at_rest` を新設**（`min_pair_distance`: 関節近傍で親メッシュ↔子メッシュの最小距離を測る）。旧方式は「隙間に置いたマーカーへの各片の距離」を測るため、親子が離れていても両方"近い"と誤判定していた（[T035]接触パッチ方式をこのゲートにも適用）。
- 溶接blendで再実行 → **verdict `HOLD_JOINT_DETACHMENT`**、失敗関節 shoulder_L/elbow_L/wrist_L/shoulder_R を正しく検出（旧: 誤PASS）。shoulder_R pair=0.269 = ソケットhackで隠せなかった真の胴↔腕隙間。出力: `D:\tmp\v50_joint_gate_after_inc140.json`。

**(3) 追加で判明した別バグ（未修正・要対応）:**
- **カメラ アスペクト比クロップ**: `v50_final_walk_preview.py:229` の ortho カメラは `ortho_scale=size.z*1.08` を 16:9 横フレームの**幅**に適用 → 縦は身長の約61%しか映らず**上半身(頭・肩)が画面外**。`sensor_fit="VERTICAL"` 等で身長基準に要修正。
- **接合ゲートの盲点(構造)**: shoulder系は親=胴/子=上腕だが、旧実装は腕内関節しか実質見ておらず**腕根↔胴の接続**を測っていなかった。(2)の直接チェックで一部是正済みだが、腕根専用チェックの明示化が望ましい。

**残タスク（未着手・要判断）:**
- **腕の再接合**: 腕メッシュ群を X約0.3 内側・Y約0.7 前へ寄せてボーン/肩に接続。ただし「正しい腕位置」は設計仕様（肩幅・A/Tポーズ意図）に依存し、かつアーマチュア(リグ)改変を伴うため、**推測で動かさず**方針承認が必要（CLAUDE.md「推測で仕様を作らない」/ Surgical Changes）。ボーン基準にメッシュをスナップ→ボーンYを胴奥行に補正、が有力案。
- カメラ修正、浮遊シャード除去、左手ミラー生成（右手 geometry_0.006）。

**検証成果物:** `D:\tmp\v50_mesh_inspect_report.json` / `v50_weld_test_report.json` / `v50_weld_apply_report.json` / `v50_arm_positions.py` / `v50_joint_gate_after_inc140.json`、`scratch/v50_weld_smoke/{fullbody_front,fullbody_side,upper_front_zoom}.png`、`scratch/v50_preview_shoulder_socket_180/frames/`

### 腕再接合 実施結果（2026-07-03 追記・承認後実装分）

**方針:** ユーザー指定の保護済みオリジナル `KEEP_ORIGINAL_..._v50_BASELINE\robot_walk.blend` を正解参照とし、全46メッシュのワールド行列をダンプ(`C:\v50_work\orig_matrices.json`)→現行ビルドの腕14メッシュへ復元。

**重要発見: 現行ビルドは全メッシュのY(奥行)が-1.331に平坦化されていた。** 腕は単純な平行移動ではなく部品ごとに姿勢復元が必要だった（オリジナルは前腕が前方に自然に出るポーズ）。

**実施内容 (`C:\v50_work\v50_arm_reattach.py`, 非破壊 → `..._WELDED_ARMFIX.blend`):**
1. **アーマチュアが2体存在**（`Robot_Mechanical_Armature`=レガシーAction保持 / `V50_Generic_Armature`=腕メッシュの実際の親・previewが操作）。**両方**の腕ボーン(UpperArm/LowerArm/Hand L/R)をオリジナルメッシュ群から導出した関節ピボット（shoulder=肩ボールシェル0.012/0.022中心、elbow=肘キャップ0.023/0.024中心、wrist=前腕端0.005/手0.006から導出）へ移動。※初回実行は片方のみ編集し腕アニメが旧ピボットで回る失敗→両方編集で解決。
2. 腕メッシュ14個のmatrix_worldをオリジナルからコピー（ボーン編集**後**に実施、順序重要）。
3. マーカー/SHARED_CORE/左手プロキシを新ピボットへ。
4. 検証: 全幅 1.749→**1.150(オリジナルと一致)**、フルボディ描画でオリジナルと目視一致。

**preview/gateで追加発見した3バグ（すべて修正済み）:**
- **(a) 巨大球バグ** `v50_final_walk_preview.py create_shoulder_sockets`: 半径1.0で球生成→`obj.scale`設定のみ→depsgraph未更新のまま`base_matrices()`が**スケール未反映の行列をコピー**→`set_torso_motion`が毎フレーム上書き→**半径1.0の巨大球がレンダーに出る**（これが以前の寄り構図で「球状の胴」に見えていたものの正体）。修正: matrix_worldにスケールを直接焼き込み+view_layer.update()。
- **(b) カメラ縦クロップ** 同 `setup_camera`: 16:9横フレームでAUTO sensor fit→ortho_scaleが横幅に適用され**縦は身長の61%しか映らず上半身が画面外**。修正: `sensor_fit="VERTICAL"` + `ortho_scale=size.z*1.52`（baseline構図=ロボット66%を再現）。
- **(c) プロキシ手の空間取り違え** 同 `update_left_hand_proxy`: プロキシは`geometry_0.005`に親付けされているのに**ワールド座標を`.location`(親ローカル空間)へ直書き**→変位。修正: `matrix_world.translation`経由で設定。

**gate側の追加修正:**
- `geometry_0.005` を HAND_L→LOWER_ARM_L へ再分類（リグ意味論と一致、wrist_L親の誤「遠方」判定を解消）。
- `attach-ratio` 0.05→0.06 に校正: **正解基準のオリジナル自体が wrist_R に 0.115 の隙間を持つ**ため（オリジナルを落とすゲートは校正過剰）。修正前の脱離0.27-0.28は2.3倍マージンで依然検出。
- **hidden測定バグ**: `hide_viewport=True`のオブジェクトはdepsgraph除外でmatrix_worldが恒等行列のまま→**原点にあると誤測定**（wrist_L子距離1.376の正体）。`unhide_measured_objects()`を追加。

**ゲート推移:** 修正前 HOLD(shoulder_L/elbow_L/wrist_L/shoulder_R) → 腕再接合後 HOLD(wrist_L/wrist_R) → 校正+バグ修正後 wrist_R PASS → プロキシ空間修正後 **PASS_JOINT_ATTACHMENT(failed joints: none, 強化基準で全12関節PASS)**。

**最終確認(2026-07-03):**
- 目視: 180フレーム全身レンダーで腕接合・破片なし・歩行動作を確認(`C:\v50_work\preview_full180b/`)。
- オリジナル比較ゲート: **component_count比 7.27→1.12**(ユーザー指摘の分離問題は構図を揃えた状態で解消)。verdict は HOLD_REGRESSION_RISK だが hard flags は foreground(bbox幅0.22: baselineはロボットが画面横断、候補はその場歩き)と **motion比0.17** のみ = リグ欠陥ではなく**参照モーション品質(歩行振幅・前進量)の問題**。これは30体スケールアップ計画のStage A(DiffMimic/100STYLES)の担当領域(→ `docs/troubleshooting/fable5_mecha_multirobot_scaleup_decision_20260703.md`)。
- 修復ツール保全: `projects/AtsugiMechaCity/inc140_repair/`(スクリプト3本+最終ゲートレポート2本+README)。

**教訓(追加):**
1. **Blenderの`obj.scale`/`obj.location`直接代入は親子・depsgraph状態に依存**。オブジェクト配置は`matrix_world`経由が安全（バグa,c共通根因）。
2. **同名ボーンを持つアーマチュアが複数ある場合、メッシュの実際の親を確認してから編集**（`o.parent`/`parent_bone`）。
3. **ゲート校正は「正解基準が通る最小の厳しさ」に合わせる**。基準自体を落とす閾値は過剰校正。
4. **viewport-hiddenオブジェクトの測定は評価前にunhide必須**（depsgraph除外→恒等行列）。

### 膝パッド埋没の発見と全身復元（2026-07-03 ユーザー指摘による追加修正）

**ユーザー指摘:** 「膝のパッドがなくなっているようにみえます」— Telegram送信画像のレビューで発覚。

**診断（全46メッシュをオリジナルと差分照合 `C:\v50_work\diff_vs_orig.py`）:**
- 欠落メッシュ: ゼロ。**膝パッド(geometry_0.008/0.009)は存在するが、Y平坦化(-1.331)で脚メッシュ内部に埋没**していた（オリジナルではY=-1.513で腿の前面に突出）。足パーツは最大0.53の奥行ズレ（オリジナルは足が前後に開いた中間ストライド姿勢）。
- **腕だけ復元した前回対応はスコープ不足**。Y平坦化は全身に及んでいた。
- 追加発見: オリジナルの `SHARED_CORE`（元ビルド自身の関節正解位置）と私のメッシュ推定手首ピボットに**0.12のズレ**。オリジナルにあるgroundtruthを使わず推定していた。

**対応:**
- 復元対象を腕14個→**オリジナル全メッシュ(Ground除く)** に拡張。
- 肘・手首ピボットを `L/R_ELBOW/WRIST_SHARED_CORE` のオリジナル位置に変更（推定値より正確）。
- 検証: depth_y 0.712→**1.285(オリジナル一致)**、正面で膝パッド突出が復活、側面でオリジナルと同じ自然な立ち姿。

**教訓(追加):**
5. **部分復元は禁物 — 正解参照があるなら全体を一括復元する**。「壊れて見える部位だけ直す」と、同じ根本原因(Y平坦化)の他の症状(膝パッド埋没)を見逃す。
6. **正解データ内のground truth(SHARED_CORE等)を最優先で使う**。メッシュ形状からの推定は最後の手段。
7. **ユーザーの目視レビューはゲートより上位の検収**。ゲートPASS後も目視指摘は即座に差分照合で検証する。

**全身復元後の追加修正（同日）:** 復元でオリジナルのストライド姿勢(右脚が奥)が戻った結果、①preview/gateの**脚ピボットY=胴中心固定のハードコード**が実関節から最大0.5ズレて誤swing/誤FAIL(knee_R/ankle_R: pair 0.003で接続済みなのに測定点が遠いだけ) → 隣接セグメント群の実測中点Yから導出する方式に両者修正。②wrist_Rはオリジナル自身の形状(前腕板が手首上0.191で終わり手と0.133の横隙間)由来 → 関節個別許容値 `PER_JOINT_TOLERANCE_RATIOS` を新設し正解基準で校正。**最終: PASS_JOINT_ATTACHMENT(全12関節)+depth 1.285/幅1.150=オリジナル完全一致+膝パッド・ストライド姿勢復活を目視確認**(`C:\v50_work\preview_full180d/`)。教訓8: **測定点・回転軸のハードコード座標は、レイアウト復元で無効化する — ピボットはメッシュ実測から導出せよ**(30体マニフェスト設計の必須要件)。

**記録:** INC-140, 関連 [T035]/[T033]/[T045], bd `Clawdbot_Docker_20260125-sbj`（旧キー `v50-robot-unwelded-mesh-and-loose-joint-gate-inc140`）

---

## [T047] Genesis 1.2.1 でV50 RL学習環境を組む際の3つの罠（Stage A実装時） -- INC-141

**Date:** 2026-07-03 JST | bd: `Clawdbot_Docker_20260125-6li`

**症状:** Stage Aトレーナのdevランで、ロボットが完全静止（vx=0.00固定・up=1.00固定・転倒0・pose_err≈1.0）。学習が成立しない。

**根本原因3つ（すべてプローブで実証・解決済み）:**
1. **MJCFの`<actuator>`(gear 400等)が「非PD還元型アクチュエータ」としてインポートされ、`control_dofs_position`と衝突**。`get_dofs_kp`が `act_gain != -act_bias` 例外を出すのがサイン。→ **対処: XMLから`<actuator>`セクションをストリップし、`set_dofs_kp/kv`(1Dテンソル・全env共有)で明示PD設定**。
2. **スポーン高の推測ミスで足が床に8cmめり込み**、接触ソルバに保持されて静止。→ **対処: 追加Plane()をやめ、MJCF自前の床+`get_qpos()`キャッシュ(ネイティブスポーン)+`set_qpos(envs_idx=)`でリセット**。高さのハードコード全廃(INC-140教訓8と同型)。
3. **「重力が効かない」は誤診だった**: +1.0持ち上げテストの静止位置(z≈1.35)が偶然「追加平面上の立位高さ」と一致していただけ。重力・接触は正常。→ **教訓: 浮遊疑いの検証は「立てない高さ」まで持ち上げて落下速度を確認する**。

**その他の実測知見:**
- `get_pos()`は相対系(スポーン=0)、`get_qpos()[:, :3]`が絶対系。**混用禁止**。
- `set_pos`はデフォルト`relative=True`。絶対指定は明示的に`relative=False`。
- 関節可動域はMJCFのdegree指定が正しくrad変換される(±40°→±0.7rad確認)。
- 参照モーションJSON `v50_ref_motion.json` は**壊れている**(root前進0.0・股振幅0.5°、DOFOrder 18に対しframe長19)。Stage Aはトレーナ内生成の解析sin歩容(股11°+前進0.8m/s目標)で代替。エクスポータ修理はStage B(100STYLES置換)で無用化されるため行わない。
- 検証ずみ健全状態: pose_err 0.005〜0.02・転倒が発生する・立位z≈0.44。

**成果物:** `rl_integration/stage_a/train_v50_walk_tracking.py`(自己完結PPO・外部RLライブラリ非依存)、プローブ群 `C:\v50_work\probe2-8.py`、本番ラン `C:\v50_work\stage_a_run1\status.json`(10イテレーションごと更新)。

**追記(2026-07-04) 罠#4 — 最重要:** **`get_vel()`/`get_ang()`(および`get_links_vel`)がこのMJCF関節体で常に0を返す**。run1〜run3(計3ラン・約4時間)は速度報酬が常時0・観測の速度が全盲のまま学習していた(足踏み収束の真の根本原因)。発見手法: ロールアウトプローブでqposの有限差分(実測±0.7m/s)とget_vel(0.000)の不一致を直接照合。**対処: 速度は`get_qpos()`の有限差分で自前計算**(线速度=Δpos/dt、角速度=連続quat差分)。**教訓: 物理量のゼロ張り付きは「動いていない」ではなく「計器が死んでいる」を先に疑い、独立した計測(有限差分)と突き合わせる**。run4(2026-07-04 08:11起動)で速度信号の復活を確認済み(未学習時vx≈-0.4の実値)。
また run2 の途中診断として: 目標速度0.8m/sは11°歩容の理論最大(~0.24m/s)を超え**運動学的に到達不能**だった(罠#5: 参照モーションの到達可能性を先に検算する)。run3以降は目標0.25m/s+股17°+周期1.2sのカリキュラム式。

---

## [T048] 2026-07-01〜07-05 Becky/Gmail添付ファイル消失 + Postgres WAL繰り返し破損 + email_db_lock無限スタック（INC-142）

**Date:** 2026-07-01〜2026-07-05 JST

**発端:** ユーザー報告「今日の朝までK10にBecky等180GB相当のデータがあったが消えている」。セッション開始前の削除であり、**直接の原因はコード調査からは特定できず**（push型`becky_b64_receiver.py`・pull型`k10_becky_puller.py`いずれも削除ロジックなし）。プロジェクトにBecky/Gmail取り込みパイプラインが**複数系統並行稼働**していたことが判明:
1. Push型: Vivobook `becky_b64_uploader.py` → K10 `becky_b64_receiver.py`(旧D:\tmp\becky_attachments、現在はF:外付けHDD)
2. Pull型: K10 `k10_becky_puller.py` ← Vivobook `vivobook_becky_fileserver.py`（`D:\tmp\becky_attachments\{mailbox}.mb\...`に生ミラー保存、**デコード/取込スクリプトが存在せず未処理のまま23,027ファイル滞留**）
3. Gmail一括: `gmail_imap_downloader.py`（デフォルト`--before 2013-06-01`のため2013年6月以降13年分が未取得のまま放置されていた）
4. Gmail継続RAG索引: `continuous_email_ingest_daemon.py`（Paperlessとは別系統、`email_search.db`用）

**誘発した二次障害（本セッション中に発生・私の操作が引き金）:**
- Eドライブ(Docker/WSL vhdx)が容量ゼロ→Becky取込全件`No space left on device`失敗。`docker image prune`後もWindows側vhdxが自動縮小せず、diskpart compactが必要と判断
- コンパクトのためDocker Desktopを`Stop-Process -Force`で強制終了 → **コンテナ内PostgresがSIGKILL相当を受けWAL破損**（`PANIC: could not locate a valid checkpoint record`、既知[T039]と同型）
- `pg_resetwal -f`で復旧するも、**トランザクションID巻き戻りにより複数テーブルで`uncommitted xmin needs to be frozen`/TOAST欠損が多発**（django_celery_results_taskresult, documents_tag, documents_document）。`pg_surgery`拡張の`heap_force_freeze`/`heap_force_kill`で該当タプルのみ安全に修復（該当4行のみ実損失）
- 上記とは独立に、Postgresが**自動再起動9,068回**のクラッシュループに突入していたことが判明（`docker inspect --format '{{.RestartCount}}'`で検出）。手動stop→resetwal→startでカウンタリセットし収束
- `continuous_email_ingest_daemon.py`のGmail増分索引が**2026-06-20から2週間"error"状態でスタック**。真因は`email_db_lock.py`のロックファイル(`email_search_ops.lock`)が28バイトのNULLバイトに破損し、`parse_lock_pid`がpidを解析できず`_clear_stale_lock`が何もせず早期returnする設計バグ（破損ロックは永久に自己解除されない）
- D:ドライブが空き0GBまで枯渇（`data/workspace`80.5GB, PLATEAU 44GB等）。Bashツールの出力キャプチャ自体が失敗する事態に。**未解決、要フォローアップ**

**対処済み:**
- `heap_force_freeze`/`heap_force_kill`でPostgres破損4行を除去・全70テーブルREINDEX完了
- `chown -R 1000:1000`でPaperlessパーミッション修復（T039既知手順）
- `email_db_lock.py`に**ロック年齢ベースの孤立ロック検出**を追加（pid解析不能でも30分以上古ければ自動削除）→ コード修正済み・動作確認済み
- Becky添付を外付けHDD(F:)へ再送信・Paperless consumeへ展開（`becky_ingest_attachments.py --all`, デコード468件成功）
- Gmail(2013年6月以前)を`data/workspace/email_rag_sender_filters.json`のblacklist_patternsで事前フィルタ（1,021通・添付67件を隔離、削除はせず`data/workspace/gmail_blacklist_excluded/`へ退避）
- n8nに`Becky/Gmail DB Ingest Report (30min)`ワークフロー新設（documents_tagのサブディレクトリ由来タグで分類・Telegram通知）

**教訓:**
1. **同一データソースに対して複数の独立パイプラインが無documentationのまま並存すると、削除・移行判断を誤る**（本セッションでも「F:に移行済みのはず」と誤って22GBのpull型データを削除しかけた。ユーザーの「本当に確認したか」という指摘で回避）。**削除前は必ず実データ突合（ファイル形式・処理スクリプトの有無）で検証すること**
2. **Docker Desktop/WSLを強制終了する前に、必ずコンテナ側を`docker stop`等でgracefulに止める**（vhdxコンパクト等ホスト側操作が必要な場合でも同様）
3. **ロック/状態ファイルの自己修復ロジックは「解析失敗」と「解析成功だが無効」を区別し、前者も時間ベースでタイムアウトさせること**（さもないと壊れたロックは無限に居座る）
4. **`docker inspect --format '{{.RestartCount}}'`は無停止クラッシュループの検出に有効**（ログのtailだけでは気づきにくい）

**記録:** INC-142, bd `Clawdbot_Docker_20260125`（本エントリ作成時点でbd issue番号は未採番、次回セッションで補完）


---

## [T048] DXF2STEP暴走ループ(3度目)がD:を毎分1GB消費 — 全件失敗のまま巨大FMEA記録を無限生成 -- INC-142

**Date:** 2026-07-05 JST

**症状:** D:空きが126G→51Gへ約1時間で減少(毎分約1GB)。放置なら約50分で枯渇=T039(PostgreSQL WAL破損)の再現条件。

**犯人(実測特定):**
- `data/workspace/universal_growth.db` = **37.8GB**(膨張中)
- `data/workspace/thinkpad_dxf2step_quality_analysis.jsonl` = **13.8GB**(膨張中)
- 書き込み元: `k10_thinkpad_dxf2step_loop.py --daemon`(PID 16272) + `k10_tri_track_cae_orchestrator.py --continuous`(PID 30316)

**根本原因:** ThinkPadのDXF2STEP試行が**全件FAILED(`all_layers_failed`)のまま回り続け**、失敗のたびにFMEA/FTA/なぜなぜ/fishboneの巨大レコードをjsonlとgrowth.dbへ書き込み。「失敗→分析→同じ失敗」の無意味ループ=**[T019]意味ゲート違反、[T041]-[T043]系統の3度目の再発**。

**対処(2026-07-05 ユーザー承認のうえ実施):**
1. 両プロセスをStop-Process(全件失敗中のため損失なし)→ growth.db膨張の停止を実測確認(45秒で増分0MB)
2. jsonl 13.8GBを `F:\runaway_quarantine_20260705\` へ隔離(D:空き47Gへ回復)
3. growth.db(37.8GB)は後日診断: 中身の異常レコード確認→クリーニング→VACUUM

**恒久対策(未実装・bd起票):** 両スクリプトに**意味ゲート**を実装 — 「連続N回(例:10回)同一failure_classで失敗したら自動停止+Telegram報告」。失敗の分析記録は要約1件のみとし、同一根本原因の重複FMEA生成を禁止する。**教訓: 品質分析の自動生成は、失敗が止まらない限り、それ自体がディスク攻撃になる。**

**関連:** [T019][T039][T041][T042][T043]、INC-142

## [T049] 外観検査AI: 良品参照方式が部品の回転・傾きに弱い(偽NG) — orb_ecc+minAreaRectで対策 (2026-07-12)

**事象:** visual_inspection_ai の判定は良品画像の平均±標準偏差とのピクセル差分方式。位置ずれは並進ECC(±24px)のみ補正のため、検査品が回転・傾きすると①外観判定: 良品でも全面差分で偽NG(12度回転良品でscore 0.55) ②寸法測定: W/Hが軸平行boundingRectのため回転すると過大測定、の2点でユーザー要件(回転しても正確判定)を満たさなかった。

**対策(実装済み):**
1. `detection/alignment.py` に `align_similarity()` 追加 — ORB特徴点+RANSAC粗合わせ(±180度)→ECC(MOTION_EUCLIDEAN)微調整。シフト判定は画像中心の実移動量(純回転はwarp並進成分が回転中心分大きく出る罠に注意)。失敗時は並進→無補正へ段階フォールバック(REVIEW側に倒れる安全設計維持)。レシピ `model.alignment: "orb_ecc"`。
2. `measurement/geometry.py` — `measurement.rotation_invariant: true` で minAreaRect(回転外接矩形)測定。長辺/短辺を規格nominalの大小に対応付け。annotation.pyにpoly描画追加。

**検証(2026-07-12):** tests/test_rotation.py 6件 + 既存回帰10件 全パス。回転良品スコア: 5度 0.294→0.007 / 12度 0.552→0.009 / 20度 0.786→0.011(推定角は±0.1度精度)。回転15度の寸法測定 W8.823/H5.823/穴1.593mm 全て規格内判定。12度回転+傷はscore 0.052でNG検出維持。

**残課題・教訓:** ①45度など視野からはみ出す回転は情報欠損で残差大(score 0.24) — 撮像は部品全体が視野に入ること ②無地・特徴レス部品はORBマッチ失敗→並進フォールバック(小角度のみECC収束) ③180度対称部品は対称位置に整列され得る(良品判定には無害)。

**追補(同日): 整列残差のスコア床問題も解決** — 回転良品の残差0.009は不良最小値0.0049と分離不能だった。残差は基準画像の勾配(エッジ)位置に集中するため、`model.edge_tolerance: 0.3` を新設し std_eff=max(std, |grad(mean)|×0.3) で許容。実測: 回転良品 5/12/20度とも0.0004以下(不良最小の1/12以下)、エッジ上のバリ0.0094→0.0080で検出維持、傷0.052→0.046。k=0.3は0.5/0.8より欠陥抑制が小さい保守値を採用。テスト計17件パス。edge_tolerance変更後は閾値再校正(recalibrate)を推奨。

## [T050] 外観検査AI: 実データ(MVTec/VisA)で不良検出率が部品種依存(ナット0/4等) — カラー差分+PatchCore-liteを実装 (2026-07-12)

**事象:** 実データセットテスト(reference方式)の不良検出率: PCB 4/4、パイプ 2/4、ネジ 1/4、カプセル 1/4、ナット 0/4。良品の誤NGは5部品種ともゼロ。原因①: グレースケール変換で色系不良(ナットcolor等)が消える。原因②: 閾値=校正良品max×1.3のため、整列しきれない良品1枚で閾値が跳ね上がり微小不良(0.06〜0.20)を取りこぼす。原因③: 画素差分方式自体の検出力限界。

**対策(実装済み):**
1. **カラー差分** — ReferenceModelTrainer(color=True)でBGR 3ch統計(median/MAD)を保存。Detectorは3ch自動判別・チャンネル毎zの最大で判定。warpはグレーで推定し3chへ適用(alignment.pyを estimate_similarity_warp / apply_warp に分離リファクタ)。等輝度色相不良の検出をテストで確認(グレーでは不可視、カラーで3倍以上分離)。
2. **PatchCore-lite** — `detection/patchcore_torch.py` 新規。anomalibフルスタック(lightning等・CLI版依存)を回避し torch+torchvision のみで直実装: WideResNet50-2 layer2+3特徴→3x3平均プール→コアセット(ランダム10%・シード固定)→最近傍距離。`real_dataset_demo.py --engine patchcore`。導入は `pip install -r requirements-patchcore.txt`(CPU可・初回にImageNet重み132MB自動DL)。
3. 校正良品 CALIB_N 5→8枚(閾値の頑健化)。

**検証:** カラー4テスト+回転回帰7テスト等13件パス(sandbox)。PatchCoreはtorch必要のためスモークテスト(tests/test_patchcore.py, torch無しはskip)をK10で実行のこと。

**教訓:** 閾値=max×1.3は良品外れ値1枚に脆弱(median+k×MAD化は未実装・今後の候補)。実データでの検出率は部品種ごとに大きく異なるため、部品種別の方式選定(色不良→カラー、微細テクスチャ不良→PatchCore)が必要。

**追補(2026-07-13): 全数評価ハーネスで実力を数値化 → PatchCore圧勝・方針確定** — `scripts/evaluate_real_datasets.py`(良品/不良各60枚上限、MVTecは独立test/goodで誤検出率評価)+`scripts/threshold_strategies.py`(中央値+k×MAD、テスト6件)を実装。**AUROC実測: PatchCore=ナット0.939/ネジ0.421/カプセル0.825/PCB 1.000/パイプ0.977 vs referenceカラー=0.371/0.170/0.499/1.000/0.614**。結論①reference画素差分は治具固定・合成部品専用(自然変動の実部品には不向き、AUROC<0.5=逆転すらある) ②PatchCoreを実部品の既定エンジンとする ③ネジ両方式失敗の対策=学習15→60枚・校正8→16枚・入力256→320px(実装済・再評価待ち) ④カプセル「AUROC0.825なのに検出17%」=閾値設定の問題→運用指標「検出率@誤検出5%」をハーネスに追加。教訓: 5枚デモの印象と全数AUROCは別物。改善判断は必ず全数評価で。

## [T065] Moldflow 2010既存ゲートのMCP読取はUDM/NDBCを使う — INC-149 (2026-07-16)

- Goal: ユーザーが設定した射出ゲートをStudy変更なしでMCP確認する。
- Observed facts: 直接NDBC APIなし。実機Fusion meshはCompleted、3635 nodes、7278 triangles。NDBC type 40000が1件、node 2。
- Decision rule: IF Moldflow 2010の既存射出位置を読む THEN 一時UDMの`NDBC{}`からtype 40000/40002/40003を抽出する BECAUSE 直接getterは提供されない。
- Procedure: active Study -> `Project.ExportModel` -> NDBC抽出 -> node座標照合 -> UDM削除 -> cleanup status出力。
- Verification: node 2、XYZ=(-50.0000007451, 2.7391463518, 23.8075219095)、gate count 1、cleanup error 0、analysis false。
- Failure signature: hash一致でも旧応答なら8765の既存PID残留。所有者確認後、そのPIDだけ再起動する。
- Scope limit: intersection 1484、overlap 742、max AR 121.794のため解析妥当性は未承認。

## [T066] Dynabook Moldflow MCPでcopy-onlyメッシュ生成を開始する実機契約 — INC-151 (2026-07-17)

- Goal: `Moldflow_study (copy)` の原本を守り、MCPからFusionメッシュ生成と将来のゲート設置を行う。
- Observed facts: K10 Tailscale復旧後、旧bridge `100.98.133.40:8765/mcp` version 0.4.0へ接続。Synergy COMは64-bit registry viewのみ。64-bit Automation sessionでVersion 2010、active project/study、metric unitsを確認。`MeshNow(False)`はerror 0で受理され、UI進捗30%。入力STL 272 nodes/552 triangles、non-manifold edges 4、initial max AR 293.2793、average AR 63.4481。Dynabook i5-5200UはCPU 100%。
- Decision rule: IF Moldflow 2010 GUIが通常起動でAutomationを拒否する THEN study保存後にSynergyを正常終了し、64-bit cscriptでAutomation sessionを作ってから同じproject/copyを開く BECAUSE COMは64-bit viewにのみ登録され、通常GUIと外部Automationが競合する。
- Procedure: VPN identity -> MCP 8765 initialize/list-tools -> venv Python -> bind Tailscale IP -> 64-bit COM state -> canonical active-copy name -> one bounded mesh start -> poll `MeshStatus` without duplicate start -> mesh completion after which gate node is explicitly selected.
- Verification: live tool list includes `moldflow_mesh_active_study_copy` and `moldflow_set_gate_active_study_copy`; mesh start returned `ACTIVE_STUDY=moldflow_study_(copy).sdy`, `MESH_NOW_ERROR=0`, `MESH_STATUS=Running`; analysis_started=false.
- Failure signatures: `SSH tunnel did not open 127.0.0.1:18765`; wrong service/404 on incompatible 8766 agent; `No module named mcp` from global Python; HTTP 421 from bind/Host mismatch; COM 429 from wrong bitness/non-Automation GUI; immediate `EMPTY_MESH` while status is Running.
- Recovery: never repeat mesh while Running. Restart only the verified MCP PID. Use `G:\moldflow_bridge\.venv\Scripts\python.exe`, `MOLDFLOW_MCP_HOST=100.98.133.40`, and 64-bit Automation session. Remote backups are beside the deployed server.
- Scope limits: mesh completion, final quality, gate creation, material assignment, and analysis success remain unproven as of this entry.

## [T067] 歩行RLの「best travel」は歩行距離ではなく転倒滑走距離だった (2026-07-23)

- Goal: `walk_auto` が 2026-07-20 以降 `walks_then_falls <-> stand_freeze` を往復し best travel 1.85m から改善しない原因を特定する。
- Observed facts (`stage_a/check_reference_gait.py`, 16 envs / 20 s / policy action ゼロ):
  - 解析sin歩容: t=2.34s で転倒、最終 travel **1.559 m**、final upright 0.0。
  - 再ターゲット参照 `C:\v50_work\refs\walk.json`: t=1.92s で転倒、最終 travel **-1.608 m**(後退)、final upright 0.0。
  - **両参照とも全区間で mean_contact_L/R = 0.98/0.99** — 一度も足が地面から離れない。遊脚相が存在しない。
  - 歴代 best と称した値は 1.63 / 1.71 / 1.85 m。**開ループ転倒滑走 1.56 m とほぼ同一**。
- 参照モーション自体の欠陥(`walk.json`, 64 frames):
  - `ankle_L`/`ankle_R` の peak-to-peak = **0.00 deg**(+20.05 deg 固定)。足首が完全に凍結。
  - `knee_L`/`knee_R` p2p = 7.6 / 8.3 deg(人間の歩行は約60 deg)→ 足の地面クリアランスが構造的にゼロ。
  - hip_L と hip_R の逆相相関 = **0.582**、最良一致は lag 141 deg(歩行に必要な180 degではない)。sin歩容は0.999。
  - hip の p2p が左右非対称(23.02 / 18.58 deg)、全関節が正方向オフセット(恒久的な前傾中腰)。
- Decision rule: IF 歩行学習の指標が素の変位である THEN 転倒と歩行を区別できないので、指標を「転倒しなかった env のみの距離」に置き換える BECAUSE この胴体は無操作でも 1.56 m 前方に倒れ込む。
- Procedure: 学習を触る前に必ず `check_reference_gait.py` を実行し、参照歩容が単独で接地離地を発生させるか確認する。`survived=false` かつ `mean_contact≈1.0` なら報酬設計は無意味。
- Verification: `train_v50_walk_rsl.py` の eval を `clean_travel_m`(全区間直立を維持した env のみ)+`survival_rate` に変更。30 iter のポリシーは raw travel 0.167 m に対し正しく `survival_rate=0.0 / clean_travel_m=0.0` を返す。
- Failure signature: status.json の travel が伸びているのに upright が最終的に 0.0、かつ両足 contact が常時 1.0。
- Scope limit: 「参照が開ループで転倒する」こと自体は mocap 再生では正常(RLが補正するのが前提)。異常なのは **遊脚相が一度も無いこと**と**足首凍結・hip位相141 deg**という再ターゲット欠陥。RLが学習不能であることは証明していない。
- 関連: bd `Clawdbot_Docker_20260125-776g`、新規 `stage_a/v50_walk_env.py` / `stage_a/train_v50_walk_rsl.py`。

### [T067追補] bvh_retarget の膝符号・足首折り返しバグを修正 (2026-07-24)

- 原因(生系列を MJCF 可動域に対してダンプして確定):
  - **膝符号反転**: MJCF膝可動域は -30°..+10°、大可動側は「負」。人間の屈曲角(acos, 常に≥0, 生値0..67°)を `clip(+knee, -0.52, 0.17)` で写したため +10°上限に飽和し p2p 9°に潰れていた。`clip(-knee)` に反転 → -30°側を使い p2p 27.6/28.4°。屈曲ピークは -30°でフラットトップ=接地クリアランスに有利なのでスケールせず。
  - **足首 atan2 分岐折り返し**: 旧 `series_ankle` は `sagittal_angle(足)-sagittal_angle(すね)` と二つの atan2 の差を取り、各項が独立に ±π 折り返し → 系列が min -185°/DC -92° で +20°上限に凍結(p2p 0.00)。分岐フリーの `signed_sagittal_between(a,b)=atan2(af·bu-au·bf, af·bf+au·bu)` に置換 + `fit_amplitude`(中央値センタリング+90%tile頑健スケールを可動域0.75へ)で写す → p2p 22.5/30.6°、ゼロ中心。生足首 p2p は 178° と可動域±20°を大きく超えるため素のクリップは矩形波化する。
- **hip は変更せず**: 当初「位相141°」と警告したが、これは半周期でなくクリップ全長の半分でロールした測定アーティファクト。実 L-R オフセットは ~166° で mocap として正常。
- 検証: `check_reference_gait.py` を v2 化。開ループ再生はどの参照でも1歩で転倒する(バランスはRLが学習)ため first_fall は情報のみ。合否は参照JSON自身の関節振幅。OLD walk.json=kinematic_ok:false(knee7.6/ankle0.0/足接地0.96) → NEW=true(knee27.6/ankle30.6/足接地0.60)。旧参照は `walk.json.bak_frozen_ankle_20260724` に退避。
- commit: `de300439f6`。bd `Clawdbot_Docker_20260125-bpqh` クローズ。

### [T067決着] 修正参照+接地報酬trainerでフルラン成功 (2026-07-24)

- 2500iter/4096envs フルラン EVAL(deterministic, push有効下): **survival_rate=0.817, clean_travel_m=2.373m/8s, vx=0.305(目標0.331の92%), single_contact_frac=0.732(交互歩行成立), mean_air_time=0.065s**。stochastic も survival 0.777/travel 2.401m とほぼ同等=探索ノイズ依存でない実力。
- 学習推移: ep_len 1.36→15.07s, return -4.2→+44.3, fall_rate(訓練中push有) 1.0→0.53, single_contact 0.37→0.69, 転倒モード low(沈み込み) ~0.09 へ低下。
- 7日間の walks_then_falls<->stand_freeze 停滞(survival~0)を完全突破。決定要因は2つ: ①bvh_retarget の膝符号/足首折り返し修正(参照に遊脚相が生まれた) ②接地報酬(feet_air_time/single_foot_contact)+time_out正処理+obs正規化(rsl_rl)。
- ckpt退避: `C:/v50_work/autonomy/known_good/walk_rsl_20260724_survival0.82_travel2.37.pt`。trainer=`stage_a/train_v50_walk_rsl.py`。
- 残課題: v2互換レンダラ(rsl_rl ckpt: obs189/hidden[512,256,128]+normalizer, 旧render_walk.pyはobs46で非互換)による動画確認 / 地形カリキュラム / 他スキル展開。bd `qnfe` クローズ。

### [T067目視検証] rsl_rl方策の歩行を動画で確認 (2026-07-24)

- `stage_a/render_walk_rsl.py` 新規。旧 `render_walk.py` は v1 ActorCritic(obs46)専用で v2 ckpt(rsl_rl形式・actor 189→512・hidden[512,256,128]+EmpiricalNormalization)と非互換。**正規化器を通さずに生観測を入れると「歩けない」偽陰性になる**ため、必ず `OnPolicyRunner.load` 経由で policy と obs_normalizer を復元する。
- シーンは `V50WalkEnv` にカメラ設定(`cfg["camera"]`)を追加して再利用。レンダ側で別XMLを作らない(INC-141 罠#8)。
- クリーン連続ロールアウト(`--no-dr --no-reset`, 8s, deterministic): **fell=false(一度も転倒せず)・travel 2.427m・vx 0.303(目標0.331の92%)・min_upright 0.918・min_z 0.394(stand_z 0.428から3.4cm低下のみ)**。支持相 **single 0.693 / double 0.255 / flight 0.052** = 人間の歩行比に近く、跳躍(flight大)や這い(single≒0)を数値で否定。接地遷移46回/8s。
- フレーム目視(t=1s/5s/7.9s): 胴体直立・脚交互・腕振りを確認。最終フレームでも歩行継続。
- **罠**: 1envレンダは domain randomization が単一サンプルになるため、不利な質量/ゲインを引くと 2.04s で転倒し実力を過小評価する(初回レンダで実際に発生)。デモ・検証時は `--no-dr` を付ける。また mp4 書き出しは stdout をパイプすると ffmpeg サブプロセスのハンドルが壊れる(Windows OSError 9)ため別プロセスで書く。
- 成果物: `C:/v50_work/walk_rsl_clean/` (PNG81枚 + walk.mp4)、`known_good/walk_rsl_20260724_walk_check.json`。bd `purw` クローズ。

### [T068] 学習時 evaluate() の数字は信用しない — フレッシュenv再ロード検証を必須化 (2026-07-24)

- 事象: 斜面(slope_up 8°)カリキュラムの学習末尾で `evaluate()` が **survival_rate 0.814** を出力。しかし**同じrunが直前に保存したckptを再ロードすると 0.069**。
- 独立3経路で確認: (a)自作verify 0.066 (b)trainer自身の `evaluate()` を保存ckptで再実行 0.069 (c)DR抽選を変えて3回 0.069/0.111/0.245。**学習時の0.814は再現しない**。
- 切り分け: **平地ckptは再現する**(報告0.817 → 再実行0.897 → フレッシュenv検証 0.988/0.990)。よって save/load は健全。**slope ckpt自体も平地では survival 0.88** で無傷。つまり壊れていたのは方策ではなく「測定」。
- 判明した実力(再現可能な値): 斜面は**登坂自体は本物**(生存個体の獲得高度÷斜面期待高度 = 1.08〜1.15、横ドリフト0.195m、全生存個体がランプ上)だが、速度依存が強く cmd0.18→survival 0.404 / cmd0.25→0.256 / cmd0.331→0.07〜0.25。
- 罠の本質: `evaluate()` は**学習に使ったenvインスタンスで一度だけ**測るので偽陽性を出しうる。さらに指令速度を `target_vx`(=訓練指令域[0.15,0.35]の**上端**)に固定するため、実用速度での能力を過小評価もする。
- 恒久対策: `stage_a/verify_policy.py` を新設。**必ずckptをフレッシュenvへ再ロード**し、①複数指令速度のスイープ ②`climb_ratio`(実獲得高度÷地形が与える高度)を報告する。climb_ratio が無いと「幅1.6mのランプから横に外れて平地を歩いただけ」の個体が survival 満点で紛れ込むのを検出できない。
- 教訓: **学習ログの最終行を成果として報告しない。** 保存物から再現した値だけを報告する。

### [T069] blind locomotion は斜面を登れるが階段は登れない — 外受容が必須 (2026-07-24)

- 検証(`verify_policy.py`, フレッシュ再ロード, stairs, 14s, cmd 0.10/0.15/0.20):
  - **travel_m が全速度で 0.556-0.558m の一定値** = 平地助走(TERRAIN_FLAT_RUNUP=0.6m)の端、第1段の直前で停止。指令速度を上げても進まない。
  - height_gained 0.068m(段高0.10mの第1段に片足乗る程度)で以降上がらない。
  - survival 0.88-0.95 と高いが「転ばず立ち止まっているだけ」。学習曲線も it1000で return頭打ち(14.2→13.2)、vx 0.08へ低下、失敗の主因 `low` 0.55(段を越えられず高さ判定に落ちる)。
- **climb_ratio の罠**: stairs で 3.5-4.6 と>1に見えるが、助走境界では terrain_offers≈0.015m と極小のためこれで割った見かけ値。**真の指標は travel_m が助走長で頭打ちすること**。verify_policy の climb_ratio は連続地形(斜面)専用と解釈する。
- 根本原因: 観測(`v50_walk_env` obs 189dim)に**地形高さ情報が無い**。段差は衝突するまで知覚できず、足を先に上げられない。連続地形(斜面)は接地・重力・速度だけで適応できるが、離散段差は不可能。これは既知の一般則(blind policyは連続地形、離散障害は exteroception 必須)。
- 対策(bd 起票済み): legged_gym流の足元 height-scan(例 11x11グリッド)を obs に追加。地形高は privileged critic obs としても供給。段高カリキュラム 0.03→0.10m 併用。
- 教訓: **survival だけ見ると「成功」に見える失敗がある**(立ち止まりも転倒しなければ survival 高)。travel と climb を必ず併読する。

### [T069解決着手] 階段昇降のための外受容(height-scan)実装 (2026-07-24)

- 世界の文献調査（perceptive locomotion）に基づき、blindで不可だった階段に前方地形高さスキャンを追加。
- **terrain**(`train_v50_walk_tracking.py`): `terrain_dz/terrain_xml/build_model_xml` に `stair_h` 引数(段高カリキュラム、既定は現行定数=v1/実行中run不変)。新地形 `stairs_down`=床plane(無限)より下へ掘れないので **上段台(高さ h*N)からスタートし床まで降りる**。解析照合で stairs/stairs_down/非既定段高すべて terrain_dz が geom と 0/60 誤り・worst 0.0000m。
- **env**(`v50_walk_env.py`): `height_scan` cfg で前方K点(既定0.0〜1.0m/11点)ルックアヘッドを **obs末尾に連結**(履歴に折り込まない=移植を綺麗にするため)。値=`terrain_dz(ahead)-terrain_dz(here)`(flat=0規約, 昇段+/降段-)。terrain解析なのでレイキャスト不要・厳密。降段は spawn を `terrain_dz(0)=h*N` 持ち上げて台上着地、`stand_z` は terrain非依存に保ち `expect_z=stand_z+terrain_dz(y)` の二重計上を回避。obs 189→200。
- **trainer**(`train_v50_walk_rsl.py`): `--height-scan/--scan-ahead/--stair-height/--resume-surgery`。**weight surgery**=blind(obs189)ckptを200netへ移植: 共有tensorはverbatim、第1層のみ既存列コピー+新規scan11列ゼロ埋め、normalizer統計もprefix継承 → **移植直後の行動がblindとbit一致(max action diff 0.0)**を検証。よって完成した平地歩行から出発しscanの使い方だけを学習。
- 段高カリキュラム: stage1(昇段0.05m, surgery from flat walker) → stage2(0.10m, 通常resume) → 降段、の順。**各段 verify_policy 再ロード検証必須**(学習ログ不信=T068)。
- 参考文献・ライブラリは bd `y75t` と本セッションログ参照。

### [斜面決着] slope03 修正版で登坂 survival ~1.0・目視確認済み (2026-07-24)

- slope02 の回帰(0.49→0.04)は「一度に変えすぎ」が原因(batch半減+DR過剰)。**変えて害だった2点(batch, gain DR)だけ戻した** slope03: full batch 4096、DR穏当(質量±10%/gain±5%/16群)、cmd[0.12,0.28]、平地ckptから転移、1500iter。
- **verify_policy フレッシュ再ロード(T068)**: survival @0.18=**1.0** / @0.20=0.996 / @0.25=0.996、climb_ratio 1.28-1.36、on_track 1.0=幅内で完全登坂。slope01(0.40-0.49)を大幅更新。
- **目視確認(新グローバルルール初適用)**: render_walk_rsl.py で t=0.8/4.8/7.9s を Read。胴体直立(登坂前傾)・**両腕は肩に連結し腕振り正常(分離なし)**・脚交互・ランプ上を上昇。fell=false, min_upright 0.949, 支持相 single0.69/double0.27/flight0.04。
- VERIFIED ckpt: `known_good/walk_rsl_slope8deg_20260724_survival1.0_VERIFIED.pt`。bd `z15v` クローズ。

### [T069解決] 外受容(height-scan)で階段昇段が成立 (2026-07-24)

- stairs 0.05m段、height-scan有効、平地歩行から weight surgery 移植、1500iter/2048envs。
- **目視確認(グローバルルール)**: render_walk_rsl.py(--height-scan --stair-height 0.05)で t=140/300ステップを Read。ロボットは段の上で直立、**両腕は肩に連結し腕振り(分離なし)**、脚交互で段を上昇。fell=false, min_upright 0.945, 支持相 single0.72/double0.26/flight0.02。
- **verify_policy フレッシュ再ロード(T068)**: survival @0.12=0.818/@0.15=0.906/@0.20=0.844、travel 2.07-2.39m(**速度で変動=立ち止まりでない**)、height_gained 0.335-0.39m(0.05m段で約7段登坂)、on_track 1.0。
- blind(T069)は travel 0.556m一定・height 0.068m(1段)で停止だった。**height-scan が根本解決**。
- VERIFIED ckpt: `known_good/walk_rsl_stairs_h05_20260724_survival0.9_VERIFIED.pt`。
- 残: 段高0.10mへ引き上げ(stage2)、降段(descent_h05が4096envs並列学習中)。

### [T069追記] 段高0.10m一気ジャンプ失敗+descent修正で学習回復 (2026-07-24)

- **段高0.10m昇段(stairs_h10)は失敗**: verify(フレッシュ再ロード) travel 0.58m一定(助走0.6mの端で停止)・height_gained 0.064m(0.10m段を1段も越えず)・目視でも階段下で片足だけ乗せて立ち止まり。原因=0.05→0.10の2倍ジャンプが大きすぎ『hesitation局所解』(文献既知: challenging terrainで動くのを躊躇し立ち止まる方が安全に報酬を得る)。構造は正常(腕連結・姿勢OK)。対策=中間段0.07mを挿入(0.05mからresume)。
- **descent terrain_dz stair_h バグ修正の効果が劇的**: 修正前 descent_h05 は ep 0.02s・fall_by_low 1.0・return -2.25 で1500iter全く学習せず(初手で誤って転倒判定)。修正後 descent_h05b は it250で return 27.7・ep 10.5s・fall 0.35(low 0.10)・single_contact 0.69=正常に降段歩行を学習中。**この即転倒バグは目視(ep 0.02s)で気づいた**=グローバル目視ルールの有効性を実証。
- 教訓: terrain_dz を呼ぶ全箇所で stair_h を渡す(fall判定/base_height報酬/height_scan/spawn)。1箇所でも欠けると段高非既定の地形で沈黙の破綻。カリキュラムの段高ジャンプは2倍が上限の目安、間に中間段を置く。

### [階段降段成立] 0.05m 降段が verify+目視で確定 (2026-07-25)

- descent_h05b(stair_h terrain_dz バグ修正後・平地からsurgery移植・1500iter): return 33.6 peak, fall 0.16-0.28, single_contact 0.77。
- **verify(フレッシュ再ロード)**: survival @0.12=0.852/@0.15=0.949/@0.20=0.922、travel 2.67-3.15m(速度で変動)、**height_gained -0.29〜-0.36m(負値=約6-7段の降段)**、on_track ~1.0。
- **目視(グローバルルール)**: t=150/400フレーム。上段台の縁から階段へ、上体直立で制御降段、両脚が段を交互に降り、両腕は肩に連結し腕振り。崩落・転落でない。
- VERIFIED ckpt: `known_good/walk_rsl_descent_h05_20260725_survival0.9_VERIFIED.pt`。
- **マイルストーン: 階段 昇段0.05m ✅ + 降段0.05m ✅ 両方成立**(いずれも verify+目視済)。

### [自然歩容] 対称augmentation+報酬で関節対称化・足高は残課題 (2026-07-25)

- 測定した跛行(hip 24/43度・足上げ4/24cm・anti-phase 0.13)に対し、rsl_rl mirror augmentation + gait_symmetry/foot_clearance(2乗ペナルティ-3.0)/contact_symmetry/action_jerk報酬 + pose_prior 0.3→0.8で平地再学習(v2/v2b, 計~2800iter)。
- **成果**: hip/knee 関節がほぼ対称(33/33, 29/24度)、支持相 0.63/0.37=人間的、anti-phase 0.13→(v2)0.59/(v2b)0.33、目視で自然な直立歩行(腕振り・脚交互・破綻なし)。
- **残課題**: 足クリアランスが左右非対称のまま(片足~4cm/片足~25cm)で優位脚が run毎に左右入替。=**方策は対称化できても歩容リミットサイクルが自発的に片側へ崩れる**(既知の難問)。foot_clearanceの「目標(10cm)からの偏差」ペナルティでは足高の左右差を直接縛れていない。survivalは0.99→0.72に低下(自然性制約のトレードオフ)。
- 次の直接手(未実装): ①|foot_clearance_L - foot_clearance_R| を直接ペナルティ ②位相ロック対称クリアランス(左足φ=右足φ+0.5) ③rsl_rl use_mirror_loss。
- ckpt: `known_good/walk_rsl_symmetric_20260725_hipknee_sym.pt`。bd `7c9a`。

### [自然歩容・根本原因] 参照モーション自体が非対称だった (2026-07-25)

- v1-v3 で対称性augmentation+多数の報酬を投入しても足上げ左右差が残った真因: **参照モーション `walk.json`(100STYLE Neutral_FW由来)自体が左右非対称**。hip_L 23.0度 vs hip_R 18.6度、ankle_L 30.6 vs ankle_R 22.5度、`|L(t)-R(t+T/2)|`=hip5.3/ankle8.6度(0が完全対称)。人間mocapは本来左右非対称。
- `pose_prior`(重み0.8)がこの非対称参照を模倣する一方、私の対称性報酬(gait_symmetry/foot_lift_symmetry等)がそれを打ち消そうとする**綱引き**になっていた。だから4回再学習しても足上げが均等化しなかった。
- **修正**: 参照を対称化。canonical=0.5*(L(t)+R(t+T/2))、L(t)=canonical、R(t)=canonical(t+T/2)。矢状面関節は左右で符号反転しないので純粋な半周期シフト。`walk_sym.json` 生成、sym残差0.000度・L/R振幅完全一致(hip18.7/18.7, knee26.6/26.6, ankle26.0/26.0)。
- v4: walk_sym.json + --symmetry + 全対称性報酬 + pose_prior0.8 で再学習。参照とペナルティが同方向を向くので綱引き解消。
- 教訓: 模倣学習で「自然/対称」を求めるなら**参照モーション自体の性質を先に検証**する。人間mocapは対称ではない。
- 追加報酬 `foot_lift_symmetry`(EMA足上げ高さの|L-R|直接ペナルティ, -8.0): v3で25→16cmに改善(commit 402115208b)。参照対称化と併用。

### [階段0.10mフル昇段] 検証成立(中程度の頑健性) (2026-07-25)

- 0.07m中間から転移した stairs_h10b(段高0.10m=フル)。verify(フレッシュ再ロード16s): survival @0.10=0.662/@0.13=0.703/@0.16=0.707、travel 1.80-1.92m(速度で変動)、**height_gained 0.48-0.53m=約5段登坂**(0.10m段)。目視: 上体直立で0.10m段を制御登坂・腕連結・崩れなし。0.05m(survival0.9)より頑健性は落ちるが、フル段高で確実に登る。
- カリキュラム 0.05→0.07→0.10 の段階転移が有効(0.05→0.10直行は1段停止で失敗していた)。
- VERIFIED ckpt: known_good/walk_rsl_stairs_h10_20260725_survival0.7_VERIFIED.pt。
