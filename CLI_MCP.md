# Clawstack / OpenClaw における CLI化・MCP化 仕分けプロトコル

あなたは、ローカルAI基盤・LLMOps・Agent Tooling 設計に強いシステムアーキテクトです。  
以下の前提に基づき、Clawstack / OpenClaw の各機能・操作について、

- CLI化すべきもの
- MCP化すべきもの
- CLIとMCPの両対応が望ましいもの
- 現時点では対象外でよいもの

を整理した **仕分け表** を作成してください。

## 目的

目的は、Clawstack / OpenClaw のツール設計を整理し、  
AIエージェントにとって扱いやすく、かつ人間にも保守しやすい構成へ寄せることです。

特に以下を重視してください。

- OpenClaw が扱いやすいこと
- 人間が再現・デバッグしやすいこと
- ローカル完結・秘密保持を守れること
- Langfuse 等で可観測性を持たせやすいこと
- 将来的に他クライアントから再利用しやすいこと
- 何でもMCP化しすぎて複雑化しないこと

## 現在の前提構成

- Windows 11 + Docker Desktop (WSL2)
- GMKtec NucBox K10
- Intel Core i9-13900HK
- RAM 48GB
- OpenClaw がメインAIエージェント
- LiteLLM, Langfuse, Qdrant, Infinity, Paperless, Docling, n8n, SearXNG を利用
- 既存 MCP として:
  - clawstack-tools
  - n8n-workflows
- OpenClaw は Browser 操作、exec 実行、RAG検索、workflow実行、観測確認などを行う
- ローカルファースト / プライバシー優先
- 破壊的変更は避けたい
- 可観測性は Langfuse を主軸にしている

## 仕分けの判断基準

以下の観点で、CLI化 / MCP化 / 両対応 / 対象外 を判断してください。

### CLI化が向いているもの
- 人間が直接叩いて再現確認したい
- bash / PowerShell / Python / curl で単独実行しやすい
- ログ確認やデバッグが重要
- OpenClaw 以外に再利用需要が少ない
- ローカル運用・保守作業に近い
- 引数と出力が明快
- 安全に dry-run や差分確認を入れやすい

### MCP化が向いているもの
- 複数エージェント/複数クライアントから再利用したい
- ツールとして意味が安定している
- JSON入出力に向いている
- エージェントが自然言語から呼び出しやすい
- 実行権限や用途を限定しやすい
- UIやクライアントが変わっても再利用価値が高い

### 両対応が向いているもの
- 人間もエージェントも使いたい
- まずCLIを真実源として持ち、そのラッパーとしてMCPを載せると良い
- デバッグはCLI、普段利用はMCP、という役割分担が有効

### 対象外でよいもの
- 今MCP化してもメリットが薄い
- CLI化しても価値が薄い
- 内部実装のままでよい
- まずは設計整理の対象にしなくてよい

## 仕分け対象候補

以下の機能群を対象に、必要なら追加提案もしてください。

### A. RAG / 文書系
- rag_search
- 文書の再インジェスト
- Docling変換
- Paperless文書取得
- chunk再生成
- embedding再作成
- Qdrant snapshot
- Qdrant collection health check

### B. Web / 検索系
- web_search
- SearXNG health check
- 検索結果キャッシュ削除

### C. n8n / workflow系
- workflow検索
- workflow実行
- workflow詳細取得
- workflow export / backup
- workflow health check
- self-healer 実行
- self-healer dry-run

### D. OpenClaw / 運用系
- OpenClaw health check
- Browser action 実行
- exec command 実行
- request_id付き trace 照会
- recent failed traces 取得
- fallback率確認
- harness block 件数確認

### E. データ保全 / バックアップ系
- PostgreSQL backup
- ClickHouse backup
- MinIO backup
- Qdrant snapshot / restore
- ingest state backup

### F. モデル / 推論系
- 日→英クエリ翻訳
- モデル疎通確認
- Ollama target 確認
- embedding service health check
- Gemini fallback test

### G. Portal / 観測UI系
- Observability Hub API
- KPI集計
- 改善候補要約生成
- 今日のハイライト生成

## 出力してほしいもの

以下の順で出力してください。

### 1. 全体方針
- Clawstack / OpenClaw では、CLIを主軸にすべきか、MCPを主軸にすべきか
- それとも「CLIを真実源、MCPをラッパー」とすべきか
- その理由

### 2. 仕分け表
次の列を持つ表で整理してください。

- 機能名
- 推奨分類
  - CLI
  - MCP
  - 両対応
  - 対象外
- 理由
- 実装優先度
  - 高
  - 中
  - 低
- 備考

### 3. 優先実装トップ10
- まず着手すべき上位10件
- 1件ごとに短い理由

### 4. 設計原則
今後 Clawstack で新機能を追加する際に、
「CLIにすべきか」「MCPにすべきか」を判断するためのルールを
5〜8個程度で提案してください。

### 5. 推奨アーキテクチャ
- どこまでを CLI 層
- どこからを MCP 層
- どこを OpenClaw 直結
- どこを Portal API 層
に分けるべきか、簡潔に整理してください。

## 制約

- 大規模な全面刷新は提案しない
- 既存の clawstack-tools / n8n-workflows MCP は活かす前提
- 破壊的変更は禁止
- ローカルファーストを崩さない
- 秘密情報の外部送信は禁止
- 「MCPを増やせばよい」という結論にはしない
- 人間による再現性・保守性を重視する
- OpenClaw の運用を複雑化しすぎない

## 特に重視してほしい結論

私は、MCPを増やしすぎるよりも、
「CLIをしっかり整備し、その中で再利用価値の高いものだけMCPラップする」
構成がよいのではないかと考えています。

この仮説が妥当かどうかも含めて評価してください。
必要なら、Clawstack向けの現実的な折衷案を出してください。