# /excel_vba_review

## 目的
Excel/VBAコードの安全性、SQL読み取り専用性、計算式、グラフ範囲、ユーザーフォーム連携を確認する。

## 禁止
- ADODBで更新系SQLを実行しない
- Workbooks.Open後に原本へSaveしない
- Delete / ClearContents の対象範囲を曖昧にしない

## 必須チェック
- check_sql_readonly.py
- check_vba_destructive.py
