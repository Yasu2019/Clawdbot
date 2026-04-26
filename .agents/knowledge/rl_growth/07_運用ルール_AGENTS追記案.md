# AGENTS.md 追記案

以下は AGENTS.md や類似のガバナンスファイルへ追記する叩き台です。

```md
## Self-Improvement Loop Policy

1. For each substantial task, create a review record.
2. Use a reviewer model to score the first draft on accuracy, completeness, usefulness, and instruction compliance.
3. If the total score is below threshold, create an improved second draft.
4. Store both failure and success patterns in vector memory.
5. Before answering a similar future task, retrieve the most relevant prior success/failure patterns.
6. Do not blindly trust prior memory; weigh recent, higher-scoring, and task-matched memories more heavily.
7. Keep a full trace in Langfuse for observability.
8. Route tasks to different models based on measured historical performance when possible.
9. Never overwrite the original trace; append review and improvement spans.
10. Human override always has priority over automatic memory-derived guidance.
```

---

## 追加の現場ルール

- 品質報告・顧客メールは accuracy と tone を重視
- 技術プロトコルは actionability を重視
- 単位系や数値がある回答は factual_error を厳しく検出
- 不明点は断定せず assumptions を明示

