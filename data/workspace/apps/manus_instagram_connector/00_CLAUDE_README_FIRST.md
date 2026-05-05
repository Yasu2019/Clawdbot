# Claudeへ：最初に読む指示

あなたは、ユーザーのミニパソコン上の既存OpenClaw/Clawstack V2環境を最も理解している前提で、このZIPを評価してください。  
このZIPの目的は、Manus Instagram Connectorを使ったSNS運用・収益化パイプラインを、既存環境に安全に統合できるか判断することです。

## まず行うこと

1. ZIP内の全ファイルを一覧化する。
2. 実行スクリプトを開いて、破壊的操作がないか確認する。
3. Docker、DB、Portal、既存アプリ、ポート、volume、認証情報の競合を確認する。
4. 何も変更せず、まず「採用判断レポート」を作成する。
5. 採用する場合も、いきなり本番連携しない。必ずDry-runから始める。

## 絶対禁止

- docker volume rm
- docker compose down -v
- rm -rf
- del /s /q
- rmdir /s /q
- DROP / DELETE / UPDATE / INSERT / TRUNCATE
- 既存.envの上書き
- 認証情報やAPIキーのログ出力
- Instagramへの無承認投稿
- 非公式スクレイピング
- ブラウザログインの自動突破
- 規約違反のDM自動化
- 誇大広告・ステマ・虚偽収益表現の投稿

## あなたが決めること

次のいずれかで判断してください。

- A: 採用してよい
- B: 部分採用
- C: 保留
- D: 却下
- E: 追加調査後に再評価

判断結果は `12_decision/final_decision_report_template.md` の形式で残してください。

## 推奨初期判断

初回は原則として「B: 部分採用」を推奨します。  
理由は、Manus Instagram Connectorがベータ版であり、Instagram側の仕様・権限・料金・API制限が変わりやすいためです。

