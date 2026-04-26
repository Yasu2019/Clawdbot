# ZELOD IN AI Scanner 導入マスタープロトコル

## 1. 目的
Mozilla系AI脆弱性スキャナの思想を、既存のローカルAI環境に取り込み、
従来のWAFや通常のAPI監視では見落としやすい以下のリスクを継続的に試験可能にする。

- Prompt Injection
- Jailbreak
- Training / Context Data Extraction
- Tool Misuse
- Unsafe Workflow Invocation
- RAG 経由の機密漏洩

## 2. 対象環境（想定）
- OpenClaw
- n8n
- Qdrant / RAG
- LiteLLM / Ollama / ローカルLLM
- Portal / 各種ローカルアプリ
- Langfuse 等の観測基盤

## 3. 受け取り側AIへの必須指示
あなたは導入エージェントである。
以下を必ず実施すること。

1. 既存構成との衝突確認
2. 新規導入が妥当か、部分採用が妥当か、保留が妥当かを三択で判断
3. 理由を具体的に記載
4. 既存 Docker Compose, Portal card, route, env, volume, port と競合しないようにする
5. セキュリティテスト対象エンドポイントを棚卸し
6. AI特有の脅威モデルを作成
7. 最小実装（MVP）と本格実装（Production候補）の二段階案を作成
8. 導入しない場合も、代替案を提示する
9. 既存コードを破壊しない差分提案を優先する
10. 機密情報やトークンはハードコードしない

## 4. 優先してテストすべき経路
1. Chat / Agent endpoint
2. Tool execution endpoint
3. RAG retrieval endpoint
4. n8n workflow trigger
5. File ingestion path
6. Prompt template merge path
7. Admin / debug endpoint
8. Memory write path

## 5. 最低限の評価観点
- 既存システムへ簡単に差し込めるか
- 手動運用ではなく継続試験に向くか
- CI/CD か定期バッチへ組み込みやすいか
- 出力が既存運用に接続しやすいか
- MITRE ATLAS / OWASP LLM Top 10 との対応付けがしやすいか
- 結果を Langfuse / ログ基盤へ流し込めるか

## 6. 推奨ガードレイヤ
ユーザー入力
  ↓
[入力検査]
  ↓
[プロンプト組み立て]
  ↓
[LLM]
  ↓
[出力検査]
  ↓
[ツール実行制御]
  ↓
[監査ログ / 可観測化]

## 7. 必須ルール
- 「プロンプトで防ぐ」だけに依存しない
- ツール実行権限を分離する
- 外部送信系ツールは allowlist 制御する
- 高リスク操作は dry-run を標準化する
- RAG の取得結果に機密フィルタをかける
- スキャン結果を人がレビュー可能な形式で残す

## 8. 納品物の最低要件
受け取り側AIは最終的に以下を返すこと。
- 採用判断（採用 / 部分採用 / 保留）
- 現在構成との衝突一覧
- 追加コンテナ or 追加スクリプト案
- テストケース一覧
- ロールバック手順
- 本番適用前チェック項目
