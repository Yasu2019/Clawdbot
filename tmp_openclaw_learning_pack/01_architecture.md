# 01. 全体アーキテクチャ

## 目的
既存の RAG 基盤を、単なる検索ではなく「経験を残す」基盤へ進化させる。

## 基本思想
- モデル再学習はしない
- 外部記憶で経験を蓄積する
- 新規案件ごとに過去の類似事例・失敗事例・改善活動を比較する
- AIの判断結果も再保存する
- 人レビュー結果で判断品質を補正する

## 全体像

```text
[Email / Paperless / 議事録 / 改善票 / CAEログ / CSV / 手入力]
                              ↓
                             n8n
                              ↓
                      learning_engine API
                 ┌──────────┼──────────┐
                 ↓          ↓          ↓
              Qdrant      LiteLLM    Langfuse
           (知識蓄積)    (比較判断)   (観測)
                 ↓
   Portal / OpenClaw / Open WebUI / 将来の支援UI
```

## 既存環境で活かすコンポーネント
- Qdrant: ベクトル検索と payload 保持
- n8n: 取込 / 正規化 / 定期ジョブ
- LiteLLM: 比較判断の統一出入口
- Ollama: ローカル補助モデル
- Langfuse: 判断品質追跡
- Paperless + Docling: 文書変換
- Portal: UI導線
- openfoam / openradioss: CAE知見の元データ

## 新規追加コンポーネント
- learning_engine (FastAPI)
- learning_memory Portal page
- 必要に応じて `impact_memory_importer` などの軽量補助スクリプト
