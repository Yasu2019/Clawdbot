# 76-CaseA ショートショット・ボイド不具合

## AI引き継ぎ・全成果物ナレッジ統合ドキュメント

- 文書版: 2026-08-09
- 検証日時: 2026-08-09 21:50 JST以降
- 対象: Beads / Byterover / Obsidian / Gemini / Claude / GPT / Claude Code / Codex
- 正規保存先: `D:\Clawdbot_Docker_20260125\docs\handover\76CASEA_AI_HANDOVER_20260809.md`
- 文字コード: UTF-8（BOMなし）

> この文書は、確認済み事実、解析上の結論、未検証事項を区別して記録する。認証トークンは安全上記載しない。

## 1. プロジェクト概要

| 項目 | 内容 |
|---|---|
| 対象製品 | 76-CaseA カバー白（Part No. `NY0689-P01`） |
| 材料 | Cover White AY564（PP／エラストマー系25%ブレンドとのプロジェクト記録） |
| 製品重量 | 5.83 g |
| 成形機 | TOYO PLASTAR Si-450-6S、450トン |
| 金型 | SEIKI 6バルブ・ホットランナー |
| Case Aゲート座標 | X = -336.9、-255.6、-133.7 mm |
| 不具合位置 | L字フック爪部、X = -34.1、Y = 1.1、Z = 4.9 mm |
| 現象 | ショートショット、エアトラップ、ボイド。プロジェクト記録では再現率100% |

## 2. 解析結論

現在のプロジェクト仮説は、次の3現象の連成である。

1. 外周肉厚リブ（約1.8 mm）でレーストラッキングが発生する。
2. サーミスタブロックの左右から流れが回り込み、L字フック爪部をC字状に囲う。
3. 袋小路の空気が封止・圧縮され、樹脂流動に背圧を与える。

解析記録上の代表値:

- 空気背圧: 18.5 MPa
- 断熱圧縮温度: 350 ℃
- TOYO実効射出圧力: 159.0 MPa
- 必要圧力の解析推定: 175 MPa以上

これらの数値は解析モデル・実機ログに基づくプロジェクト結論であり、独立した第三者検証済みの保証値ではない。再利用時は元データと計算条件を確認すること。

## 3. 改善対策ロードマップ

| 優先 | 対策 | 条件・狙い | 検証指標 |
|---:|---|---|---|
| 1 | 多孔質真空ベントコア | L字爪底面に0.02 mm相当の排気経路を設ける | 欠肉率、ガス焼け、ベント詰まり |
| 2 | 薄肉部テーパー増肉 | 0.8 mmから1.1 mmへ局所増肉 | 充填率、重量、外観、寸法 |
| 3 | 第3バルブ遅延 | 開放を0.15秒遅延 | 合流位置、ウェルド、圧力履歴 |
| 4 | 多段速度制御 | 95%充填付近で120から35 mm/sへ減速、保圧80 MPa | ピーク圧、欠肉、バリ、サイクル |

対策は一度に混在させず、基準条件に対するDOEまたは一因子比較で効果を分離する。

## 4. 実行環境と接続

| ノード | 役割 | 接続 |
|---|---|---|
| K10 / Lavie | オーケストレーター | ローカルスクリプト実行 |
| Dynabook | Moldflowワーカー | `100.98.133.40`、ユーザー `mec21` |
| Job Worker | CAE指示受付 | `http://100.98.133.40:5683/healthz` |

- SSH鍵: `C:\Users\yasu\.ssh\moldflow_remote_ed25519`
- 秘密トークン: 本文には記載しない。ホスト環境変数 `SATELLITE_JOB_TOKEN` または承認済み秘密管理から取得する。
- トークンが過去の文書・チャット・ログへ平文露出した場合は、失効・再発行を推奨する。

## 5. 入力データ

2026-08-09の実在確認済み:

1. `C:\Users\yasu\OneDrive\デスクトップ\THH-260717-01_76ケースショート不良_1次報告書_Rev1.pdf`
2. `C:\Users\yasu\OneDrive\デスクトップ\PTY03 ケース外観写真(MITSUIコメント追記2).xlsx`
3. `C:\Users\yasu\OneDrive\デスクトップ\サーミスタ部拡大.pdf`
4. `C:\Users\yasu\OneDrive\デスクトップ\76Case_rute.jpg`
5. `C:\Users\yasu\OneDrive\デスクトップ\MDSReport_Cover White_NY0689-P01.pdf`
6. `C:\Users\yasu\OneDrive\デスクトップ\76ケース_データログ確認.xlsx`
7. `C:\Users\yasu\OneDrive\デスクトップ\m-NZFEY3-P54-01[76-CaseA]_CV010.stl`

追加参照候補（再開時に所在確認すること）:

- `IB2894-105_SI-450-6S(JPN).PDF`
- `OM1569A_SI-6S_(JPN).PDF`
- `固定.dxf`

## 6. 成果物

Downloadsで存在確認済み:

- `C:\Users\yasu\Downloads\76CaseA_ShortShot_Void_OpenFOAM_Report.pptx`
- `C:\Users\yasu\Downloads\76CaseA_ShortShot_Void_OpenFOAM_Report.pdf`
- `C:\Users\yasu\Downloads\P54_01_Exact_LHook_PhotoMatch_Fill.mp4`
- `C:\Users\yasu\Downloads\P54_01_UserRoute_MeltFlow_Animation.mp4`
- `C:\Users\yasu\Downloads\P54_01_Real_Wall_Filling_Animation.mp4`
- `C:\Users\yasu\Downloads\P54_01_Viewport_001mm_UltraMicroMesh_Fill.mp4`

追加生成・存在確認済み:

- `C:\Users\yasu\Downloads\P54_01_Exact_DXF_Gates_Flow_Animation.mp4`
  - 生成日時: 2026-08-09 21:47:17 JST
  - サイズ: 383,680 bytes
  - SHA-256: `D3C6F618B24E366F145ADF3EBAA553CED612B04A4BAA2E5EE66D1D6377C29E74`
  - 動画仕様: H.264、2560×1440、12 fps、55フレーム、4.583秒
  - FFmpeg全フレームデコード検査: エラー0

### DXFゲート動画に関する検証上の注意

- `render_exact_dxf_gate_flow.py` は表示ラベルとしてX = -336.9、-255.6、-133.7 mmを使用している。
- 実際の描画座標はSTL系の3点 `[-20.58,-485.11,-5.57]`、`[-20.58,-321.23,-5.57]`、`[-20.58,-78.68,-5.57]` をハードコードしている。
- 現版スクリプトは `固定.dxf` を実行時に読み込まず、製品全幅655.5 mmをコード上で照合していない。
- したがって、動画生成・Windows Downloads配置・3ゲート描画は検証済みだが、DXF原図に対する「100%正確」「655.5 mm全幅符合」は現時点で独立検証済みとは扱わない。
- Telegram送信関数と送信呼び出しは実装されている。成功応答を保存した永続ログは発見できなかったため、「送信済み」はユーザー申告として記録する。

## 7. 実行スクリプト

ルート: `D:\Clawdbot_Docker_20260125\scripts\`

- `generate_full_pptx_and_pdf_report.py`: PPTX/PDF報告書生成
- `render_exact_l_hook_short_shot.py`: L字フック爪部の可視化
- `render_user_route_flow_animation.py`: 手書き流動経路との比較
- `render_realistic_wall_filling.py`: キャビティ壁内の充填可視化
- `render_viewport_001mm_micro_mesh.py`: 高密度メッシュ可視化
- `render_exact_dxf_gate_flow.py`: DXFゲート配置の流動可視化
- `analyze_toyo_datalog_full.py`: TOYOログ統計解析
- `cae_te_remote_trial.py`: リモートCAE試行制御

## 8. 再開手順

1. 本文書の「未確認・要再生成」を確認する。
2. 入力ファイルを読み取り専用で存在・サイズ・更新日時・SHA-256照合する。
3. 実行中のCAE、収集、学習、レンダリング処理を確認し、無関係な旧処理は停止しない。
4. `固定.dxf` の正規パスを特定し、DXFからゲート座標を直接抽出してSTL座標変換を数式・検算値とともに保存する。
5. 製品全幅655.5 mm、3ゲート位置、カメラ投影範囲を機械検証したうえで、必要ならDXFゲート動画を再生成する。
6. PPTX/PDFの数値と元データの対応を再確認する。
7. 文書更新後、UTF-8 strict read、U+FFFD、典型的文字化け、リンク切れを検査する。
8. Beads、Obsidian、ベクトルDBへ同一版を登録し、ハッシュを記録する。

## 9. 引き継ぎ品質と未解決事項

- 本文書はUTF-8で保存し、文字化け検査を行う。
- 「完全」「100%」は検証証拠がある範囲に限定する。
- 解析値の根拠式、境界条件、材料物性、メッシュ収束性は元スクリプト・報告書で再確認する。
- DXF動画ファイル自体は完成成果物として扱うが、DXF原図との100%幾何符合は別の未解決検証項目として扱う。
- 秘密情報をMarkdown、Beads、Obsidian、ベクトルDBへ保存しない。
- `render_exact_dxf_gate_flow.py` にTelegram認証情報が平文で埋め込まれている。失効・再発行後、環境変数または秘密管理へ移行する。

## 10. 関連する永続ナレッジ

- `D:\Clawdbot_Docker_20260125\docs\handover\KNOWLEDGE_INGESTION_HANDOVER_20260809.md`
- `D:\Clawdbot_Docker_20260125\data\workspace\memory\knowledge_ingestion_repair_20260809.md`
- Beadsには本書の生成・検証結果を要約して記録する。

---

この文書を正規入口とし、別AIは未確認事項を既成事実として補完しないこと。
