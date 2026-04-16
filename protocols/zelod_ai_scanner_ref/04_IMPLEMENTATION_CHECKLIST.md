# 実装チェックリスト

## A. 事前確認
- [ ] 既存 Docker Compose 一式をバックアップした
- [ ] ポート競合確認をした
- [ ] 既存 Portal card / route / nginx 配信物との競合確認をした
- [ ] 認証情報の格納先を確認した
- [ ] 本番と検証を分離した

## B. 対象の棚卸し
- [ ] Chat endpoint
- [ ] Agent endpoint
- [ ] Tool execution endpoint
- [ ] RAG retrieval path
- [ ] Ingestion path
- [ ] Workflow trigger path
- [ ] Admin / debug endpoint
- [ ] Memory write path

## C. スキャン観点
- [ ] Prompt Injection
- [ ] Jailbreak
- [ ] Sensitive data extraction
- [ ] Cross-tenant / cross-context leakage
- [ ] Tool abuse
- [ ] Unsafe external call
- [ ] Prompt override
- [ ] Hidden instruction reveal

## D. ガード実装
- [ ] 入力フィルタ
- [ ] 出力フィルタ
- [ ] ツール実行権限分離
- [ ] 外部送信 allowlist
- [ ] 高リスク操作 dry-run
- [ ] 監査ログ
- [ ] 失敗時の fail-closed ルール
- [ ] RAG 機密フィルタ

## E. 運用
- [ ] 定期スキャンスケジュール
- [ ] CI/CD 組み込み可否確認
- [ ] レポート保存先
- [ ] 再現性のある試験データ
- [ ] ロールバック手順
- [ ] アラート条件
