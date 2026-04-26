# HANDOFF_TO_ANTIGRAVITY.md

## Antigravityへの依頼

OpenClaw Gateway / Portal / Docker Compose / RAG関連の統合候補として、このテンプレートを検査してください。

## 判断してほしいこと

- 完全採用できるか
- 部分採用にすべきか
- 既存構成と衝突するため保留すべきか

## 実施手順

1. README.md を読む
2. ACT.md を読む
3. 既存 compose / Portal / apps ディレクトリを確認
4. scripts/run_review.py を実行
5. 変更前に差分とリスクを出す
6. 採用判断を DECISIONS.md に追記

## 安全制約

ユーザー承認なしで次を行わないこと。

- 既存DBへの書き込み
- 認証情報の変更
- 既存サービスの削除
- 外部公開ポートの追加
