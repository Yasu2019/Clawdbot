# Mail Todo Extract

## Purpose
- メールから ToDo、期限、担当、添付確認、返信要否を抽出する。

## Data Source Priority
1. `email_search_query.py tasks-context`
2. `email_search_query.py context`
3. 元メール本文

## Procedure
1. 依頼事項と参考情報を分離する。
2. 期限を抽出し、曖昧なら `期限不明` とする。
3. 担当候補は推定しすぎず、根拠文を残す。
4. 添付があれば確認タスクを作る。
5. 顧客メールは返信要否を必ず判定する。
6. 社内メールは転記先、依頼先候補も補助情報として残す。

## Output Template
```markdown
# Mail Todo Extract

## Summary
- 要旨:

## Action Items
- [ ] 項目
  - 担当候補:
  - 期限:
  - 根拠文:
  - 緊急度:

## Reply Needed
- 要否:
- 相手:
- 返信期限:
- 返信で触れるべき点:

## Attachments to Check
- ファイル名:
- 確認観点:

## Classification
- 顧客要求 / 社内依頼 / 調査依頼 / 共有 / 保留

## Risks / Notes
- クレーム化リスク:
- 誤解リスク:
- 不明点:
- 保留理由:
```

## Rules
- 依頼と参考情報を分離する。
- 期限不明は `期限不明` と明記する。
- 担当は推定しすぎない。
- 添付があれば必ず確認タスク化する。
- 顧客メールは返信要否を必須判定する。
- 社内メールは転記先、依頼先候補も補助情報として抽出する。

## Integration Notes
- Telegram / OpenClaw で期限や未回答を聞かれたら、先に `tasks-context` を使う。
- 検索コマンド:
  `python3 /home/node/clawd/email_search_query.py tasks-context "<user request>" --limit 5`
- 元メール本文が必要な場合だけ `context` 側へ落とす。
