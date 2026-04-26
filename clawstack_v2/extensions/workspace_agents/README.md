# OpenClaw × Workspace Agents 本番完全版（自律運用プロトコル）

このZIPは、OpenClaw/Clawstack環境に「Workspace Agents型」の自律QAエージェント群を統合するための現場投入プロトコルです。

## 目的
- QA不良率分析の自動化
- IATF 16949内部監査資料の自動生成
- CSV監視による異常検知
- OpenClaw RAG連携
- n8n通知・承認フロー連携
- Image2/画像生成系AIを使った教育資料・監査資料作成
- Codex CLI / Claude Code / Antigravity に渡して自律実装させる

## 最重要安全ルール
1. SQL Server/社内DBは必ずREAD ONLY接続。
2. UPDATE / DELETE / INSERT / MERGE / DROP / ALTER / TRUNCATE / EXEC は禁止。
3. 外部送信はHITL承認後のみ。
4. OpenClaw既存compose、既存Portalカード、既存ポートを必ず調査してから統合。
5. 既存ファイルは上書きせず、patch/backup方式で差分適用。
6. 認証情報・Bearer Token・DBパスワードはZIP内に直接書かない。

## 推奨配置
D:\Clawdbot_Docker_20260125\clawstack_v2\extensions\workspace_agents

## 主な内容
- `prompts/` Codex / Claude / Antigravity投入用プロンプト
- `agents/` 各Agent仕様YAML
- `api/` FastAPI実装骨格
- `n8n/` 承認付き自動化フロー雛形
- `openclaw/` OpenClaw連携設定
- `portal_card/` Portalカード雛形
- `sql/` READ ONLY SQLテンプレート
- `docs/` 運用設計・安全設計・導入手順

## 初回実行イメージ
```powershell
cd D:\Clawdbot_Docker_20260125\clawstack_v2
mkdir extensions\workspace_agents
# ZIP展開後
powershell -ExecutionPolicy Bypass -File .\extensions\workspace_agents\scripts\preflight_check.ps1
```

## 注意
このZIPは「実装させるための本番プロトコル」です。実運用前に、必ず社内DB接続、通知先、監査対象文書、RAGコレクション名を確認してください。
