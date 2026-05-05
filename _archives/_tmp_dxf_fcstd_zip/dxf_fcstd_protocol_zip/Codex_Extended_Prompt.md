# Codex 追加強化指示
追加要件:
- Spreadsheet を使って主要寸法をパラメータ化する
- feature_map.json に各Featureの由来ビューと根拠を書き出す
- 断面比較により不要テーパを自動検出する
- 深さ不明のザグリは候補スケッチだけ生成して report に保留出力する
- config で front/right/top の bbox を与えられるようにする
- DXF中の TEXT/MTEXT から φ, depth, c'bore, thru をパターン抽出する
- 既存の DXF → STEP コードを調査し、再利用可能部分と置換対象を分類する
- 既存コードをいきなり削除せず、棚卸しレポートを先に出す
- 再利用可能なら parser / cleaner / report / config を流用する
- PartDesign生成ツリーに不向きな既存 builder は新規実装に切り替える
