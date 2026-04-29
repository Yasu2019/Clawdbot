# Claude Review Prompt

このZIPは Clawstack に Julia Numerical Worker を追加するためのものです。
あなたの役割は実装ではなく、安全レビューです。

## レビュー観点

- 既存Clawstackを壊す変更がないか
- docker-compose override方針が守られているか
- ポート衝突リスク
- セキュリティリスク
- .env/APIキー漏洩リスク
- ファイル書き込み権限の過剰付与がないか
- Node-REDやPortal既存ファイルの上書きリスク
- レベラー計算結果が正式CAEと誤認されない記述になっているか

## 出力形式

1. 総合判定: 採用可 / 条件付き採用 / 却下
2. 危険箇所
3. 修正案
4. 実装前チェックリスト
5. ロールバック手順
