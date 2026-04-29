# Codex / Claude / Antigravity 作業指示書

## 目的
このZIPを既存Clawstackへ安全に融合する。ただし、既存ファイルの破壊・上書きは禁止。

## 作業原則
- まずGitHubまたはZIPでバックアップ
- 既存Portal構造を調査
- 既存ComfyUIの配置とmodels/custom_nodesを調査
- 追加配置で実装
- 不明な場合は既存を変えず、READMEに追記

## 禁止事項
- `docker compose down -v` の実行
- DB volumeの削除
- custom_nodesの一括削除
- 既存Portalのindex.html上書き
- 既存Node-REDフローの削除

## 成功条件
- PortalにVNCCSカードが表示される
- Node-REDにVNCCS Dataset Loggerフローが追加される
- DOE CSVが生成できる
- ComfyUI側のワークフロー管理場所が明確
- 生成画像と条件JSONのペア管理ルールが文書化されている
