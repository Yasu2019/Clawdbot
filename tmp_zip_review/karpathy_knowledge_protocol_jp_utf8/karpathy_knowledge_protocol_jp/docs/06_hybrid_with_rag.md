# 06 Hybrid With Existing RAG

## 結論
既存RAGは捨てず、Karpathy方式と併用します。

## 役割分担
### RAGが向くもの
- 膨大な資料からの初期発見
- キーワード検索
- 類似事例探索
- 横断的な存在確認

### Claude Code + Wikiが向くもの
- 深い要約
- 因果関係整理
- 類似概念の差分整理
- 判断記録
- 継続成長

## 運用例
1. Paperless/Qdrant で候補資料を探索
2. 候補を raw に集約
3. Claude Code が compiled 生成
4. wikiへ構造化
5. 後日質問結果を qa へ追記
6. 価値が高ければ topics へ昇格
