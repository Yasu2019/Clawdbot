# Qdrant スキーマ案

## コレクション候補

### task_memories
タスク全体の履歴

### success_patterns
高スコア回答とその前提

### failure_patterns
失敗例と原因

### rewrite_pairs
初回回答→改善版の対応

---

## payload例

```json
{
  "task_id": "uuid",
  "task_type": "email_editing",
  "input_summary": "顧客向け残留油分測定メールの添削",
  "user_goal": "丁寧で誤解の少ない説明",
  "model": "gemini-2.5-flash",
  "review_model": "claude-opus",
  "score": 4.4,
  "failure_tags": [],
  "success_tags": ["clear_explanation", "customer_friendly"],
  "initial_answer": "...",
  "improved_answer": "...",
  "final_answer": "...",
  "latency_ms": 5400,
  "cost_usd": 0.012,
  "timestamp": "2026-04-11T10:00:00+09:00"
}
```

---

## ベクトル化対象

原則として以下を連結して embedding してください。

- task_type
- input_summary
- user_goal
- final_answer
- failure_tags / success_tags

理由は、将来の類似検索で「似た問題にどう答えたか」を拾いやすくするためです。

