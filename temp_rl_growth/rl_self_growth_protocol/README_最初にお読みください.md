# RL自己成長ループ 導入パック

このZIPは、あなたのミニPC上の既存構成

- OpenClaw
- LiteLLM
- Langfuse
- Qdrant
- Paperless / Docling / RAG系
- Ollama / Claude / Gemini 等の複数モデル運用

を前提に、**実務で使える「自己評価→改善→再利用」ループ**を追加するための実装たたき台です。

## このパックの狙い

多くの「自己成長システム」は、実際には以下で止まっています。

- 会話ログが溜まる
- Langfuseにトレースが残る
- 良い/悪いが何となく見える
- しかし、次回の挙動が変わらない

このパックでは、そこから一歩進めて、次を実現することを目的とします。

1. **回答ごとに評価を取る**
2. **悪い回答は改善案を生成する**
3. **良い回答は成功パターンとして蓄積する**
4. **次回プロンプトやRAG検索時に再利用する**
5. 必要に応じて **ルータ(LiteLLM)やモデル選択にも反映する**

---

# 重要な前提

この仕組みは、通常の意味での「モデル重みの学習」ではありません。

つまり、OllamaやGeminiやClaude本体の重みを書き換えるのではなく、以下で成長させます。

- 記憶（Qdrant / RAG）
- プロンプト改善
- 成功/失敗パターン再利用
- モデル振り分け改善
- レビューエージェントによる自己修正

したがって、**現実的・安全・すぐ試せる**一方で、
**本当のファインチューニングとは別物**です。

---

# まず最初に導入すべき最小構成

最初は以下だけで十分です。

- 1) 実行結果の評価JSONを取る
- 2) 失敗時に改善版回答を生成する
- 3) 成功パターンと失敗パターンをQdrantに保存する
- 4) 次回の類似タスク時にそれをRAGで引く

これだけでも、かなり「次からうまくなる」感が出ます。

---

# パック内のファイル

- `01_全体アーキテクチャ.md`
- `02_導入手順_段階別.md`
- `03_評価設計_KPIとスコアリング.md`
- `04_Qdrantスキーマ案.md`
- `05_Langfuse連携設計.md`
- `06_自己改善フロー_擬似RL.md`
- `07_運用ルール_AGENTS追記案.md`
- `08_失敗例と対策.md`
- `09_将来拡張_RLAnything風.md`
- `templates/system_prompt_patch.md`
- `templates/reviewer_prompt.txt`
- `templates/improver_prompt.txt`
- `templates/task_memory_schema.json`
- `templates/reward_schema.json`
- `examples/python/minimal_loop.py`
- `examples/python/qdrant_memory.py`
- `examples/python/review_and_rewrite.py`
- `examples/python/router_feedback.py`
- `examples/python/env_example.txt`
- `examples/json/example_trace_payload.json`
- `examples/mermaid/loop_mermaid.md`

---

# あなた向けの実務上の使いどころ

特に次の用途で効果が出やすいです。

- メール文面改善
- 品質報告書の作成支援
- CAE解析手順の提案改善
- GD&T / 図面読解の説明品質向上
- 社内手順書のドラフト改善
- Codex / Claude / Antigravityへのプロトコル生成改善

---

# 導入方針

おすすめ順は以下です。

## Phase 1
- Langfuse評価記録
- 改善案生成
- Qdrant保存

## Phase 2
- 類似タスク検索で再利用
- 成功/失敗プロンプト断片の自動注入

## Phase 3
- ルータに反映
- モデル選択をタスク別に最適化

## Phase 4
- 自動A/B比較
- 自己報酬関数調整
- 失敗再試行戦略の学習

---

# 注意

- このZIPは**導入可否の最終判断を受け取る側のCodex / Claude / あなた自身に委ねる**前提で作っています。
- つまり、全部を無理に入れるのではなく、必要な部分だけ採用してください。
- まずは最小構成から始め、問題なければ段階的に強化してください。

