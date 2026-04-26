# 01. セキュアAI実行基盤 設計書

## 1. 目的
Claude Code、OpenClaw、MCP、Codex、Antigravity等のAIエージェントを業務PCで使用する際、誤操作・マルウェア・情報漏洩・APIキー流出を防止する。

## 2. 基本アーキテクチャ

```text
Windows 11 Pro
  └─ WSL2 Ubuntu（Windows drive automount disabled / interop disabled）
       └─ Docker Engine / Docker Desktop WSL backend
            ├─ openclaw_gateway
            ├─ claude_code_runner
            ├─ codex_runner
            ├─ rag_qdrant
            ├─ paperless/docling
            └─ langfuse/observability
```

## 3. 防御層

| 層 | 防御内容 | 監査ポイント |
|---|---|---|
| Windows | 本体側の機密ファイルをAI実行領域から分離 | WindowsドライブをWSLに自動マウントしない |
| WSL2 | interop無効化、Windows PATH遮断 | `/etc/wsl.conf` の確認 |
| Linuxユーザー | root常用禁止、専用ユーザー利用 | `id claw` の確認 |
| Docker | コンテナ単位で役割分離 | `docker compose ps` |
| Secrets | `.env` を直接配布しない | 権限、readonly mount |
| Network | 必要通信のみ許可する方針 | 例外申請とログ |
| AI Policy | 危険操作禁止、HITL | PROMISES/TOOLS相当文書 |
| Evidence | 診断ログを定期保存 | `evidence/` に保管 |

## 4. 禁止事項
- Windows PowerShell上でAIエージェントに自律操作をさせない。
- `C:\Users\...` 直下をAIエージェントに直接読ませない。
- 顧客図面、IATF監査資料、APIキーをクラウドLLMに無制限送信しない。
- `docker.sock` をAIエージェントコンテナへ安易にマウントしない。
- `--privileged` コンテナを原則禁止する。

## 5. 例外運用
例外が必要な場合は `templates/exception_request.md` に記録し、期限・理由・対象データ・承認者・復旧方法を明確化する。
