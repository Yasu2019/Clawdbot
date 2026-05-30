# アーキテクチャ

```text
User / Portal
  -> OpenClaw / Hermes Agent
      -> Hermes Bridge API
          -> Safety Harness
          -> QA Memory
          -> MCP tool endpoints
      -> Ollama local model
      -> Qdrant / PostgreSQL
```

## 採用判断

採用価値が高い条件:

- HermesがOpenClaw既存機能と衝突しない
- Ollamaローカルモデルで十分な応答が得られる
- Safety Harnessを全コマンド実行前に通せる
- メモリ保存先が専用workspaceに限定される

採用を保留する条件:

- Hermesが本番Docker volumeへ直接アクセスする
- 外部LLMへ機密情報を送る設計が残る
- 自律実行ログが残らない
- Portalから停止・隔離できない
