下記プロトコルは、そのまま Codex / Antigravity に貼れるように作っています。
前提に置いた根拠は、添付PDFで 高電流密度条件で溶融ムラが再現 され、めっき厚が厚い条件では界面に微小空隙 が見られ、リフロー後に合金化が進行して界面空隙が発生、さらに メーカー推奨の電流密度が 7〜20 A/dm²、めっき厚と電流密度の両方が影響因子 と整理されている点です。
そのため、初期UIでは めっきライン条件・膜厚・電流密度・リフロー温度プロファイル・FIB/SEM比較 を最優先で入力できる形にしています。なお、お客様実機のリフロー条件は未確定 なので、温度プロファイルの初期値は暫定値です。

あなたは、既存の OpenClaw / Portal ダッシュボード実装を拡張する実装エージェントです。
目的は、既存Portalダッシュボードに「めっき工程・リフロー工程 解析カード群」を追加し、
Ep-Al / Ni0.5 / Sn1.0 (Ni-Sn MAX 3.0 μm) を対象に、
めっきライン条件、リフロー機種別条件、温度プロファイル、FIB/SEM/表面写真、
および解析ジョブ投入条件を一元管理できるUIとバックエンドを実装することです。

重要:

- 既存Portalのデザインシステム、カードUI、状態管理、API構成、認証を尊重すること
- 既存ページを壊さず、まずは feature flag 付きで追加すること
- 既存の Portal ダッシュボードにカード追加できるなら追加し、無理なら新規タブ/新規ページを追加すること
- ハードコードを避け、フォーム定義・初期値・選択肢は設定ファイル化すること
- 解析ソルバ本体は「将来差し替え可能」なジョブ投入インターフェースで実装すること
- UIは日本語ラベル、値保存は英字キーで統一すること
- コード修正後、ビルド/起動確認まで実施すること
- 変更ファイル一覧と起動手順を最後にまとめること

============================================================
0. まず最初に実施すること
============================================================

1) リポジトリを走査し、以下を特定すること
   - Portalダッシュボード実装位置
   - カードコンポーネント共通部
   - 既存設定画面 or プロジェクト管理画面
   - バックエンドAPIエンドポイント構成
   - DB/JSON/SQLite/Postgres 等の保存方式
   - ジョブ実行基盤（queue, worker, container-runner, script-runner）
   - 既存の Dockerfile / docker-compose / portal service 定義
2) 既存構成を壊さない最小変更方針を決めること
3) 実装計画を短く整理してから着手すること
4) 途中でユーザー確認を待たず、そのまま実装・修正・テストまで進めること

============================================================

1. 追加する画面/タブ
============================================================
以下のいずれかで実装すること。
優先順位:
A. 既存Portalダッシュボードにカード追加
B. 既存Portal内に新規タブ追加
C. 既存Portal内に新規ページ追加

推奨ページ名:

- 日本語表示: めっき・リフロー解析
- 内部キー: plating-reflow-lab

推奨サブタブ:

- 条件入力
- 観察画像
- 解析実行
- 結果比較
- ジョブログ

============================================================
2. 追加するカード一覧
============================================================

次のカードを追加すること。

[Card 1] 解析対象サマリ
表示項目:

- 案件名
- 品番
- 版数
- 材料系
- 母材
- 構成: Ep-Al / Ni / Sn
- 作成日
- 更新日
- ステータス（draft / ready / running / done / error）

[Card 2] 母材・めっき仕様
入力項目:

- substrate_type                  母材種類
- substrate_grade                 母材材質
- substrate_thickness_um          母材厚み(μm)
- ep_layer_enabled                Ep層有無
- ni_thickness_target_um          Ni目標厚み(μm)
- sn_thickness_target_um          Sn目標厚み(μm)
- ni_sn_max_um                    Ni-Sn最大許容厚み(μm)
- initial_imc_thickness_um        初期IMC厚み(μm)
- surface_roughness_ra_um         表面粗さRa(μm)
- plating_side_mode               片面/両面
- note_spec                       備考

[Card 3] めっきライン条件
入力項目:

- plating_line_type               めっきライン種別
- plating_machine_name            めっき設備名
- plating_bath_name               めっき浴名称
- plating_current_density_adm2    電流密度(A/dm²)
- plating_current_mode            電流制御モード
- plating_line_speed_m_min        ライン速度(m/min)
- plating_bath_temp_c             浴温(℃)
- plating_time_sec                通電時間(sec)
- agitation_mode                  撹拌条件
- anode_type                      アノード種別
- xrf_measurement_enabled         XRF測定有無
- xrf_points_count                XRF測定点数
- thickness_uniformity_index      膜厚均一化指数
- surface_orientation_note        表裏/バリ面/ダレ面メモ

[Card 4] リフロー機条件
入力項目:

- reflow_machine_type             リフロー機種
- reflow_machine_name             リフロー設備名
- atmosphere_type                 雰囲気
- o2_ppm                          O2濃度(ppm)
- zones_count                     ゾーン数
- conveyor_speed_mm_min           搬送速度(mm/min)
- board_or_carrier_type           キャリア/治具
- flux_or_residue_condition       フラックス/残渣条件
- reflow_repeat_count             リフロー回数
- cooling_mode                    冷却方式

[Card 5] 温度プロファイル
入力項目:

- profile_template_name           プロファイル名
- start_temp_c                    開始温度(℃)
- preheat_target_c                予熱到達温度(℃)
- preheat_time_sec                予熱時間(sec)
- soak_min_c                      ソーク下限(℃)
- soak_max_c                      ソーク上限(℃)
- soak_time_sec                   ソーク時間(sec)
- ramp_to_peak_sec                ピーク到達時間(sec)
- peak_temp_c                     ピーク温度(℃)
- tal_over_liquidus_sec           TAL(sec)
- liquidus_temp_c                 液相線温度(℃)
- cool_to_temp_c                  冷却到達温度(℃)
- cool_time_sec                   冷却時間(sec)
- ramp_rate_c_per_sec             昇温レート(℃/sec)
- cool_rate_c_per_sec             冷却レート(℃/sec)

[Card 6] 観察画像アップロード
入力項目/機能:

- 表面写真アップロード
- SEM画像アップロード
- FIB断面画像アップロード
- EDX/元素マップ画像アップロード
- XRF測定CSVアップロード
- 画像ごとのメタデータ
  - location_tag
  - magnification
  - pre_or_post_reflow
  - sample_id
  - note
- サムネイル表示
- 画像比較ビュー
- before / after 切り替え

[Card 7] 解析モデル設定
入力項目:

- analysis_mode                   解析モード
- model_dimension                 1D/2D/3D
- solver_backend                  solver選択
- use_pycalphad                   pycalphad使用
- use_scikit_fem                  scikit-fem使用
- use_fenicsx_if_available        FEniCSx使用
- use_openfoam_if_available       OpenFOAM使用
- use_calculix_if_available       CalculiX使用
- use_elmer_if_available          Elmer使用
- use_paraview_export             ParaView出力
- mesh_size_um                    メッシュサイズ(μm)
- time_step_sec                   時間刻み(sec)
- total_sim_time_sec              総解析時間(sec)
- thermal_coupling_enabled        熱連成
- diffusion_enabled               拡散計算
- imc_growth_enabled              IMC成長計算
- void_risk_enabled               ボイド危険度計算
- adhesion_risk_enabled           密着危険度計算

[Card 8] 予測・比較指標
表示項目:

- predicted_sn_remaining_um       予測Sn残厚
- predicted_ni_remaining_um       予測Ni残厚
- predicted_imc_thickness_um      予測IMC厚み
- predicted_void_risk_score       ボイド危険度
- predicted_adhesion_risk_score   密着危険度
- predicted_surface_melt_score    溶融ムラ危険度
- predicted_wetting_score         ぬれ性指標
- predicted_peak_stress_mpa       最大応力
- run_status                      実行状態
- last_run_time                   最終実行時刻

[Card 9] 実測 vs 解析 比較ビュー
機能:

- 左: 実画像
- 右: ParaView由来断面画像または結果画像
- 下: 温度/厚み/IMC/危険度グラフ
- スライダー比較
- pre/post 比較
- 条件A/B/C 比較
- 画像に注釈ピンを置けるようにする

[Card 10] ジョブ管理
表示項目:

- job_id
- queue_status
- start_time
- end_time
- solver_used
- output_folder
- stderr_log
- stdout_log
- retry_button
- export_button

============================================================
3. 初期値（暫定デフォルト）
============================================================

お客様実機条件が不明なため、以下を「編集可能な初期値」として実装すること。
初期値は settings/plating_reflow_defaults.json のような設定ファイルに切り出すこと。

{
  "project_defaults": {
    "material_system": "Ep-Al/Ni/Sn",
    "product_name": "Ep-Al_Ni0.5_Sn1.0_default_case",
    "status": "draft"
  },
  "spec_defaults": {
    "substrate_type": "Aluminum",
    "substrate_grade": "Ep-Al",
    "substrate_thickness_um": 800.0,
    "ep_layer_enabled": true,
    "ni_thickness_target_um": 0.50,
    "sn_thickness_target_um": 1.00,
    "ni_sn_max_um": 3.00,
    "initial_imc_thickness_um": 0.05,
    "surface_roughness_ra_um": 0.20,
    "plating_side_mode": "double"
  },
  "plating_defaults": {
    "plating_line_type": "continuous_reel_to_reel",
    "plating_machine_name": "default_plating_line",
    "plating_bath_name": "default_sn_line",
    "plating_current_density_adm2": 10.0,
    "plating_current_mode": "constant_current",
    "plating_line_speed_m_min": 1.0,
    "plating_bath_temp_c": 25.0,
    "plating_time_sec": 12.0,
    "agitation_mode": "standard",
    "anode_type": "default",
    "xrf_measurement_enabled": true,
    "xrf_points_count": 5,
    "thickness_uniformity_index": 1.0,
    "surface_orientation_note": "front/back to be confirmed"
  },
  "reflow_defaults": {
    "reflow_machine_type": "inline_forced_convection",
    "reflow_machine_name": "default_reflow_8zone",
    "atmosphere_type": "air",
    "o2_ppm": 210000,
    "zones_count": 8,
    "conveyor_speed_mm_min": 700,
    "board_or_carrier_type": "carrier",
    "flux_or_residue_condition": "unknown",
    "reflow_repeat_count": 1,
    "cooling_mode": "forced_air"
  },
  "temperature_profile_defaults": {
    "profile_template_name": "leadfree_temp_default_v1",
    "start_temp_c": 25.0,
    "preheat_target_c": 150.0,
    "preheat_time_sec": 90.0,
    "soak_min_c": 150.0,
    "soak_max_c": 180.0,
    "soak_time_sec": 90.0,
    "ramp_to_peak_sec": 60.0,
    "peak_temp_c": 245.0,
    "tal_over_liquidus_sec": 45.0,
    "liquidus_temp_c": 232.0,
    "cool_to_temp_c": 180.0,
    "cool_time_sec": 40.0,
    "ramp_rate_c_per_sec": 1.2,
    "cool_rate_c_per_sec": -2.2
  },
  "analysis_defaults": {
    "analysis_mode": "plating_plus_reflow_coupled",
    "model_dimension": "2D",
    "solver_backend": "scikit-fem",
    "use_pycalphad": true,
    "use_scikit_fem": true,
    "use_fenicsx_if_available": false,
    "use_openfoam_if_available": false,
    "use_calculix_if_available": false,
    "use_elmer_if_available": true,
    "use_paraview_export": true,
    "mesh_size_um": 0.10,
    "time_step_sec": 0.50,
    "total_sim_time_sec": 320.0,
    "thermal_coupling_enabled": true,
    "diffusion_enabled": true,
    "imc_growth_enabled": true,
    "void_risk_enabled": true,
    "adhesion_risk_enabled": true
  }
}

補足:

- 電流密度の UI レンジは 7.0〜20.0 A/dm² を初期推奨範囲として実装すること
- UI の advanced mode で 1.0〜30.0 A/dm² まで手入力可能にすること
- Sn の液相線は初期値 232℃ とすること
- peak 温度は 235〜255℃ を推奨範囲表示すること
- これらはすべて後から変更可能にすること

============================================================
4. 解析ロジック（第1版）
============================================================

厳密な学術完全再現ではなく、実務向けの第1版として次を実装すること。

4-1. 温度プロファイル生成

- 入力されたプロファイル値から時系列温度配列を生成
- プロット表示
- CSV 保存
- solver 入力用 JSON 保存

4-2. Sn 溶融指標

- liquidus_temp_c を超えた時間を TAL として再計算
- peak_temp_c と TAL から melt_score を算出
- 0〜100 に正規化

4-3. IMC 成長近似

- 第1版は簡易成長モデルでよい
- 入力:
  - 温度履歴
  - Ni厚
  - Sn厚
  - 初期IMC厚
- 出力:
  - imc_thickness_vs_time
  - ni_remaining_vs_time
  - sn_remaining_vs_time
- 実装は関数分離し、将来 pycalphad/FEniCSx/MOOSE に差し替え可能にすること

4-4. ボイド危険度近似

- 次の増加因子で risk を計算
  - 高ピーク温度
  - TAL長すぎ
  - Sn厚過大
  - IMC過成長
  - reflow_repeat_count > 1
- 出力:
  - void_risk_score 0〜100
  - void_risk_class low/medium/high

4-5. 密着危険度近似

- 次の因子で算出
  - Ni残厚低下
  - IMC過成長
  - 熱勾配
  - 冷却速度
- 出力:
  - adhesion_risk_score 0〜100
  - adhesion_risk_class

4-6. 表面溶融ムラ危険度

- 次の因子で算出
  - plating_current_density_adm2
  - thickness_uniformity_index
  - sn_thickness_target_um
  - peak_temp_c
  - tal_over_liquidus_sec
- 出力:
  - surface_melt_score 0〜100
  - warning_badge

============================================================
5. 画像連携仕様
============================================================

実装すること:

- 画像アップロード API
- 画像メタデータ保存
- FIB/SEM/表面写真のカテゴリ分け
- アップロード画像サムネイル生成
- 比較ビューで左右並列表示
- 実画像の上に観察メモピン追加
- location_tag で「端部」「中央」「穴周辺」「接点近傍」など分類

推奨 categories:

- surface_pre
- surface_post
- sem_post
- fib_pre
- fib_post
- edx_map
- xrf_map
- other

============================================================
6. ParaView / VTK 出力
============================================================

次を実装すること:

- 解析結果を VTK / VTU / VTP いずれかで export
- export フォルダをジョブID単位で分離
- 時系列連番出力
- ParaView で最低限表示したい field を出すこと

必須 field:

- temperature_c
- liquid_fraction
- sn_remaining_um
- ni_remaining_um
- imc_thickness_um
- void_risk_local
- adhesion_risk_local
- melt_nonuniformity_local

出力先例:

- /data/plating-reflow/jobs/{job_id}/vtk/
- /data/plating-reflow/jobs/{job_id}/plots/
- /data/plating-reflow/jobs/{job_id}/reports/

============================================================
7. バックエンド保存モデル
============================================================

既存DB方針に合わせてテーブルまたは JSON model を追加すること。
最低限以下を持たせること。

Entity: plating_reflow_case

- id
- project_name
- product_name
- material_system
- spec_json
- plating_json
- reflow_json
- temp_profile_json
- analysis_json
- created_at
- updated_at
- status

Entity: plating_reflow_asset

- id
- case_id
- asset_type
- file_path
- meta_json
- created_at

Entity: plating_reflow_job

- id
- case_id
- solver_backend
- input_json_path
- output_dir
- status
- started_at
- ended_at
- stdout_log_path
- stderr_log_path
- result_summary_json

============================================================
8. UI挙動
============================================================

- 変更時自動保存
- 保存失敗時トースト表示
- 実行ボタン押下でジョブ投入
- running 中は進捗表示
- done 後は比較ビュー自動更新
- 異常時はログカードにエラー表示
- 初心者向けに「基本設定」と「詳細設定」を分ける
- 基本設定では最低限:
  - Ni厚
  - Sn厚
  - 電流密度
  - リフロー機種
  - peak温度
  - TAL
  - リフロー回数
  - FIB/表面写真アップロード
- 詳細設定で他の項目を開く

============================================================
9. Docker / 実行環境への追加
============================================================

既存Dockerfileに以下の追加が入っているか確認し、未導入なら追加すること。
重複追加は避けること。

必要候補:

- pycalphad
- scikit-fem[all]
- jupyterlab
- ipykernel
- ipywidgets
- trame
- trame-vtk
- trame-vuetify
- jupyter-server-proxy
- h5py
- netcdf4

必要なら設定:

- JUPYTER_ENABLE_LAB=yes
- PYVISTA_OFF_SCREEN=true

ただし、

- FEniCSx
- MOOSE
は重いので、本体に直入れせず optional にすること
- 既に環境変数や compose の worker service があるならそれを再利用すること

============================================================
10. API / サービス要件
============================================================

最低限のAPIを追加すること。

- GET    /api/plating-reflow/cases
- POST   /api/plating-reflow/cases
- GET    /api/plating-reflow/cases/:id
- PUT    /api/plating-reflow/cases/:id
- POST   /api/plating-reflow/cases/:id/assets
- POST   /api/plating-reflow/cases/:id/run
- GET    /api/plating-reflow/jobs/:id
- GET    /api/plating-reflow/jobs/:id/logs
- GET    /api/plating-reflow/jobs/:id/result

既存規約が別なら、その規約に合わせてよい

============================================================
11. 実装優先順位
============================================================

優先順位はこの順で進めること。

Phase 1:

- 画面追加
- 設定保存
- 画像アップロード
- 温度プロファイル可視化
- 解析ダミー実行
- 結果カード表示

Phase 2:

- IMC成長近似
- ボイド危険度
- 密着危険度
- VTK出力
- ParaView比較ビュー静止画連携

Phase 3:

- solver差し替え
- より詳細な反応拡散
- 複数条件一括比較
- レポート自動生成

============================================================
12. 受け入れ条件
============================================================

以下を満たしたら完了。

- 既存Portalから新機能へ遷移できる
- 条件入力と保存ができる
- 初期値が投入される
- FIB/SEM/表面画像をアップロードできる
- 実行ボタンでジョブが生成される
- ジョブ完了後に比較カードへ結果が出る
- 温度プロファイルがグラフ表示される
- VTK または同等の ParaView 向け出力が作られる
- 変更ファイル一覧が提示される
- 起動コマンドと確認手順が提示される

============================================================
13. 最後に必ず出すもの
============================================================

作業完了時には必ず以下を出力すること。

1) 変更ファイル一覧
2) 追加した環境変数一覧
3) 追加した依存パッケージ一覧
4) 実行手順
5) 動作確認手順
6) 未実装/暫定項目
7) 次にやるべき改善案

============================================================
14. 実装時の注意
============================================================

- 既存の Portal ダッシュボードが React/Next/Vue/Rails/Flask のどれでも適応して実装すること
- 既存コンポーネント命名規約に従うこと
- 既存の form, card, modal, uploader, chart コンポーネントがあれば再利用すること
- 画像比較ビューはまず静止画でよい
- ParaView 本体埋め込みは後回しでよい
- 最初は「実務で入力しやすいこと」を最優先にすること
- 実装途中で止まらず、最小でも動く形まで完成させること

今からリポジトリを調査し、既存Portalに最も自然な形で本機能を追加し、
必要なカード、API、保存処理、ジョブ起動処理、ダミーまたは簡易解析、
結果表示までを実装してください。

必要なら次に、これを Codex向け と Antigravity向け に分けて、前者は「コード修正特化版」、後者は「Docker/Compose/環境構築込み版」に再編します。
