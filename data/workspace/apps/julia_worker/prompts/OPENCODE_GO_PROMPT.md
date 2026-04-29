# OpenCode GO Prompt

目的:
  既存ClawstackにJulia Numerical Workerを安全に融合する。

作業モード:
  - 破壊的変更禁止
  - 既存構成調査優先
  - Gitバックアップ必須
  - override compose方式
  - Portalカード追加のみ
  - 失敗時は即ロールバック案を提示

具体タスク:
  1. ZIPの中身を確認
  2. READMEとdocsを読む
  3. 既存Clawstackのcompose/network/portal構成を調査
  4. standalone起動テスト
  5. override作成
  6. Portalカード追加
  7. curlでAPIテスト
  8. 変更レポート作成

禁止:
  - docker compose down -v
  - docker system prune
  - 既存DB削除
  - 既存Portal全面書換
  - 既存Node-REDフロー上書き
