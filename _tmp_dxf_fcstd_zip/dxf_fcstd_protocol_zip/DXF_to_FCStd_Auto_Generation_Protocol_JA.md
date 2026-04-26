# DXF → FCStd 自動生成プロトコル
## 対象
- Docker コンテナ内に FreeCAD が導入済み
- 実装担当: Codex / Claude Code / Antigravity 等
- 最終成果物: 編集可能な FCStd, 実行用 Python/FCMacro, ログ, 判定レポート

## 1. 目的
ユーザーが事前に整理した第三角法の2D DXF図面から、
FreeCAD PartDesign ベースの生成ツリーを持つ FCStd を自動生成する。

生成されるモデルは、以下を満たすこと。
- FreeCAD上で生成ツリーから編集可能
- ベース形状は Sketch + Pad
- ザグリは原則 PartDesign Hole
- ポケット/抜き形状は Sketch + Pocket
- 不要なテーパ、ロフト、メッシュ近似面を生成しない
- 寸法解釈が曖昧な場合は勝手に補完せず停止または保留レポート
- 後工程でユーザーが修正・削除・穴追加・寸法変更・拘束見直しを行いやすい構造

## 2. 最重要方針
### 2.1 やってはいけないこと
1. OBJ/STLメッシュから形状を逆生成してFCStd化すること
2. 根拠のないテーパを付けること
3. Loft / Sweep / ruled surface で曖昧に埋めること
4. 寸法が不明なのに穴深さ・ザグリ深さを推定確定すること
5. 複数ソリッドを乱立させること
6. 線群から閉ループ検出に失敗したのに、そのまま押し出すこと
7. 寸法線・文字・補助線を製品輪郭として採用すること

### 2.2 必ず守ること
1. 単一Body中心
2. Feature tree を明示命名
3. 曖昧箇所は report.json / report.md に残す
4. 自動生成した各Featureに由来情報を残す
5. 失敗しても途中成果物を保存
6. ユーザーが FreeCAD GUI で追跡できる構成にする

## 3. 入力前提
ユーザーはDXFを事前に整理する。

### 3.1 残してよいもの
- 製品外形線
- 加工形状線
- 穴中心や穴円
- ザグリ指示に必要な寸法線
- 正面図 / 側面図 / 平面図
- 必要な中心線
- 必要最小限の文字注記

### 3.2 削除済みであるべきもの
- 外枠
- 表題欄
- 不要な寸法線
- 参考図
- 重複図形
- 旧版の痕跡
- 関係ない注記

### 3.3 DXFの望ましい条件
- 第三角法である
- 各ビューが空間的に分離されている
- 単位は mm
- 同一ビュー内で線が大きく崩れていない
- 線種やレイヤである程度意味分けされていると望ましい

## 4. 出力成果物
最低限、以下を生成すること。
1. output/model.FCStd
2. output/report.md
3. output/report.json
4. output/preview.png
5. output/export.step
6. output/export.stl
7. logs/process.log

可能なら追加:
- output/feature_map.json
- output/detected_views.svg
- output/diagnostic_cleaned_dxf.FCStd

## 5. 生成ツリーの標準構成
FreeCAD document 名: AutoModel

Body 名:
- Body_Main

推奨 Feature 命名:
- Sketch_BaseProfile
- Pad_Base
- Sketch_Pocket_Front_01
- Pocket_Front_01
- Sketch_Pocket_Front_02
- Pocket_Front_02
- Sketch_HolePattern_Front_01
- Hole_CBore_01
- Hole_CBore_02
- Sketch_Hole_Through_01
- Hole_Through_01
- DatumPlane_Front
- DatumPlane_Right
- DatumPlane_Top

禁止:
- Sketch001, Pad002 のような無意味連番のみ
- Fusion, Loft, Sweep を安易に使うこと

## 6. 形状生成の基本ロジック
### 6.1 ベース形状
ベース形状は以下のいずれかで作る。

優先順位:
1. 側面図または断面図から板厚方向を含む断面形状を取得し Pad
2. それが不可能な場合、正面外形 + 別寸法から厚み指定して Pad
3. それも不可能なら停止し、厚み未確定レポートを出す

重要:
- ベース形状は直線と円弧からなる閉ループ
- 根拠のない draft angle を入れない
- 複数ループがある場合、外周/内周を明確に判別

### 6.2 穴
穴は原則 PartDesign Hole を使う。

穴分類:
1. 貫通穴
2. 止まり穴
3. ザグリ穴
4. 皿穴
5. 不明

判定ルール:
- 円 + 寸法注記 + ザグリ注記あり → Hole で counterbore/countersink
- 円のみで深さ不明 → 原則貫通穴候補として保留扱い
- 円が正面図にあり、側面図に段付き断面が見える → ザグリ候補
- 寸法から貫通が明記されない限り、深さを勝手に決めない

ザグリは次のパラメータを保持可能な構造で実装する。
- pilot diameter
- counterbore diameter
- counterbore depth
- through / blind

不明な項目がある場合:
- Hole作成を見送り
- Sketch_Candidate_CBore_xx を残す
- report に要確認と出す

### 6.3 ポケット
矩形抜きや開口部などは Pocket を使う。

Pocketの条件:
- 閉ループであること
- ベースの対象面に投影可能であること
- 深さが明記されること
- 貫通なら Through All
- 深さ未確定なら保留

注意:
- 2D図で開口に見えても、実際は片側段欠きかもしれない
- 側面/断面との突合で確認すること

## 7. ビュー検出ロジック
DXFから正面図・側面図・平面図を分離する必要がある。
完全自動が難しい場合でも、半自動で bbox 指定できる設計にする。

### 7.1 検出モード
1. auto mode
   - 図形クラスタリング
   - 外接矩形
   - 面積・要素数・中心位置で候補選定
2. semi-auto mode
   - config JSON で view bbox を与える

### 7.2 config例
```json
{
  "units": "mm",
  "views": {
    "front": [0, 0, 120, 80],
    "right": [130, 0, 190, 80],
    "top": [0, 90, 120, 140]
  },
  "base_strategy": "right_view_profile",
  "front_reference_face": "XZ",
  "depth_axis": "Y"
}
```

### 7.3 実装方針
- まずは semi-auto を標準
- auto は補助機能
- ビュー認識失敗時は必ず停止

## 8. DXF解析方針
使用候補:
- FreeCAD Draft import
- ezdxf
- FreeCAD Part / Sketcher API

推奨:
- DXFの前処理は ezdxf
- 最終形状生成は FreeCAD API

解析対象エンティティ:
- LINE
- LWPOLYLINE
- POLYLINE
- ARC
- CIRCLE
- TEXT / MTEXT
- INSERT

前処理:
1. 不要レイヤ除外
2. 重複線除去
3. 微小セグメント除去
4. endpoint snap
5. 閉ループ候補抽出
6. 円・円弧認識
7. 注記抽出

## 9. 閉ループ検出の条件
閉ループ検出は最重要。

条件:
- 端点距離許容値 tol_join を設ける
- 小さすぎるギャップは補正
- 自己交差ループを除外
- 面積が極端に小さいループは除外
- 寸法線由来の細長い閉ループを除外

優先順位:
- 最大面積の閉ループ = ベース外形候補
- 内包ループ = ポケット/開口/穴候補
- 円 = 穴候補として別処理

## 10. 寸法解釈のルール
文字解析は補助であり、100%自動理解を期待しない。

最低限認識したいパターン:
- φ5
- Φ5
- 5キリ
- 深さ3
- ザグリ φ8 深さ2
- CBORE 8x2
- THRU

基本姿勢:
- 寸法注記が明確なら採用
- 明確でなければ形状線優先
- 解釈不確定なら保留

## 11. FreeCADでの生成手順
### 11.1 ドキュメント生成
- 新規Document作成
- PartDesign Body 作成
- 原点・基準面確保

### 11.2 ベーススケッチ生成
- 側面図または断面図から閉ループ取得
- Sketch_BaseProfile 作成
- ジオメトリ投入
- 必要最低限の拘束付与
- 過拘束は避ける

### 11.3 Pad
- Pad_Base
- 長さは front view / config / thickness から決定
- 対称押し出しは避け、基準を固定
- モデル原点との関係を report に残す

### 11.4 前面加工
- 前面に datum plane または support face を定める
- Sketch_Pocket_Front_xx
- 開口部は Pocket
- 円穴は Hole 候補へ振り分け

### 11.5 ザグリ加工
- Sketch_HolePattern_Front_xx
- Hole feature を生成
- counterbore/countersink が確定している場合のみ実施
- 不明時は候補スケッチだけ残す

### 11.6 側面加工
- 側面図由来のポケットや穴がある場合
- 対象面に新規 Sketch
- Pocket / Hole を追加

### 11.7 仕上げ
- recompute
- トポロジーエラー検査
- 単一Body確認
- STEP/STL出力
- サムネイル画像出力

## 12. 推奨実装構成
```text
project/
  app/
    main.py
    config_schema.py
    dxf_parser.py
    dxf_cleaner.py
    view_detector.py
    loop_detector.py
    annotation_parser.py
    feature_inference.py
    freecad_builder.py
    validators.py
    reporters.py
    exporters.py
  macros/
    build_from_dxf.FCMacro
  configs/
    sample_config.json
  tests/
    test_loops.py
    test_hole_inference.py
    test_builder.py
  output/
  logs/
```

## 13. モジュール別要件
### 13.1 dxf_parser.py
- ezdxfでエンティティを読み込む
- layer, type, bbox, geometry を抽出
- 出力: 正規化済み entity list

### 13.2 dxf_cleaner.py
- 重複線除去
- 微小線除去
- snap
- 不要レイヤ除去

### 13.3 view_detector.py
- ビュー領域推定
- semi-auto bbox を優先
- 候補の可視化

### 13.4 loop_detector.py
- 閉ループ抽出
- 外周/内周判定
- 面積計算
- 自己交差チェック

### 13.5 annotation_parser.py
- TEXT/MTEXTから穴径・ザグリ深さ候補抽出
- パターン辞書で認識

### 13.6 feature_inference.py
- どのループをベース/ポケット/穴にするか決定
- 不確定なら HOLD

### 13.7 freecad_builder.py
- FreeCAD document 作成
- Sketch, Pad, Hole, Pocket 生成
- 命名統一
- 由来情報保持

### 13.8 validators.py
- shape validity
- single solid check
- unexpected taper check
- feature dependency check

### 13.9 reporters.py
- markdown/json レポート出力
- 曖昧点一覧
- 推定根拠一覧

## 14. 余計なテーパ防止ルール
今回の失敗を踏まえて、不要テーパ防止を明示ルールにする。

禁止条件:
- 直線断面の押し出しから、断面寸法が途中で変化してはいけない
- 明示された draft/taper 寸法がない限り、壁面角度は90°前提
- 曲面化や補間面は禁止

検証:
- ベースPad後、任意高さ断面を複数切って断面比較
- 断面形状が変化していたらエラー
- validators.py に入れること

## 15. ユーザー修正しやすいFCStdにするためのルール
1. 各Feature名を意味的にする
2. スケッチは1機能1目的
3. 1つのスケッチに何でも詰め込まない
4. 穴は Hole、開口は Pocket に分ける
5. 由来ビューを properties / report に残す
6. できれば Spreadsheet を使って主要寸法を変数化する

## 16. Spreadsheet連携の推奨
可能なら、FreeCAD document 内に Spreadsheet を作る。

例:
- thickness
- base_width
- base_height
- hole1_diameter
- cbore1_diameter
- cbore1_depth

Feature 側からこれを参照させると、後修正しやすい。
ただし初版では無理に全部変数化しなくてよい。
まずは安定生成優先。

## 17. レポート出力仕様
report.md には最低限以下を書くこと。

### 17.1 解析概要
- 入力ファイル名
- 実行時刻
- 使用config
- 検出ビュー数
- 抽出ループ数
- 作成Feature数

### 17.2 確定したもの
- ベース外形
- 押し出し長さ
- 穴径
- ザグリ径
- ザグリ深さ
- Pocket深さ

### 17.3 保留項目
- 深さ不明
- 断面不整合
- ビュー不一致
- 文字解釈不能
- 閉ループ失敗

### 17.4 危険項目
- 同名Featureの重複
- 自己交差スケッチ
- 複数ソリッド化
- 断面変化
- 不要テーパ疑い

## 18. 実行モード
### 18.1 CLIモード
```bash
python app/main.py \
  --input /data/input/sample.dxf \
  --config /data/configs/sample_config.json \
  --output /data/output
```

### 18.2 FreeCAD headless
```bash
freecadcmd macros/build_from_dxf.FCMacro -- \
  --input /data/input/sample.dxf \
  --config /data/configs/sample_config.json \
  --output /data/output
```

実装上の注意:
- headless動作を優先
- GUI必須処理は避ける
- 画像出力だけ GUI が要る場合は fallback を用意

## 19. テスト要件
最低限以下のテストを作ること。

### 19.1 単純矩形 + 貫通穴
- ベース矩形
- 1円穴
- 期待: Pad + Hole

### 19.2 矩形 + ザグリ穴
- front circle
- cbore寸法あり
- 期待: Hole(counterbore)

### 19.3 ベース + Pocket
- 開口部あり
- 期待: Pocket

### 19.4 余計なテーパ検出
- 断面一致検査
- 期待: taperなし

### 19.5 ループ不完全
- 微小ギャップあり
- 期待: 自動補正 or 停止レポート

## 20. Codexへの具体的な実装指示
以下をそのまま実装方針として採用すること。

### 実装タスク
1. Dockerコンテナ内の FreeCAD 実行方法確認
2. Python から FreeCAD module import 可否確認
3. ezdxf 利用可否確認
4. DXF解析モジュール作成
5. semi-auto view bbox config 対応
6. loop detector 実装
7. feature inference 実装
8. FreeCAD builder 実装
9. report 出力実装
10. サンプルDXFで FCStd 生成
11. STEP/STL/PNG 出力
12. 不要テーパ検証追加
13. 失敗時ログ整備
14. README 作成

### 実装優先順位
- 第1優先: 安定してPad/Hole/Pocketの木を作る
- 第2優先: ザグリ自動認識
- 第3優先: 寸法注記解析の強化
- 第4優先: 完全自動ビュー認識

## 21. 初版で妥協してよい点
初版では以下は未完成でもよい。
- 全注記の高精度OCR/意味解析
- 完全自動の第三角法ビュー判定
- 複雑断面の完全理解
- 皿穴の全表記揺れ対応
- 幾何公差や表面粗さ記号の理解

初版で必須なのはあくまで:
- ベースが正しくPadされる
- 穴がHoleで作れる
- Pocketが不要テーパなしで作れる
- FCStdが編集可能

## 22. 実装完了の受入基準
以下を満たしたら合格。
1. FCStd を FreeCAD GUI で開ける
2. 生成ツリーに意味的な Feature 名がついている
3. Pad/Hole/Pocket が履歴に残る
4. ユーザーが Hole の径や深さを修正できる
5. 不要テーパが存在しない
6. report.md に保留事項が明記される
7. STEP と STL が出る
8. 失敗時に原因が分かるログがある

## 23. Codexに貼る実行依頼文
```markdown
あなたは、Dockerコンテナ内に導入済みの FreeCAD を使って、
2D DXF から編集可能な FCStd を自動生成する実装担当です。

最終目的は、メッシュ変換ではなく、
FreeCAD の PartDesign ベースの生成ツリーを持つ FCStd を作ることです。

必須条件:
- 出力は FCStd
- 生成ツリーは Body + Sketch + Pad + Hole + Pocket を基本にする
- ザグリは原則 PartDesign Hole を使う
- 不要なテーパを絶対に入れない
- Loft/Sweep/メッシュ近似は禁止
- 寸法が曖昧な箇所は勝手に確定せず、report に保留として出す
- ユーザーが後から FreeCAD GUI で修正、削除、追加工できる構成にする

入力前提:
- ユーザーが DXF から不要な外枠、表題欄、不要寸法線を削除済み
- 第三角法の正面図/側面図/平面図がある
- ザグリなど必要寸法線は残っている場合がある

実装してほしいもの:
1. DXF解析モジュール
2. ビュー検出または config で bbox 指定
3. 閉ループ抽出
4. feature inference
5. FreeCAD builder
6. FCStd出力
7. STEP/STL/PNG出力
8. report.md/report.json 出力
9. 不要テーパ検出
10. README

推奨構成:
- dxf_parser.py
- dxf_cleaner.py
- view_detector.py
- loop_detector.py
- annotation_parser.py
- feature_inference.py
- freecad_builder.py
- validators.py
- reporters.py
- main.py
- macros/build_from_dxf.FCMacro

実装ルール:
- ベース形状は Sketch_BaseProfile + Pad_Base
- 穴は Hole_Through_xx または Hole_CBore_xx
- 開口は Pocket_xx
- 無意味な Sketch001 などの名前は避ける
- 失敗時ログを残す
- 中途成果物も保存する
- 初版は semi-auto config 前提でよい
- 完全自動よりも、安定・編集可能・不要テーパ無しを優先する

まず最初に、
(1) コンテナ内 FreeCAD 実行方法確認
(2) Python import 可否確認
(3) ezdxf 利用可否確認
(4) サンプルDXFで最小PoC作成
の順で進めてください。

その後、
- 実装計画
- ディレクトリ構成
- 主要ファイル
- 実行コマンド
- 初回PoC結果
を示し、
次に本実装へ進んでください。
```

## 24. 追加の強化指示
精度を上げたい場合は、以下を追加要件として採用する。
```markdown
追加要件:
- Spreadsheet を使って主要寸法をパラメータ化する
- feature_map.json に各Featureの由来ビューと根拠を書き出す
- 断面比較により不要テーパを自動検出する
- 深さ不明のザグリは候補スケッチだけ生成して report に保留出力する
- config で front/right/top の bbox を与えられるようにする
- DXF中の TEXT/MTEXT から φ, depth, c'bore, thru をパターン抽出する
```

## 25. 推奨する進め方
最初から完全自動を狙わず、次の3段階で進める。

### Phase 1
- semi-auto bbox
- ベースPad
- 貫通穴
- simple pocket
- FCStd保存

### Phase 2
- ザグリ認識
- Hole counterbore
- report強化
- Spreadsheet導入

### Phase 3
- 注記解釈拡張
- 自動ビュー判定
- 複雑断面対応
- GUI補助ツール

## 26. 既存コードの扱い方針
既存の DXF → STEP 変換アプリがある場合、いきなり削除しない。

### 原則
- まず現行コードの責務分解を行う
- 再利用できる部分は流用
- 形状生成がメッシュ依存、Loft依存、テーパ誤生成を起こす部分は置換候補

### 先に確認する項目
1. DXF読込処理
2. entity正規化処理
3. view分離ロジック
4. loop抽出ロジック
5. STEP出力ロジック
6. 既存テスト
7. CLI引数体系
8. 依存ライブラリ
9. 出力物の保存場所
10. 既存ユーザー設定ファイル

### 融合が向くケース
- DXFパーサが安定
- bbox設定やレイヤ除外が既にある
- report/log基盤が既にある
- Docker 起動ルールに既存資産がある

### 置換が向くケース
- メッシュから逆算している
- Loft/Sweep主体
- テーパ誤生成が構造的に起こる
- PartDesign生成ツリーを作れない
- コードが密結合で再利用困難

### 推奨戦略
- Phase A: 現行コード棚卸し
- Phase B: 再利用できる前処理だけ抽出
- Phase C: FreeCAD builder を新規実装
- Phase D: 旧出力系を段階廃止
