# 03. Learning Engine 仕様

## 3.1 役割
learning_engine は以下を担当する。
- 取込正規化
- 埋め込み
- Qdrant保存
- 類似検索
- LLM比較
- judgement保存
- feedback反映
- Langfuse送信

## 3.2 主要エンドポイント
- `GET /health`
- `POST /ingest/case`
- `POST /ingest/email-message`
- `POST /ingest/email-thread`
- `POST /ingest/quality-issue`
- `POST /ingest/improvement-activity`
- `POST /ingest/cae-run`
- `POST /compare/case`
- `POST /compare/email-thread`
- `POST /compare/cae-run`
- `POST /feedback/judgement`
- `POST /search/memory`

## 3.3 推奨判断モデル
- 主比較: `google/gemini-2.5-flash`
- ローカル補助: `ollama_chat/qwen2.5-coder:7b`
- 将来的にコード/CAEログ解析だけローカル優先でも可

## 3.4 基本処理
1. 入力を正規化
2. 構造化事実を抽出
3. 埋め込み生成
4. 専用コレクションへ保存
5. 比較時は関連コレクションを横断検索
6. LLMで「共通点 / 相違点 / 想定主因 / 再発リスク / 推奨アクション」を生成
7. judgement保存
8. 人レビューで更新

## 3.5 設計原則
- 既存 compose への影響最小
- ポート競合回避
- Qdrant / LiteLLM / Langfuse を内部URLで呼ぶ
- n8n が主オーケストレータ
