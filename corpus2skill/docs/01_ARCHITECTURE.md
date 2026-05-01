# 01 アーキテクチャ

## 全体像

Paperless / File Library / 手動投入ファイル
→ Extractor
→ Tree Builder
→ Corpus Tree Store
→ Navigator Agent
→ Evidence Tracker
→ OpenClaw Gateway / Portal
→ Langfuse Trace

## 従来RAGとの違い

従来RAG:
- Query
- Embedding
- Qdrant top-k
- Answer

Corpus2Skill:
- Query
- Root overview確認
- Branch選択
- 必要なら下位階層へ移動
- 外したら戻る
- 原文ID取得
- 回答
- 探索ログ保存

## ハイブリッド設計
Qdrantは廃止しません。役割を変えます。

- Qdrant: 類似候補の高速発見
- Corpus Tree: 文書構造・文脈保持
- Navigator: 探索判断
- Evidence Tracker: 引用と監査証跡

## 鈴木様環境での主な用途

### IATF内部監査
- 条項 → 社内規定 → 記録 → エビデンス → 監査質問

### 図面・GD&T
- 図面番号 → datum → feature → tolerance → 測定方法 → 3Dモデル対応面

### QC工程表
- 工程 → 管理項目 → 規格 → 測定頻度 → 異常処置 → 関連帳票

### 不具合解析
- 現象 → 発生工程 → 過去類似 → 原因系統 → 是正処置 → 効果確認

