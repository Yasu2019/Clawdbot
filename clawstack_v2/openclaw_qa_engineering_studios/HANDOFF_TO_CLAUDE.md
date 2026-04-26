# HANDOFF_TO_CLAUDE.md

## Claude Codeへの依頼

OpenClaw QA Engineering Studios を読み込み、QA/IATF/CAE/RAG/Portal/Docker の各役割エージェント設計として妥当性をレビューしてください。

## レビュー観点

1. 役割分担が過剰でないか
2. OpenClaw既存構成と矛盾しないか
3. 安全制約が不足していないか
4. Codex / Antigravity に渡せる粒度か
5. ACT.md による再開性が十分か

## 禁止事項

- 既存コードを無断で大規模リファクタしない
- SQL書き込み処理を提案しない
- APIキーやBearer tokenの記載を求めない
