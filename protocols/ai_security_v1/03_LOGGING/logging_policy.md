# LOGGING POLICY

## 記録対象
- ユーザー指示
- 実行候補
- 承認/却下結果
- 実際の変更内容
- 参照ファイル一覧
- エラー内容

## 最低限必要なログ項目
- timestamp
- actor
- action
- target
- result
- hash or diff reference

## 保管方針
- /logs に集約
- 日次ローテーション
- 監査用スナップショットを別保存
- 重要ログは削除禁止
