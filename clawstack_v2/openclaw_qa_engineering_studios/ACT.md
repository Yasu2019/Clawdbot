# ACT.md - OpenClaw 作業記憶

## 現在の目的

Claude Code Game Studios の考え方を、OpenClaw向けの品質保証・CAE・RAG・Portal・Docker運用テンプレートへ変換する。

## 現在の状態

- 初期テンプレート生成済み
- 既存OpenClaw環境への実配置は未実施
- 既存Compose / Portalカード / ポート一覧との衝突確認は未実施

## 次に行うこと

1. `install_into_openclaw.ps1` を使う前に、配置先パスを確認する
2. 既存 `PORTAL_APPS.md` と `docker-compose*.yml` を確認する
3. `scripts/run_review.py --mode full` を実行する
4. 問題がなければ OpenClaw Gateway から参照できる位置へ配置する

## 最終チェックポイント

- [ ] SQL読み取り専用制約を確認
- [ ] Portalカード重複を確認
- [ ] Dockerポート衝突を確認
- [ ] 機密情報漏洩チェックを実施
- [ ] ACT.md / DECISIONS.md / RISKS.md を更新

## 作業ログ

- 2026-04-25: 初期ZIPテンプレート生成。
