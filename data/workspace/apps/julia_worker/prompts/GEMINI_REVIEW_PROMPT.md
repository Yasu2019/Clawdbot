# Gemini Review Prompt

ClawstackにJulia Numerical Workerを追加する構成をレビューしてください。
特に、既存Docker構成・Portalカード・Node-RED連携との衝突を確認してください。

## 重点確認

- compose network名の不一致
- 8096/8097の衝突
- PortalからのCORS/API_BASE問題
- OpenClaw Tool登録時のURL問題
- Windows/WSLパス問題
- 初回Julia precompileによる遅延
- 簡易推定モデルの誤用リスク

## 期待出力

- 実装前に直すべき点
- 実装後の確認コマンド
- 現場投入前の注意点
