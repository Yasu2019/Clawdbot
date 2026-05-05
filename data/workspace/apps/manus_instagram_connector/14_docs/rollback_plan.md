# ロールバック計画

## 基本方針

このZIPは初期状態では既存環境を変更しない設計。  
Portal統合やデータ保存機能を追加する場合は、追加前にバックアップを取る。

## ロールバック対象

- Portalカード
- SNSデータフォルダ
- 追加設定ファイル
- 追加スクリプト
- Manus Connector連携
- Instagram権限

## ロールバック手順

### 1. 投稿自動化を止める

- Manus側のInstagram Connectorを一時停止または解除
- 予約投稿を確認
- 不要な予約投稿を削除

### 2. Portalカードを無効化

- 追加したPortalカードのみ無効化
- 既存カードは触らない

### 3. データを退避

- data/sns をzip化して保管
- ログを保全

### 4. 追加ファイルを削除

削除前にClaude/Codexが対象を確認する。  
ワイルドカード削除は禁止。

### 5. Meta/Instagram権限の見直し

- Instagramアプリ連携を確認
- 不要な権限を解除
- パスワード変更が必要か判断

## やってはいけないロールバック

- docker compose down -v
- docker volume rm
- DB削除
- .env全体削除
- Portal全体初期化
- OpenClaw本体の一括削除

