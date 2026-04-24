# Codex CLI / Claude Code / Antigravity 向け 完全統合指示

あなたは OpenClaw 既存環境に Auto LP Generator を安全に統合するエージェントです。

## 絶対条件
- 既存Docker Compose、Portal、カード、APIを壊さない
- 既存ファイルを上書きする前に差分確認
- ポート衝突を確認
- 127.0.0.1 bindを維持
- APIキーやBearer Tokenをログに出さない
- 統合できない場合は「保留」とし、理由を報告

## 実施手順
1. ZIPを展開
2. README.mdとdocs/INTEGRATION_CHECKLIST.mdを読む
3. 既存 D:\Clawdbot_Docker_20260125\clawstack_v2 の構成を確認
4. ポート8010が空いているか確認
5. 単独起動: docker compose up -d --build
6. scripts\healthcheck.bat
7. Portalカードを既存Portalへコピー
8. 既存カード一覧へ追加
9. 動作確認
10. integration_report.md を出力

## 採用判断
- 完全採用: 既存環境と衝突なし、Portalから起動可
- 部分採用: APIのみ、Portalカード保留
- 保留: ポート衝突、認証未整備、既存カード衝突など
