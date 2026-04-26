# OpenClaw TACO++ 完全自律版 統合ガイド

## 1. 統合方針
既存の OpenClaw Gateway / LiteLLM / Qdrant / Langfuse / n8n を壊さないため、TACO++は横置きサービスとして起動します。

## 2. 推奨接続点
- Gateway: terminal observation を LLM に渡す直前
- ingest_watchdog.py: Paperless/Docling/OCRログをRAG投入する直前
- workflow_healer.py: 同一コマンド反復時に保守モードへ戻す
- Langfuse: compression stats を event として記録

## 3. CAE用安全設定
絶対保持: ERROR, WARNING, divergence, contact fail, timestep collapse, NaN, negative volume, element distortion
圧縮可: iteration, progress meter, heartbeat, healthcheck, mesh listingの連続行

## 4. 本番採用判定
- 圧縮前後で critical 行数が減っていないこと
- エージェントが「全文が必要」と訴えた時に rollback できること
- Langfuse上で圧縮率・保護行数が見えること
