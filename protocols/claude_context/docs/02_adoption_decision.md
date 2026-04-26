# 02 Adoption Decision

## 導入判定

採用すべき条件:
1. 対象リポジトリが大きい、または複数サービス構成である。
2. Claude Code / Cursor / Codex CLI / Antigravity の探索ループが多い。
3. 同じコード理解を複数エージェントで共有したい。
4. 機密性のためローカル完結が望ましい。

見送り条件:
1. 小規模な単一アプリのみ。
2. IDE標準検索で十分。
3. Dockerリソースに余裕がない。
4. 現行RAG基盤の安定化が優先。

## OpenClawへの推奨判断

OpenClaw / Clawstack はサービス数が多く、Docker Compose、Portal、RAG、n8n、Langfuse、Paperless、CAE系コンテナなどが混在するため、Claude Context導入効果は高い。
ただし最初から本番Composeへ直結せず、overlay composeで試験導入する。
