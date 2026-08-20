# 76ケースA/B Moldflow設定監査（2026-08-10）

## 実行方針

- 既存のMoldflow study、定期タスク、監視プロセスは削除・上書きしない。
- Aは新規プロジェクト `CLAW_76CASE_VALIDATION_20260810`、BはMoldflow 2010の単一プロジェクト追加制約を避けた別プロジェクトとして作る。
- 材料DBで `Sumitomo Chemical Company / Noblen AY564 / ID 53781` を特定。報告書の `SILVERLEN PP AY564` との同一性確認までは解析を開始せず、汎用PPで代用しない。
- A/Bの実測不良位置との一致、充填時間、圧力履歴をMoldflow Insight 2010結果と比較してから予測精度を判定する。

## 入力ファイル完全性

| 入力 | サイズ (byte) | SHA-256 |
|---|---:|---|
| m-NZFEY3-P54-01[76-CaseA]_CV010.stl | 125,708,384 | `8374B53DCD6D3D919C61F0CDB037BEAD75DA3E32BD13941E752CB637FB066586` |
| m-NZFEY4-P54-01[76-CaseB]_CV010.stl | 128,354,484 | `BFC543584B0D66F156A7623B5A7911907EC2FFEEE63DD54089644194FD41BD16` |
| 固定.dxf | 1,483,329 | `4AEDE12CCFC7D4C8D9F0F18C187EC75F59A151881DED2D4C8420686EF962BF9F` |
| THH-260717-01_76ケースショート不良_1次報告書_Rev1.pdf | 3,007,178 | `9DD77756BB4EC55CC2832EF8E28DEC27A993247689E3F0ACCD6000C0F4E86D8D` |
| PTY03 ケース外観写真(MITSUIコメント追記2).xlsx | 364,454 | `EC4D81E98D0AE76FB6D457227798713159F4483521DE1C3C32522761088072B9` |
| 世紀初回【正式見積書】リチウムイオンバッテリーカバー型 (1).pdf | 390,575 | `779C7EBFC681D2F57EA1AF9F9EEDDE130C7D053B15DAC29C6F4770F14ECDE669` |

## 資料間の突合結果

- 不具合報告書: Case Aは7個発生、Case Bは捨てショットを含め発生なし。Aの不良部は最終充填位置との記載。
- 材料表記: `SILVERLEN PP AY564 ナチュラル`。
- 製品側ゲート径: `Φ0.85 mm × 各3か所`、`Φ1.1 mm × 各20か所`。
- 世紀見積書のホットランナー: 公称1.0 mmバルブ×2、公称1.6 mmバルブ×4、マニホールド×1。これは上記の製品側ゲート径とは別仕様であり、混同しない。
- 固定.dxf: A/Bに相当する2列で、X座標 `-336.905118...`, `-255.625118...`, `-133.705118...` の円中心を確認。ゲート配置との最終対応は報告書の配置図およびMoldflowのノード位置で再確認する。
- TOYOログ: 最大圧力管理値は約121.9914～135.0009 R MPa、実データは概ね126～130 R MPa、充填時間は概ね1.57～1.58 s。過去の159 MPa表記はストローク列の誤読であり使用しない。
- 不具合報告書自身が、従来解析では異径ゲートを同一径で設定したため実物との差があると明記している。

## 文字化け・抽出品質

- 不具合報告書27ページから38,658文字を抽出し、U+FFFDは0件。
- 見積書は画像PDFとしてレンダリングし目視確認。OCR由来の推測値を解析条件へ直接投入しない。
- Excelは文字セルがなく、640×480画像9枚を抽出して目視確認。画像注記は構造化テキストとして扱わない。

## Moldflow実行状態

- Dynabook worker `100.98.133.40:5683` およびMoldflow MCP `:8765` の接続を確認。
- 既存study `G:\moldflow_bridge\work\CLAW_MF_AUTOREPAIR_20260719_02\mf_fc_strip_out_study_(copy).sdy` は未変更。
- Case A STLを `G:\moldflow_bridge\work\cad\76CaseA_CV010_8374B53D.stl` へ転送し、SHA-256一致を確認。
- 新規Case A study `G:\moldflow_bridge\work\CLAW_76CASE_VALIDATION_20260810\76casea_baseline_1mm.sdy` と、CAD由来study `76casea_cv010_8374b53d_study.sdy`（約28.2 MB）を生成。1.0 mm Fusionメッシュ処理後にMCP応答復帰を確認。
- Case B STLを `G:\moldflow_bridge\work\cad\76CaseB_CV010_BFC54358.stl` へ転送し、SHA-256一致を確認。
- Case Bは1.0 mmおよび1.5 mmのFusionメッシュ生成がMoldflow MCP内部の300秒上限に達し、study未生成。失敗先は空ディレクトリのみで、Aおよび既存studyは未変更。反復実行は停止し、次回はCAD取込みとメッシュ生成を分離する。
- 材料カタログ8,169行からAY564は1件のみヒット: `id=53781`, `manufacturer=Sumitomo Chemical Company`, `trade_name=Noblen AY564`, `family=POLYPROPYLENES (PP)`。
- 材料設定、ゲートノード設定、解析開始は未実施。

## 未完了条件

1. Case AのCAD取り込み完了とメッシュ品質（自由辺、重複、アスペクト比、要素数）の確認。
2. Case BはCAD取込みとメッシュ生成を別APIに分離し、300秒制限を回避して独立studyを作成。
3. AY564の粘度、pVT、熱物性、転移/固化特性を含む正式材料カードの特定または作成。
4. 実機の射出速度段、樹脂温度、金型温度、V/P切替、保圧、冷却条件の確定。
5. 異径ゲート、6バルブの開閉タイミング、ランナー/ノズルを実仕様でモデル化。
6. Aの7件発生位置とBの非発生を盲検比較し、位置誤差・圧力誤差・充填時間誤差を評価。
