# 02 OpenCode GO 現時点メモ

2026-04時点の公開情報確認メモ。

- OpenCode公式Docsでは、OpenCode GoはOpenCodeのプロバイダーとして扱われ、`/connect` で接続し、`/models` で利用可能モデルを確認する流れ。
- 公式Docs上のモデル例には、GLM-5/5.1、Kimi K2.5/2.6、MiMo、MiniMax、Qwen3.5/3.6 Plus、DeepSeek V4 Pro/Flashなどが掲載されている。
- 公式Docsでは、利用制限はリクエスト数固定ではなく、5時間・週・月ごとのドル換算利用枠として説明されている。
- モデル一覧や制限は変更される前提で、導入スクリプトにモデル名を固定しすぎないこと。

## 実務注意
- API base URLやモデルIDは、必ず契約後のOpenCode画面・公式Docs・実際の `/models` で確認する。
- サードパーティ記事の料金・モデル一覧は変動前提。
