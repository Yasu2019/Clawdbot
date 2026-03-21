# Email RAG Filters

Email RAG の送信元除外ルールは、次の JSON で管理します。

- [email_rag_sender_filters.json](D:/Clawdbot_Docker_20260125/data/workspace/email_rag_sender_filters.json)

主な用途:
- メルマガ除外
- 業務外送信元の blacklist
- nightly 通知本文の業務メール抽出

反映先:
- [generate_email_rag_message.py](D:/Clawdbot_Docker_20260125/data/workspace/generate_email_rag_message.py)

変更方法:
1. `newsletter_patterns` に除外キーワードを追加
2. `blacklist_patterns` に除外したい送信元名・ドメイン・メールアドレス断片を追加
3. 次回 Email RAG 実行時に自動反映
