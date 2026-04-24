# 推奨役割分担表

| Agent | 主担当 | 禁止/制限 | 備考 |
|---|---|---|---|
| OpenClaw | 日常実行、社内業務導線、RAG活用 | 単独で全体統治しない | 既存主系統 |
| Claude Code | 設計、レビュー、仕様整合 | 本番削除は承認必須 | 長文設計に強い |
| Codex CLI | 実装、パッチ、コード生成 | protected branch pushは承認必須 | 実装担当 |
| Antigravity | 調査、案出し、試作 | 本番更新しない | コスト分散先 |
| Cursor/OpenHands | 必要時のみ補助 | 主系統化しない | 任意 |

## 推奨委譲ルール
- 設計書 → Claude Code
- 実装 → Codex CLI
- 比較調査 → Antigravity
- 文脈/RAG依存業務 → OpenClaw

## 予算優先順位
1. OpenClaw
2. Codex CLI
3. Claude Code
4. Antigravity
