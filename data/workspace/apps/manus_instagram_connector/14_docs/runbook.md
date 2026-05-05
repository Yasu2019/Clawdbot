# 運用Runbook

## 目的

Manus × InstagramをOpenClaw運用に取り込む際の安全な手順。

## Step 1: ZIP確認

Claude/Codexに以下を確認させる。

- README
- 00_CLAUDE_README_FIRST
- scripts
- configs
- safety
- decision

## Step 2: 読み取り専用監査

PowerShell:

```powershell
cd <ZIP展開先>
powershell -ExecutionPolicy Bypass -File .\10_scripts\audit_clawstack_readonly.ps1
```

Python:

```bash
python 10_scripts/collect_env_readonly.py
```

## Step 3: 静的安全確認

```bash
python 10_scripts/safe_run_checklist.py .
```

## Step 4: オフライン試験

```bash
python 10_scripts/generate_content_calendar.py
python 10_scripts/validate_post_text.py sample_post.txt
python 10_scripts/build_weekly_report.py 11_templates/insights_sample.csv
```

## Step 5: Manus手動試験

- Manusに競合分析プロンプトを投入
- 結果をOpenClawテンプレに貼る
- 投稿前レビューを行う
- 投稿はまだしない

## Step 6: Instagram連携確認

- Instagram Professional Accountか確認
- Connector権限を確認
- テスト投稿は人間承認後のみ
- 投稿ログを残す

## Step 7: 本格運用

- 週5投稿まで
- 週次レポート
- 月次で収益導線見直し
- クレジット消費確認
- 規約変更確認

