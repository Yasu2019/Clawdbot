# 03 Ingest / Compile / Query / Maintain

## 1. Ingest
### 入れる対象
- Web記事
- PDF
- 社内規格
- 顧客要求事項
- 不具合解析レポート
- 実験メモ
- 会議メモ

### 収集例
- Obsidian Web Clipperで `raw/web/`
- Paperless経由PDFを `raw/pdf/`
- 社内ExcelやPowerPointをPDF化して `raw/internal/`

## 2. Compile
### 目的
生資料を、AIが扱いやすく、人間も再利用しやすいMarkdownへ変換します。

### 生成物の例
- 要約
- キーワード一覧
- 用語集
- 関連リンク
- 重要判断点
- 不明点
- 次に確認すべき事項

### 推奨出力形式
```markdown
# タイトル
## Summary
## Key Facts
## Definitions
## Related Notes
## Open Questions
## Source Links
```

## 3. Query
質問した結果を使い捨てにせず、`wiki/qa/` に蓄積します。

### 保存推奨項目
- 質問日時
- 質問文
- 使用した対象ノート
- 回答
- 追加で発生した仮説
- 次回確認事項

## 4. Maintain
### 定期メンテ項目
- 重複ノート統合
- 壊れたリンク修正
- 矛盾点の抽出
- 古い情報の明示
- 用語ゆれ統一

### 月次点検例
- 「同じテーマで複数結論がある」ノート洗い出し
- 「参照元が古い」ノート確認
- 「未整理タグ」付きノートをゼロ化
