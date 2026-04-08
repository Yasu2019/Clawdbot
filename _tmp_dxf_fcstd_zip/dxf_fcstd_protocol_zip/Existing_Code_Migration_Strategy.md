# 既存 DXF→STEP アプリの扱い方針
## 結論
既存コードは、いきなり削除しない。
まず棚卸しし、再利用可能部品と置換対象を切り分ける。

## 1. 先に見るべきもの
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

## 2. 融合が向くケース
- DXFパーサが安定している
- bbox設定やレイヤ除外機能が既にある
- report / log 基盤がある
- Docker 起動ルールや入出力規約が整っている
- エンティティ正規化やループ抽出が部品化しやすい

## 3. 置換が向くケース
- メッシュから逆算している
- Loft / Sweep 主体
- テーパ誤生成が構造的に起こる
- PartDesign の生成ツリーを作れない
- FCStd を編集可能な履歴付きで出せない
- コードが密結合でテスト不能

## 4. 推奨戦略
### Phase A
現行コード棚卸し
- 現行構成図
- 再利用可能モジュール一覧
- 危険モジュール一覧
- 削除候補一覧

### Phase B
前処理のみ再利用
- DXF parser
- cleaner
- bbox config
- logging
- report

### Phase C
FreeCAD builder 新規実装
- Sketch_BaseProfile
- Pad_Base
- Hole
- Pocket
- validators
- feature_map

### Phase D
旧 builder 段階廃止
- STEP直出し専用 builder は残すか互換層化
- メッシュ依存 builder は廃止候補

## 5. Codexへの指示
- 旧実装を先に読んで責務を一覧化
- 再利用部位は流用
- Builder系はゼロベースでもよい
- 既存CLI互換が必要なら adapter を作る
