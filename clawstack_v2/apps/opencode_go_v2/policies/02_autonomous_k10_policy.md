# K10 自律ノウハウ蓄積ポリシー

## 許可する自律活動
- 公開Web情報の収集
- YouTube、GitHub、公式Docsの調査
- AI、CAE、DOE、金型、樹脂成形、プレス、ゲーム開発のノウハウ収集
- 有益性スコアリング、重複確認、タグ付け、ローカルDB登録
- 改善候補リスト作成、Portalでの提案表示

## 禁止する自律活動
- 本番システムの自動変更
- Docker Composeの勝手な変更
- Git push、ファイル削除
- Gmail読取
- 社内文書、図面、STEP、DXF、PDF図面、Paperless NGX原文の外部送信

## 自律モード
- Observe: 調査のみ
- Learn: 調査、要約、有益性判定、DB登録
- Propose: 改善提案まで
- Implement-Dev: dev環境のみ。ユーザー明示指示時のみ

標準は Learn。システム変更を伴う場合は Propose まで。
