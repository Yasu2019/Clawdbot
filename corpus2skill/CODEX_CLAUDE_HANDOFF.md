# Codex / Claude / OpenCode GO 引き継ぎ指示書

## 依頼目的
このZIPは、既存の clawstack-unified に Corpus2Skill 型の構造探索RAGを追加するための本番設計テンプレートです。

## 最初にやること
1. 既存リポジトリをGitでバックアップする
2. 既存docker-compose.yml、Portal構成、OpenClaw Gateway構成を読む
3. このZIPの構成を既存環境に合わせて差分適用する
4. 直接上書きせず、まず `corpus2skill/` 配下に展開する
5. compose override で起動確認する

## 絶対ルール
- 既存Portalカードを削除・改名しない
- 既存OpenClaw Gatewayを直接破壊しない
- Qdrant既存コレクションを削除しない
- Paperless原本を改変しない
- Langfuse設定を上書きしない
- 大規模修正前は必ずGitHubへpushまたはローカルcommitする

## 採用判断
既存環境と競合する場合は、Codex/Claude側で以下を判断してください。

- 既存機能に統合すべきか
- 新規Portalカードとして分離すべきか
- API Gatewayにルート追加するか
- n8n経由にするか
- Node-RED経由にするか

## 本番化に必要な追加実装
- Paperless API連携
- Qdrant hybrid search連携
- tree store永続化(SQLite/Postgres/JSONLのいずれか)
- Langfuse trace送信
- OllamaローカルLLMによる階層要約
- 人間確認済みフラグUI
- Evidence Viewer

## 優先順位
1. Shadow modeでIATF文書だけ処理
2. QC工程表を追加
3. 図面PDFを追加
4. STEP/3Dモデルメタ情報を追加
5. 不具合解析ログを追加
6. Portalで横断探索

