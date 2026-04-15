# 評価設計 / KPI とスコアリング

## なぜ評価設計が重要か

自己成長は「評価の質」でほぼ決まります。
評価が曖昧だと、改善ループはすぐ壊れます。

---

## 最低限の評価軸

各回答に対して 0〜5 点で採点することを推奨します。

1. 正確性
2. 完全性
3. 実用性
4. 指示遵守
5. 簡潔性
6. 再利用性

---

## 総合報酬の例

```text
reward =
  0.30 * accuracy +
  0.20 * completeness +
  0.20 * usefulness +
  0.15 * instruction_following +
  0.10 * conciseness +
  0.05 * reuse_value
```

---

## 実務で追加すべき軸

### メール文面系
- 丁寧さ
- 誤解の少なさ
- 社外向け自然さ

### 技術プロトコル系
- 手順の実行可能性
- 前提条件の明確さ
- コピペ可能性

### CAE / 品質解析系
- 単位や数値の整合
- 仮定の明示
- 再現可能性

---

## スコア閾値の例

- 4.2以上: 成功例として保存
- 3.4〜4.19: 記録のみ、必要なら軽微改善
- 3.39以下: 改善版生成を実行

---

## 失敗カテゴリ例

- factual_error
- missing_steps
- vague_explanation
- format_violation
- too_long
- too_short
- unsafe_assumption
- low_actionability

これを reviewer に必ず1つ以上出させることで、後の分析がしやすくなります。

