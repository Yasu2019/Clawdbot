# 03_CODEX_PROTOCOL_ja

## 目的
Codex系エージェントに対し、防御目的・ローカル限定・要承認の脆弱性診断フローを渡すためのプロトコルです。

## 貼り付け用プロトコル
```text
Task: Assist with a local, defensive vulnerability review workflow.

Operating constraints:
- Authorized targets only
- Local repositories and approved test hosts only
- No destructive commands
- No credential rotation, deletion, restart, or write operations without explicit approval
- No external exfiltration of code, configs, logs, or secrets
- All exploitability claims must be verified safely in a sandbox or test clone
- Prefer read-only analysis and structured outputs

Workflow:
1. Inventory files and rank likely security-sensitive areas
2. Correlate with static scan results
3. Generate hypothesis list
4. Propose minimal safe reproduction steps
5. Draft fixes
6. Produce a remediation report

Output schema for each issue:
- id
- title
- severity
- confidence
- evidence
- repro_status
- fix_summary
- file_refs
```

## 推奨運用
- まず Git ブランチを切る
- AI の提案修正は差分レビュー必須
- 本番反映前に検証ログを添付
