# 03 Install Steps

## 1. ZIPを展開

例:
D:\OpenClaw_ClaudeContext_Protocol

## 2. 事前確認

PowerShell:
```powershell
cd D:\OpenClaw_ClaudeContext_Protocol
powershell -ExecutionPolicy Bypass -File .\scripts\00_preflight_windows.ps1
```

## 3. Milvus overlay起動

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\01_start_milvus_overlay.ps1
```

## 4. Ollama埋め込みモデル準備

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\02_prepare_ollama_embeddings.ps1
```

## 5. MCP設定

Claude Code / Cursor / Claude Desktop等のMCP設定へ configs/*.example.json を参考に追加する。

## 6. インデックス作成

Claude CodeまたはMCP対応エージェントから、対象リポジトリを index_codebase する。
対象例:
D:\Clawdbot_Docker_20260125

## 7. 検索テスト

検索例:
- OpenClaw Gatewayの認証処理はどこか
- Portal card一覧はどこで定義されているか
- n8n self healerの実装箇所
- Paperless ingest watchdogの処理フロー
