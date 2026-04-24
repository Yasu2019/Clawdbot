# 目標構成

```text
[Portal / OpenClaw]
        |
        v
[Paperclip control plane]
   |        |         |
   |        |         +--> Governance / budget / org chart / goal alignment
   |        +------------> Agent heartbeat scheduling
   +---------------------> Task / company / delegation control

[Claude Code] [Codex CLI] [Antigravity] [Cursor/OpenHands(optional)]
        \        |        /
         \       |       /
             [LiteLLM]
                |
      +---------+---------+
      |                   |
   [Cloud LLMs]       [Ollama local]

[Langfuse] <--- traces/usage --- [OpenClaw / LiteLLM / n8n]
[Qdrant]   <--- memory / RAG ---- [OpenClaw / ingest pipelines]
[n8n]      <--- events / alerts -- [Paperclip / OpenClaw / infra]
```

## ポイント
- Paperclip は RAG の本体ではない
- Paperclip はコントロールプレーンとして扱う
- OpenClaw を「社員」、Paperclip を「会社」として扱う
- 既存の観測基盤は Langfuse を継続利用

## 通信方針
- 可能な限り 127.0.0.1 に限定
- 外部公開は原則しない
- モバイルや外出先アクセスが必要な場合のみ Tailscale 等の別経路を検討
