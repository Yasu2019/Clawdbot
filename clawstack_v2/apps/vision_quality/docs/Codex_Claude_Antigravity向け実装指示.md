# Codex / Claude / Antigravity 向け実装指示

## 最重要

既存のOpenClaw / Portal / Docker Compose / Node-RED構成を壊さないこと。

## 禁止

- 既存docker-compose.ymlを直接大改造しない
- 既存Portalカードを削除しない
- 既存ポートを勝手に変更しない
- Gitバックアップなしで大規模変更しない
- APIキーをコミットしない
- 顧客図面や検査画像を外部APIへ送信しない

## 作業前

```bash
git status
git add .
git commit -m "backup before vision quality integration"
```

## 推奨実装順

1. このZIPを modules/vision_quality に配置
2. docker-compose.vision.yml 単独起動
3. health確認
4. Portalカード追加
5. Node-REDフロー追加
6. OpenClaw GatewayからAPI呼び出し
7. 監査ログCSV出力
8. RAG連携
9. AnomalibまたはVLM連携

## 採用可否判断

- 既存構成と競合しないなら採用
- ポート競合があれば.envのみ変更
- 既存アプリに影響が出る変更は不可
