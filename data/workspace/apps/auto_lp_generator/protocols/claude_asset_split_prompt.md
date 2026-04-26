# Claude 用 素材分割プロンプト

添付したグリッド画像から、各UI素材を個別PNGとして切り出してください。

要件:
- 背景を透過
- ファイル名は英数字
- assets_manifest.json を作成
- 余白を最小化
- アイコン、背景図形、KPIカード装飾を分離
- Webで使いやすいサイズに調整

出力:
- assets/*.png
- assets_manifest.json
- 切り出し失敗がある場合は理由を明記
