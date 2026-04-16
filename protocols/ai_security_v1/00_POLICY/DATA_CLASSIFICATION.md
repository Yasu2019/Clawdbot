# DATA CLASSIFICATION

## Level A: 公開可
- 一般公開資料
- 公開済み技術メモ

## Level B: 社内限定
- 手順書
- 運用メモ
- 一般議事録

## Level C: 機密
- 顧客図面
- 品質データ
- 原価情報
- 社内未公開仕様

## Level D: 最重要
- APIキー
- VPN情報
- 認証トークン
- 秘密鍵
- 個人情報を含む原本

## 取り扱い原則
- Level C/D は AI にフルアクセスさせない
- Level D は原則 secrets 管理または手動投入のみ
- 分類不明データは上位分類で扱う
