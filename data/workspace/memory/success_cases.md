# 成功事例集 (Success Cases) — ローカルLLM参照用

目的: 高難度問題の解決過程を「再利用できる形」で残す。全エージェントは成功時にここへ追記する。
指南書: `docs/LOCAL_LLM_CODING_PLAYBOOK.md` / 失敗集: `trouble_history.md`

**追記の型 (1事例=1節、この5項目を必ず)**
```
## [S###] タイトル (日付, 担当)
- 問題: 何が起きていたか (症状)
- 診断: どうやって根本原因に到達したか (見た実物・使った数値)
- 解決: 何をどう変えたか (最小変更で)
- 証拠: 成功をどう確認したか (実測値)
- 再利用: 次に同種問題が来たらどうするか (1-2行)
```

---

## [S020] Dynabook Moldflow synmesh を正規 COM ルートで起動し Completed (2026-07-26)
- 問題: `MeshNow(False)` は error 0 でも `synmesh.exe` が立たず Pending のまま。GUI は遅く、開始成功と遅延が区別しづらい。Design Link 不在で STL 新規メッシュも不可。
- 診断: 成功時の親プロセスは必ず `amijm.exe`。失敗例はシード無し/Failed Midplane。正規経路は Session1 Synergy + 64bit `cscript` `/IT` + `CreateObject` + `OpenItemByName` + `MeshGenerator` + `MeshNow`。
- 解決: 既存の別ジョブ synmesh を停止後、同ルートで `mf_fc_strip_out_study (copy)` に MeshNow。シード sample nodes/tris>=20 を確認してから実行。
- 証拠: synmesh CMD `-output mf_fc_strip_out_study~4Mesh mf_fc_strip_out_study_(copy).udm`；`MESH_STATUS_FINAL=Completed` / SUCCESS（`agent_mesh_start.log`）。正典 `docs/knowledge/dynabook_moldflow_synmesh_canonical_route_20260726.md`。bd key `moldflow-synmesh-canonical-route`。T076 / S020。
- 再利用: IF Dynabook でメッシュ THEN 正規ルート以外を発明しない。IF MeshNow=0 でも synmesh 不在 THEN 未成功。IF GUI が遅くても synmesh が対象 UDM で生きていれば開始成功とみなして待つ。

## [S019] Lavie 樹脂充填 snappyHexMesh 経路を実績ケースのテンプレート化で成立させた (2026-07-25)
- 問題: `openfoam_lavie` トラックが8連続 ERROR で meaning gate 停止。修正しても症状が
  `mesh_mode 未対応` → `pyvista が STEP を読めない` → `STL の中に CARTESIAN_POINT が無い` と
  次々に別のエラーへ移り、最後は `returncode 0` なのに充填29%で FAILED になった。
- 診断: Lavie の**実行主体**が `C:\lavie_usb_pack`（K10と別コピー・11日前）だと突き止め、
  以後は「リポジトリのファイル」ではなく「実行ファイルのハッシュ」で検証した。ジオメトリは
  `forbid_plate_geometry=True` なのに `pp_plate` へ暗黙代替されていた。同梱STLは552三角形・
  非多様体・21.40cm3 で、KPI が使う `cavity_volume_m3`(41.33cm3) の半分だった。決定打は
  **`snappyhexmesh` 分岐に成功実行の記録が1件も無い**ことで、mm前提と bbox中心の
  `locationInMesh`（=中空内部で、樹脂が流れる2mm肉厚ではない）が未検証のまま残っていた。
  最後の29%は `_inject_parameters_openfoam` が `pack_end_time`(0.32s) で controlDict の
  `endTime` を上書きし `analysis_end_time_s`(1.24s) を見ないためで、solver は正常終了に見える。
- 解決: 定数を推測し直すのをやめ、実績ケース `moldflow-union-xplus-d2-mfalign-v3-20260723` の
  dict 21個を Lavie から回収して
  `data/cae_te_workspace/experiments/openfoam/mfalign_snappy_v001` にテンプレート化し、
  `build_mfalign_snappy_case` で実体化する方式へ置換。併せて (a) 制約フラグ下の代替は raise、
  (b) `stl_bbox_mm`/`geometry_bbox_mm` で binary/ASCII STL を判別、(c) snappy への STEP は明示 raise、
  (d) `_openfoam_mesh_steps` に `surfaceFeatureExtract→blockMesh→snappyHexMesh -overwrite→topoSet→createPatch -overwrite`、
  (e) 実績 STL を正規サンプルへ昇格、(f) 充填ホライズンを `pack_end_time` にも設定。
- 証拠: `repro-mfalign-v3b-20260725` が SUCCESS / `RESULT: PASS`。fill 99.48%、fill_time 0.90s
  （実績帯 0.808-1.347s 内）、`fill_complete=true`、最終 Phase-1 volume fraction 0.995763、
  `End` @ Time 1.24006、2630s、checkMesh 非直交 Max 36.2/Avg 2.57。実績 alpha 0.9963 に対しては
  -0.05pp なので「等価」とは言わない。INC-161 / T073 / bd `Clawdbot_Docker_20260125-6t03`。
- 再利用: IF あるコード経路に成功実行の記録が無い THEN その定数は未検証として扱い、実績成果物を
  逐語コピーしてテンプレート化する（生成ロジックを書き直さない）。IF リモートで直したのに
  症状が変わらない THEN 実行主体のパスとハッシュを先に確認する。IF solver が `returncode 0` で
  KPI だけ足りない THEN 打ち切り時刻（endTime の上書き）を疑う。

## [S018] OpenRadioss 4mm ASSYを物理窓で正しくSUCCESS判定 (2026-07-25)
- 問題: 4mm x 4mm打抜き解析がNORMAL TERMINATIONしても、警告文字列・破断後ERR・FAILURE START数の誤解釈で恒久FAILEDになった。
- 診断: 新規K10実行を70,000 cycleまで監視。実エラー0、破断開始0.49868ms、破断前ERR=-0.7%、最終DM/M=8.856%、実削除要素0、VTK 3個を確認し、判定器の4つの偽陽性を生ログと分離した。
- 解決: velocity/time-stepを行スコープ化し、cycle-tableを解析し、最初の破断時刻の99%以前でERRを評価し、FAILURE STARTと実削除要素を分離。ワーカーはbusy時に即409を返す。
- 証拠: `k10-press_blanking_assy-4mmx4mm-20260725-1221` はNORMAL_TSTOP、t_final=0.560ms、PART_ID=1形状KPI抽出、修正版ゲートSUCCESS。回帰テスト5/5 PASS。INC-160 / T072 / bd `Clawdbot_Docker_20260125-de46`。
- 再利用: IF 切断解析で破断後ERRが急落する THEN 最初の破断より前の安定窓を評価する。IF FAILURE STARTが多い THEN 実削除要素数と混同せず、材料破断開始として別KPIにする。

## [S017] Moldflow COM 429 の真因はGUIモーダル — セッション1のウィンドウ状態で特定 (2026-07-25)
- 問題: Dynabook の Moldflow MCP ブリッジ(0.8.5)は正常起動し28ツールが応答するのに、アクティブstudy系が全て `CREATEOBJECT_FAILED:429`。`probe_com` は30秒×2回タイムアウト後、約150秒でようやく成功し `Version : (unavailable)`。
- 診断: 先行知見(INC-151/152)のビット数・セッション不一致仮説を先に潰した（0.8.5は該当ツールを全て `bitness=64` で実行、MCPもSynergyも SessionId=1）。SSHはセッション0でウィンドウ列挙できないため `schtasks /IT` でセッション1に入り込み、`EnumWindows`+`IsWindowEnabled` とスクリーンショットを取得。メインウィンドウ `enabled=False`、`Internet Explorer_TridentDlgFrame` の「スクリプト エラー」が可視。閉じるとハンドルが `3805930`→`1644694` に変化し、再生成ループと確定。
- 解決: GUI操作での解除を断念し、`schtasks /IT` で Synergy を強制再起動（新PID 3884）→ 同セッションでブリッジ再起動。`.cursor/mcp.json` に `dynabook-moldflow` → `http://100.98.133.40:8765/mcp` を登録（ブリッジの `MOLDFLOW_MCP_HOST=100.98.133.40` によりHost検証を通過）。
- 証拠: `probe_com` 32/64bit 両方成功・`Version : 2010`、`inspect_state` `ok:true`/`metric_units_ok:true`、読み取り一式 117秒→36秒。画像 `docs/evidence/inc159/synergy_blocked_script_error_20260725.png`(異常) と `docs/evidence/inc159/synergy_recovered_20260725.png`(復旧)。INC-159 / T071 / bd `Clawdbot_Docker_20260125-v7di`。
- 追加判明(同日): 48時間で `synergy.exe` が41回クラッシュ（全件 `MFC80U.DLL` 8.0.50727.6229 / `0xc0000005` / offset `0x6c372`）。クラッシュPIDはGUIのPID 6688と別＝`CreateObject` が起動した短命COMサーバ。GUIが固まる→COM要求ごとに新インスタンス→即クラッシュ→429、が真の連鎖。復旧後クラッシュゼロ。
- 再利用: IF Moldflow COM が429 THEN 先にセッション1で `IsWindowEnabled` を見る（COM再登録やビット数変更に進まない）。**429でCreateObjectをリトライしない**（落ちるインスタンスが増えるだけ）。IF 閉じた後にダイアログのハンドルが変わる THEN 再試行せずアプリ再起動。**`SendMessage(SC_CLOSE)` と `SendKeys` は固まったモーダルに対して無限ブロックするので使用禁止、`PostMessage` のみ**。対話タスクの待ちは120秒以上を見込む。

## [S016] OF box-shell Telegram VOF = STL surface + iso only (2026-07-22)
- 問題: Telegram 充填アニメが平板に見え、ユーザーが繰り返し却下。bbox は 100x60x50 なのに意味が伝わらない。
- 診断: (1) 壁面 `alpha` 塗り / `threshold(alpha)` は薄肉シェルを「薄い板」に見せる (2) side/front/top 正対カメラは奥行きを潰す (3) 送信前にフレーム目視していなかった。
- 解決: `Moldflow.stl` 表面に `alpha.polymer` を sample して着色。カメラは iso（高さが分かる視点）のみ。t=0 静止画を先に送る。side/front/top・壁面塗り・体積閾値 GIF は送らない。
- 証拠: ユーザーが REFERENCE still + `CORRECTED ... camera=iso` を OK。ローカル `data/workspace/moldflow_bridge/of_vof_anim_stl_20260722/`。bd key `of-vof-telegram-box-shell-stl-fill`。
- 再利用: IF 箱シェル VOF を Telegram する THEN STL表面着色 + iso + 送信前フレーム目視。IF 平板に見える THEN カメラ/描画モードを疑い、メタデータだけで箱と断言しない。K10自動配信の OpenFOAM ParaView Telegram は無効（`CAE_OPENFOAM_PARAVIEW_TELEGRAM` 既定0）。原因はカメラではなく `blockmesh_bbox` の別STEPが多い。

## [S012] No4 Fast Fill + Cool (circuits) SUCCESS; Warp HARD_BLOCKED 200052 (2026-07-20)
- 問題: AnalysisSequence の Fast Fill / Cool / Warp 段を自動化し、Fill+Pack(`Flow`) 以降を SUCCESS 証拠付きで閉じる必要があった。
- 診断: COM 受理は Fill/Fast Fill/Flow/Cool のみ。strip に冷却回路ゼロ。`model_4_cooling.sdy` はチャンネル0で Fill 起動。`runstudy` は cwd=親必須。`warp.exe` は Flow `.op2` があっても ERROR 200052（interface 未設定）。
- 解決: Fast Fill は SaveAs+COM+MCP runstudy。Cool は tutorial `cpu_base` をコピーし `cool.exe`（124 circuits）。Warp は当時 GUI 必要と誤判断（後続 S013 で CLI `-interface` で解消）。
- 証拠: Fast Fill `mf_fc_fastfill_20260720_120214~2.*` (~105s)。Cool `mf_cool_cpubase_20260720_123230.oc1/.c2p` cycle 24.7s。正典 `docs/knowledge/moldflow_analysis_sequence_probe_20260720.md`。MCP 0.8.4。
- 再利用: IF Fast Fill THEN COM `Fast Fill`+runstudy cwd=parent。IF Cool tutorial THEN cpu_base+`cool.exe`。Warp は S013 参照。

## [S015] MF vs OF scorecard + v2 rheology/U calibration (2026-07-21)

- 症状: 同一箱型φ2でも OF が MF Fill に近づかない / 比較不能
- 解決: 粗メッシュ2.5万で充填到達(v1 α≈99.9%@0.80s)。scorecard で fill_time -25% を検知し U=10.55 + powerLaw n=0.275 + rho=900 の v2 を投入
- 根拠: `docs/knowledge/mf_of_compare_improve_box_phi2_20260721.md` / `mf_of_scorecard_box_phi2_20260720.json`
- 再利用: IF velocity-BC で OF fill_time が MF より速い THEN U*=(t_of/t_mf)。圧力不足は粘度(powerLaw/Cross)を上げる。等価主張禁止
- 未解決: v2 完了後の圧力KPI・熱連成

## [S014] MF→OF handoff for box φ2 gate (PROXY_GAP) (2026-07-20)

- 症状: 同一STL・φ2ゲートなのに Lavie OpenFOAM が Moldflow Fill に近づかない / 比較不能
- 解決: Dynabook Fill KPI（fill_time=1.077s, V, gate area）から U≈14.21 m/s・endTime≈1.24s・maxGlobalCells=150k の handoff を生成し engine/tri-track に接続
- 根拠: `docs/knowledge/mf_vs_of_box_phi2_comparison_20260720.md` / `mf_to_of_handoff_box_xplus_d2_20260720.json`
- 再利用: IF MF fill_time + cavity volume + gate area known THEN `scripts/mf_to_of_handoff.py` → `apply_mf_to_of_handoff` / tri-track overwrite。SUCCESS は fill_complete 必須。等価主張禁止 (PROXY_*)
- 未解決: Lavie 再実行（IP不通）・圧力合わせ用 Cross-WLF は次段

## [S013] Strip Cool + Warp CLI -interface SUCCESS (No4 xu6i, 2026-07-20)
- 問題: strip Cool が 0ch HARD_BLOCK、Warp が ERROR 200052 で No4 が閉じられない。
- 診断: CreateBeamsByPoints 単独だと inlet がパート節点/中間節点に乗り 701870。CreateNDBC は EntList 渡しが正。`warp.exe -help` に `-interface filePrefix` があり、200052 は GUI 必須ではなくフラグ欠落。
- 解決: `Modeler.CreateNodeByXYZ` → Channel 40480 beams → `CreateNDBC(EntList,40020)` → `cool.exe`。Warp は Flow の `~N.op2` を `-interface <prefix>` で指定。
- 証拠: Cool `mf_strip_cool_v12_20260720.oc1/.c2p` (8 circuits, cycle 35s)。Warp `mf_fc_warp_v2_20260720~W.ow3` (180KB) + `~W.lsp` (1MB); 3 study 再現。`STRIP_COOL_SUCCESS_20260720.md` / `WARP_SUCCESS_INTERFACE_CLI_20260720.md`。
- 再利用: IF strip Cool THEN CreateNodeByXYZ+40480+CreateNDBC(EntList)+cool.exe cwd=parent。IF Warp after Flow THEN `warp.exe -mes raw -output <base>~W -interface <flow>~N <sdy>` cwd=parent。COM Warp 文字列は引き続き不可。

## [S011] Face-center gate Fill COMPLETED + progressive PNG Telegram (2026-07-20)
- 問題: 角ゲート N2 のままではユーザー要求の +X 面中央ゲートとならない。Fill 完了後も Telegram へ初期/中期/最終の充填進行 PNG が届かず、ExportImage や SetMaxValue では失敗または同一画像になる。
- 診断: MF2010 では旧 NDBC 削除が不安定→UDM strip で GATE_COUNT=0 にしてから N1154 を打つと gate_count=1。Fill plot は GUI 読込後 GetMaxValue>0 が必要。ExportImage=438。SaveAnimation GIF 24f + Pillow 10/50/100% が唯一の進行差分経路。MCP/Synergy は session 1 (`schtasks /IT`)。
- 解決: study `mf_fc_strip_out_study_(copy).sdy` に N1154 @(50.0,2.09,27.70); Fill COMPLETED; bridge 0.8.3 の `moldflow_export_fill_stages` + host `moldflow_fill_png_telegram.py` / runner `--stage fill_png_telegram`。
- 証拠: GATE_COUNT=1; STATUS_CODE=1 elapsed 141.16s fill_frac~1.077; Telegram message_id 16781/16782/16783; evidence `runner_results/20260720_082610/stage_fill_png_telegram.json`。正典: `docs/knowledge/dynabook_moldflow_end_to_end_runbook_20260720.md`。
- 再利用: IF 面中央ゲート THEN UDM strip→N1154 (gate_count=1)。IF 進行 PNG THEN SaveAnimation→Pillow→sendPhoto (ExportImage禁止)。IF COM THEN `/IT` session1 + MCP>=0.8.3。詳細 bd remember `dynabook-moldflow-facecenter-fill-png-20260720`。

## [S010] Moldflow configure on SaveAs copy + MachineFinder IT fail-closed (2026-07-20)
- 問題: bridge 配線後も study copy への `material_id=1007` configure 実証と MachineFinder の interactive 再probe、UI用 label-join が残っていた。
- 診断: フォルダ xcopy コピーは mesh/node 喪失で N2 欠落。MachineFinder は `schtasks /IT` でも err=424 (Object required)。`select_machine` は COM ハングし得る。
- 解決: 同一 project で SaveAs コピー→lean Select+Save VBS を `/IT` 実行。MachineFinder は fail-closed で process-condition + `*.30007.udb` 目録に固定。CAE Studio `_join_synergy_materials_to_file_catalog` + `/api/material-label-join`。configure は label scan 上限と skip_gate 時 Save 継続。
- 証拠: `configure_min.log` に Selected material ID 1007 / SAVE_OK=True; `probe_machine_IT.log` に MachineFinder_err=424 + FALLBACK; catalog total=13; unit tests 5 PASS; copy=`...gatefill_matcfg_20260720.sdy`。
- 再利用: IF configure 試験 THEN SaveAs copy (同 project)。IF MachineFinder 424/timeout THEN 機種COMを諦め process params。IF UI表示 THEN label-join のみ (catalog≠property DB)。

## [S009] Moldflow material/machine bridge wired on Dynabook MCP (2026-07-19)
- 問題: 材料/成形機は SQLite UDB 目録のみで、解析は Synergy 内蔵 DB。ジョブから材料 id 選択と機種経路が未配線だった。
- 診断: Fill SUCCESS 実績は domain 21000 + FieldDescription + material id 1007。`*.30007.udb` は 26(K10 SQLite)/13(Dynabook install) のファイル目録。MachineFinder COM は probe が timeout=COM弱。
- 解決: MCP 0.7.0 で `configure_study(material_id|mfg+trade + process params)`、`list_machine_catalog`、`probe_machine_com`、`select_machine`(fail-closed)。CAE Studio `/api/machine-inventory`。runner/docs。
- 証拠: Dynabook `bridge_version=0.7.0` tools=23; catalog ok total=13; unit test 4 PASS; probe timeout→process-condition fallback 確定。
- 再利用: IF Fill 材料指定 THEN Synergy domain 21000 + material_id 優先。IF 機種 COM timeout THEN UDB 目録+clamp/pressure プロセス条件。UDB を物性DBと言わない。

## [S001] Moldflow充填が「板のまま」→3層の根本原因を実物検証で特定 (2026-07-15, Fable5)
- 問題: カスタムSTLの充填動画依頼後もTelegramには100x60x2板の動画のみ。
- 診断: ①run_dirの時系列ディレクトリ有無→ソルバー未実行と確定 ②ログのdeltaT数列→1e-16に崩壊=発散 ③checkMeshでメッシュ体積318cm³ vs 部品体積42cm³→「部品の外側」を解いていたと数値で確定。保持点(0,0,0.025)が中空部だった。
- 解決: locationInMeshを肉厚2mm内部(-0.049,0,0.025)へ(STLをレイキャスティングで解析して算出)。ゲート/ベントはtopoSet cylinderToFace+patchToFace subsetで部品表面に生成。Courant上限20→1.0/0.5。
- 証拠: checkMesh品質OK・alpha有界[0,1]・実CFD動画がTelegram到達。
- 再利用: 「充填がおかしい」→ まずメッシュ体積÷部品体積を計算。>1.5なら外部流。保持点は必ず肉の内部。詳細: trouble_history [T064]。

## [S002] batダブルクリックが無言で不発 → 原因は改行コードLF (2026-07-15, Fable5)
- 問題: Explorerから.batを起動してもログが書かれず、コンソールも残らない。
- 診断: 同フォルダの別batは動く→内容差分ではなく生成方法の差。AIツールのファイル書き込みはLF改行 → cmd.exeはCRLF前提。
- 解決: `sed 's/$/\r/'` でCRLF化+ASCII化したbatを再生成 → 即起動。
- 証拠: 同一内容のCRLF版が一発で動作 (solder_demo.log 18:17 start)。
- 再利用: AIが生成するbatは必ずCRLF。日本語echoは避ける(CP932文字化け)。失敗時にconsoleが残るよう `pause` を必ず入れる。

## [S003] 半田データセット判定が全件同一スコア → エンジン選定で解決 (2026-07-15, Fable5)
- 問題: solder-joint-dataset評価で全18枚がscore 1.0000=識別力ゼロ。
- 診断: ①normalが6枚しか読めていない→拡張子.tiff未対応(find実物確認) ②修正後も全件1.0→参照差分方式は切り出しサイズ不揃い画像に原理的に無力(T050の実測と一致)。
- 解決: ①tiff対応のローカルimgs_in追加(共有関数は不変更) ②NTFS大小文字非区別の重複をsetで排除 ③エンジンをPatchCoreへ。
- 証拠: 正常2枚(2.76/3.25) vs 不良16枚(3.26-4.06)=全不良が全正常より高スコア(順位分離100%)。
- 再利用: 新データセットはまず拡張子・枚数・サイズ分布を実測。切り出し画像→PatchCore。閾値は全数評価で決める。

## [S004] DoEエンジンを実解析に接続 (モック排除パターン) (2026-07-15, Fable5)
- 問題: D/I最適計画がモックKPI上で動いており"最適解"が式に埋め込まれた答えだった(T063)。
- 解決: scripts/moldflow_doe_real_trials.py — 計画点→cae_te_remote_trial.py実試行→KPIスクリプトの実測値でRSM更新。連続3失敗で停止する意味ゲート+state.json再開+通知なし(summary.mdのみ)。
- 証拠: D/I計画生成→RSM適合→最適点探索の全経路をテスト済(設計10点×2変数)。
- 再利用: 最適化ループを作る時はこのファイルを雛形にする。KPIは必ず解析出力ファイル由来。

## [S005] 既存WebUIへの機能追加はクライアント側集計で無停止反映 (2026-07-15, Fable5)
- 問題: 外観検査AIにタグ検索・判定事例ページを追加したいがAPI再起動はリスク。
- 解決: /api/samplesの既存データをapp.js側で集計(タグ導出・グループ化)する設計にし、サーバ変更ゼロ。record_sampleには後方互換のtags引数のみ追加。
- 証拠: ブラウザ再読込のみで2タブ稼働。既存タブ・API無変更。
- 再利用: 表示系の追加はまずクライアント側集計で実現できないか検討。サーバ変更は最終手段。

## [S006] Moldflow 2010の既存ゲートをMCPで非破壊確認 (2026-07-16, Codex)
- 問題: メッシュはMCPで確認できたが、Synergy上で設定済みの射出ゲートをMoldflow 2010 COMから直接読めなかった。
- 診断: Autodeskの採用解でNDBCの直接getterが存在せず、一時UDMを読む必要があると判明。配置後も旧PIDが応答していたため、ファイル更新と実行中バージョンを分離して検証した。
- 解決: 読取専用UDM export、NDBC型40000/40002/40003抽出、ノード座標照合、一時UDM削除を既存MCP inspectorへ追加した。
- 証拠: 実機MCPがgate_count=1、node_id=2、座標(-50.0000007451, 2.7391463518, 23.8075219095)、cleanup_error=0、analysis_started=falseを返した。
- 再利用: IF Moldflow 2010の既存射出位置を読む THEN UDM/NDBCを解析 BECAUSE 公式APIに直接getterがない。配布後はhashとlive responseを確認する。

## [S007] Moldflow 2010のコピー限定AutoFixをMCP実行 (2026-07-16, Codex)
- 問題: メッシュ診断APIが150～180秒で停止し、GUI修復しかできないように見えた。
- 診断: 実機`synapi.chm`から`MeshEditor.AutoFix()`と`DuplicateStudyByName2()`を発見。初回は表示名とSDY名の記号差で安全停止した。
- 解決: Study名を英数字だけに正規化し、既存`copy 2`を再利用するコピー限定ツールを実装した。
- 証拠: AutoFixが580件除去、Save=True、analysis_started=false。元StudyへAutoFixは実行していない。
- 再利用: IF Moldflow書込み操作 THEN 元Studyを複製しcanonical name一致後のみ実行。表示名とSDYファイル名を直接比較しない。

## [S008] Dynabook Moldflow 2010のFusionメッシュをMCPから開始 (2026-07-17, Codex)
- 問題: VPN、8765/8766混在、Python環境、bind policy、COM bitness、通常GUIとAutomationの競合により、MCPからメッシュ生成へ到達できなかった。
- 診断: 各層を独立検証し、Synergy COMが64-bit registry viewのみ、MCPは専用venv必須、`MeshNow(False)`は非同期であることを実機値から確定した。
- 解決: copy名一致・write gate・64-bit cscript・3回限定COM retryを持つ `moldflow_mesh_active_study_copy` と明示node限定の `moldflow_set_gate_active_study_copy` を実装・配備した。
- 証拠: 7 tests PASS、remote SHA一致、live MCP tool list確認、Version 2010/active project/study確認、3.0 mm mesh start error 0、UI進捗30%、analysis false。
- 再利用: IF Moldflow 2010 MCP書込み THEN VPN/service/interpreter/bind/COM/session/study identityを順にゲートし、`Running`を成功途中状態としてpollする。完了前に再実行しない。
# Dynabook Moldflow MCP AutoFix execution with fail-closed quality gate (2026-07-19)

1. **Problem**: automate Moldflow 2010 mesh repair while preserving the original study.
2. **Key action**: use 64-bit COM in the visible Windows session, SaveAs a copy, run `MeshEditor.AutoFix()`, save, and quantitatively reinspect.
3. **Result**: AutoFix removed 174 elements; intersections 1201->1052 and overlaps 595->529. Mesh still failed, so gate and analysis were correctly blocked.
4. **Reusable rule**: never export the model while mesh status is Pending/Running, and never accept AutoFix from its removed-count alone.
5. **Evidence**: `docs/knowledge/dynabook_moldflow_mcp_mesh_autofix_20260719.md`, INC-152, Beads `Clawdbot_Docker_20260125-h8dx`.

## [S017] Steam向けElectronゲームを安全な段階ゲートで完成 (2026-07-24, Codex)
- 問題: 2つの入力ZIPはPhaser試作とUnityタイトル部品だけで、Steam提出可能な完成ゲームではなかった。初回npm取得、依存監査、Electron起動、ホストメモリでも個別障害が発生した。
- 診断: npm registry PONG 15.897秒、監査10件、`ELECTRON_RUN_AS_NODE=1`、`vmmemWSL`約9.5GBと各原因を事実で分離した。ゲームロジック不良とホスト/ツールチェーン不良を混在させなかった。
- 解決: 新規 `games/bunny-colony/` に限定し、Electron 43.2.0 + Canvasで7日制コロニー戦略ゲームを実装。依存を更新し、子プロセスだけ環境変数を除去し、Docker停止後に専用SVGアイコン付きPortable EXEを1回再生成した。
- 証拠: ルールテスト5/5、npm audit 0、unpacked/portableの応答ウィンドウ確認、89,602,232 bytes、SHA-256 `AA7305AA52F1DE1F599FECAC098F6DFA3B6A83913255185085CD5935006482CD`。INC-153～156、Beads `Clawdbot_Docker_20260125-6emb`。
- 再利用: IF Electron配布を作る THEN 依存取得を監視し、完全監査、`ELECTRON_RUN_AS_NODE`、空きcommit memory、GUI応答、正確なプロセス清掃、SHA-256の順にゲートする。BECAUSE ビルド成功だけでは配布可能性を証明できない。

## [S019] 融合AIメッシュを商用スタイライズキャラクターへ再構築 (2026-07-26, Codex)

- **問題:** 2D由来の単一AIメッシュで腕とスカートが同一面になり、ウェイト補正ではポーズ時の伸長・裂けを解消できなかった。
- **診断:** v16のレスト／ポーズ比較で変形のみの破綻を確定。v20では橋渡し面1,067枚の削除が腰欠損を生み、局所修正の限界を確認した。
- **解決:** 顔・髪・眼・上着・スカート・腕・手・脚・靴を閉じた独立部品として再構築し、8 PBR材質、19ボーン／19頂点グループへ結合した。
- **証拠:** v23は21,452三角形、元メッシュとFBX再読込で境界0・非多様体0。GLB/FBX独立再読込で `PASS_COMMERCIAL_STYLIZED`。
- **再利用:** IF生成メッシュで衣装と関節部が同一トポロジーに融合している AND ウェイト境界で三角形が伸びる THEN 局所ウェイト修正を打ち切り、閉じた独立部品へ再構築する。BECAUSE 接着面のまま異なるボーン変形を与える限り破綻は再発する。

## [S020] Mixamo異骨格アニメを開始フレーム差分で安全に移植 (2026-07-26, Codex)

- **問題:** Mixamo 65ボーンの絶対ポーズをv23の19ボーンへ移すと、親変形が重複し腕前方・脚交差が発生した。
- **診断:** アーマチュア空間`pose.matrix`には親変形とTポーズ固定オフセットが含まれていた。
- **解決:** `matrix_basis`の開始フレームからの局所回転差を、両骨格のレスト軸間で変換してベイク。元リグ・メッシュ・アクションを出力前に削除。
- **証拠:** Idle 251、Walking 42、Talking 151フレーム。GLB/FBX再読込で3アクション・19ボーン・8材質、`PASS_MIXAMO3_RETARGET`。
- **再利用:** IF異なるレスト姿勢間でリターゲットする THEN 最初のアニメーションフレームを基準に局所回転差だけを移す。BECAUSE 絶対ポーズは親回転とソース骨格固有の初期姿勢を重複適用する。
## [S021] Resumed and verified a 4 GB Unity installer safely (2026-07-26, Codex)

- **Problem:** The D-drive download was partial and a retry could outlive the
  outer harness timeout.
- **Diagnosis:** F: had about 1.63 TB free; HTTP Range continuation produced
  measurable growth. The timeout defect was a 35-second attempt plus one retry.
- **Solution:** Preserve the original, copy the partial to F:, run 25-second curl
  chunks with retry disabled, persist progress, and stop after three no-growth
  chunks.
- **Evidence:** Final size 4,031,619,680 bytes; zero no-growth chunks;
  Authenticode `Valid`; signer `Unity Technologies SF`; state
  `verified_complete`.
- **Reuse:** IF downloading a large signed installer, THEN separate the resumable
  worker from its observer and require exact size plus vendor signature before
  execution.
## [S022] Installed Unity side-by-side through an explicit UAC gate (2026-07-26, Codex)

- **Problem:** Silent Unity installation was cancelled at Windows UAC and left a
  stale `installing` status.
- **Diagnosis:** `/S` suppresses installer UI but cannot bypass elevation;
  `consent.exe` and the localized Start-Process exception proved cancellation.
- **Solution:** Catch launch failure, keep the target-exists gate, notify the
  user, and retry only after explicit UAC approval with `/D` as the final
  argument.
- **Evidence:** Exit code 0; Unity product version
  `6000.0.73f1_a166abc3bf0e`; Authenticode `Valid`; signer
  `Unity Technologies SF`; existing C-drive metadata preserved.
- **Reuse:** IF a silent Windows installer requires elevation, THEN treat UAC as
  an explicit human gate and never equate `/S` with authorization.
## [S023] Unity Humanoid import passed a warning-zero commercial gate (2026-07-27, Codex)

- **Problem:** Automatic Humanoid mapping discarded animated spine, neck, and
  shoulder rotations; loop settings remained absent; an initial validator used
  unavailable ModelImporter APIs.
- **Diagnosis:** FBX meta showed Chest mapped as human Spine, intermediate bones
  unmapped, translation DOF off, custom clips empty, and retarget warnings.
  Unity documentation requires first-import clips to be populated in
  OnPreprocessAnimation.
- **Solution:** Configure clips in OnPreprocessAnimation; explicitly map 19
  Humanoid bones; enable translation DOF; force synchronous FBX reimport; use
  public Unity APIs plus a separate serialized-meta warning gate.
- **Evidence:** Unity exit 0; Avatar Human/Valid; 3 clips with correct loops;
  warning/error fields empty; 19 mappings; Animator states and prefab components
  valid; final validation PASS.
- **Reuse:** IF a postprocessor changes existing model import behavior, THEN
  force reimport and verify both Unity runtime objects and serialized meta,
  BECAUSE recompiling the postprocessor alone does not update an existing FBX.

## [S024] Unity EditMode Humanoid motion was proven by deterministic clip sampling (2026-07-27, Codex)

- **Problem:** Animator state routing reached Walking, but `Animator.Update()` in
  EditMode did not produce a reliable LeftFoot pose delta.
- **Diagnosis:** The clip, valid Humanoid Avatar, mapping, and controller state
  all passed independently; only the EditMode measurement path failed.
- **Solution:** Keep state-transition checks, then use
  `AnimationMode.SampleAnimationClip` at 0.00 and 0.45 seconds with cleanup in
  `try/finally`.
- **Evidence:** Unity exit 0; Idle > Walking > Talking > Idle; LeftFoot rotation
  delta 34.5734 degrees and position delta 0.379801 m; Build Settings unchanged.
- **Reuse:** IF an EditMode Humanoid gate must prove motion, THEN test controller
  routing and deterministic pose sampling separately, BECAUSE state advancement
  alone does not prove animation-curve application.

## [S025] Unity commercial heroine passed a packaged Player gate before game integration (2026-07-27, Codex)

- **Problem:** Editor validation did not cover coroutine compilation, Player
  linker dependencies, or headless Humanoid pose updates.
- **Diagnosis:** CS1626 identified invalid iterator structure; UnityLinker proved
  NUnit leaked from tests; a real Player proved state routing but zero pose under
  Null graphics culling.
- **Solution:** Use explicit coroutine gates, separate runtime and Editor-test
  asmdefs, and set `AlwaysAnimate` only in the isolated smoke scene.
- **Evidence:** Build warnings/errors 0/0; Player exit 0; sequence
  Idle>Walking>Talking>Idle; LeftFoot 10.3514 degrees / 0.510514 m; EditMode
  tests 4/4; production scene integration PASS with Build Settings unchanged.
- **Reuse:** IF a Unity character is Player-ready, THEN require a packaged
  Player JSON+exit-code+bone-motion gate before production-scene integration.

## [S026] Tokimeki production UI and fallback lip sync passed a real-screen Player gate (2026-07-27, Codex)

- **Problem:** The commercial heroine had no BlendShapes or Jaw bone, while
  hidden/batch-mode capture returned a black image and early layouts contained
  camera, mouth-scale, overlap, and ground-edge defects.
- **Diagnosis:** Unity API measured one skinned renderer, zero BlendShapes,
  Head present and Jaw absent. Successive real images separated capture,
  transform-space, camera-bounds, and UI-layout failures.
- **Solution:** Integrated dialogue and five schedule actions into production
  UGUI; added an explicitly labelled world-space Head-following procedural mouth;
  isolated the render runner in a separate scene; captured a visible Player.
- **Evidence:** Build warnings/errors 0/0, EditMode 4/4, Player exit 0,
  interactions 2, Study selected, lip peak 0.9817447, and a visually approved
  113,191-byte PNG. Production Build Settings stayed empty.
- **Reuse:** IF a character lacks facial deformation targets, THEN use a clearly
  labelled world-space fallback and require a visible packaged-Player image
  gate. BECAUSE a state flag or hidden capture cannot prove facial alignment or
  presentation quality.
