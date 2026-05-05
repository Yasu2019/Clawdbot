# 実装タスク表
## Stage 0: 調査
- [ ] FreeCAD 実行コマンド確認
- [ ] freecadcmd / python import FreeCAD 確認
- [ ] ezdxf 使用可否確認
- [ ] 既存 DXF→STEP アプリ棚卸し
- [ ] 再利用可能部位の一覧化

## Stage 1: 最小PoC
- [ ] semi-auto config で front/right/top bbox 指定
- [ ] 1つのベース閉ループを取得
- [ ] Sketch_BaseProfile 作成
- [ ] Pad_Base 作成
- [ ] 単純な円穴を Hole で作成
- [ ] FCStd 保存
- [ ] STEP/STL 出力
- [ ] report.md 出力

## Stage 2: 安定化
- [ ] loop detector 改良
- [ ] annotation parser 実装
- [ ] Pocket 対応
- [ ] ザグリ候補認識
- [ ] Hole counterbore 対応
- [ ] feature_map.json 出力
- [ ] process.log 出力
- [ ] エラー時中間成果物保存

## Stage 3: 品質強化
- [ ] 不要テーパ検出
- [ ] 単一Body検証
- [ ] Spreadsheet パラメータ化
- [ ] 断面比較検証
- [ ] PNGプレビュー出力
- [ ] README 整備
- [ ] テスト作成

## 受入条件
- [ ] FCStd が GUI で開ける
- [ ] Feature 名が意味的
- [ ] Pad/Hole/Pocket が履歴にある
- [ ] ザグリ不明時は保留化される
- [ ] 不要テーパがない
- [ ] report に未確定点が出る
