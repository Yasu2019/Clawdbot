# 実装メモ

## 推奨初期パラメータ
- heartbeat: 60 / 120 / 180 秒の3段階
- budget: 小さく開始
- multi-company: まずは 1 company のみ

## 先にやらないもの
- 全エージェント常時稼働
- いきなり外部公開
- 既存チケットシステム完全連携
- 本番 DB 直結

## 将来拡張
- Postgres 外部化
- n8n 経由のアラート自動化
- Langfuse 連携強化
- Tailscale 経由の限定リモートアクセス
