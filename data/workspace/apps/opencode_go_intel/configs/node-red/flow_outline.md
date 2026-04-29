# Node-RED Flow Outline

1. Inject: 定期実行または手動実行
2. HTTP Request/RSS: 公開情報取得
3. Function: 機密・個人情報マスク
4. HTTP Request: LiteLLM `/chat/completions` に送信
5. Function: 有益性スコアをJSON化
6. Switch: 採用候補 / 保留 / 不採用
7. File/Paperless/GitHub: レポート保存
8. Dashboard/Portal: 結果表示

本番では、Node-RED credentialにAPIキーを保存し、flow JSONへ直書きしない。
