# リスクと対策

## リスク1: 自動リンクの誤接続
対策:
- まず sandbox で検証
- high-value notes だけ監査
- 違和感が強い MOC を削減

## リスク2: ノート爆増
対策:
- seed / reduce / reflect の対象を限定
- domain ごとに投入量を制御
- 週次で prune

## リスク3: Claude Code 依存
対策:
- markdown 所有を維持
- 生成ファイル構造を Git 管理
- 代替手段（RAG / 手動MOC）を残す

## リスク4: 既存RAGとの二重管理
対策:
- RAG は原本検索
- arscontexta は思考ネットワーク
- 文書全文を二重投入しない

## リスク5: Vault 汚染
対策:
- 本番 Vault へ直入れしない
- separate sandbox
- rollback 手順を事前定義
