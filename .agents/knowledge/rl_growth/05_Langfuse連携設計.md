# Langfuse連携設計

## 取るべきトレース

1. task_received
2. model_selected
3. first_answer_generated
4. review_completed
5. answer_rewritten (必要時)
6. memory_saved
7. final_answer_emitted

---

## スコアとして記録したいもの

- reward_total
- accuracy
- completeness
- usefulness
- instruction_following
- latency_penalty
- cost_penalty

---

## 理想の見え方

Langfuse画面上で以下が見えるようにすることが理想です。

- タスク種類別の平均スコア
- モデル別成功率
- 改善前後の差分
- 失敗カテゴリの頻度
- コストに対する品質効率

---

## 注意

評価値を雑に1個だけ記録すると、あとで役に立たないことが多いです。
最低でも

- 総合点
- 主要サブスコア
- 失敗カテゴリ

の3つは残してください。

