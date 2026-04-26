# Paperless / OpenClaw 連携案

## 1. 連携思想
MarkItDown は OCR の代替ではなく、**構造化された Markdown 出力層**として使う。

- OCR: 文字の取得
- MarkItDown: 構造化表現
- Docling: 補正または代替変換
- Chunker: RAG向け分割
- Embedder: ベクトル化
- Qdrant: 格納
- OpenClaw: 推論利用

## 2. 推奨データフロー
```text
受領フォルダ
→ 必要なら OCR
→ MarkItDown
→ Markdown正規化
→ 文書種別推定
→ セクション分割
→ embedding
→ Qdrant
→ エージェント検索
```

## 3. 実務上のおすすめ
- 原本は必ず残す
- 派生Markdownは再生成可能にしておく
- md と metadata.json をペアで保存
- 失敗ファイルは quarantine に隔離
- 日本語ファイル名の正規化ルールを決める
