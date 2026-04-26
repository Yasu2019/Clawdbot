# OpenClaw Learning Memory Protocol Pack

このZIPは、既存の Clawstack / OpenClaw 統合環境に対して、**疑似 Nested Learning / 経験蓄積AI** を追加するための引き渡しパックです。

前提環境:
- 既存 `docker-compose.yml` に `qdrant`, `n8n`, `litellm`, `ollama`, `langfuse`, `docling`, `paperless`, `portal_server`, `openfoam`, `openradioss` などが存在
- 追加は最小限にし、既存環境を壊さない
- 新規中核サービスは `learning_engine`

このパックには以下が含まれます。

1. 全体方針
2. データ範囲とガードレール
3. 学習エンジン仕様
4. Email / 品質問題 / 改善活動の学習仕様
5. CAE / FEM の成功失敗知識化仕様
6. n8n ワークフロー案
7. Qdrant コレクション設計
8. docker-compose 追記例
9. API 仕様
10. Portal UI 案
11. サンプル JSON
12. 実装順序と受入基準

重要:
- 元勤務先（Foxconn / Marunix など）のメールも経験資産にはなり得るが、**現在業務データと無差別統合はしない**
- `source_org`, `confidentiality`, `reuse_scope`, `review_status` を必須メタデータにする
- まずは「検索・比較・判断補助」までに留め、**自動送信 / 自動対外回答** は初期段階では無効にする
