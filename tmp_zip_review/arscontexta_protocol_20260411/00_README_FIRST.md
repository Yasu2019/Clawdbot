# Ars Contexta 導入プロトコル（Claude / Codex 判定委任版）

この ZIP は、**arscontexta をあなたの環境へ導入するかどうかを、受け取り側の Claude Code または Codex が判断しやすい形**で整理したプロトコルです。

## この ZIP の目的
- arscontexta の**導入価値**
- **既存 Obsidian Vault を壊さない導入順**
- **Claude Code / Obsidian / 既存 RAG 基盤との住み分け**
- **採用 / 不採用 / 一部採用**を判断するための評価基準
- そのまま AI エージェントへ渡せる実行指示文

## 前提
- 既存 Vault をできるだけ壊さない
- 既存 OpenClaw / RAG / Paperless / Qdrant を活かす
- 導入の可否は受け取り側エージェントが判断
- 文字コードは UTF-8

## 公開情報ベースで確認できた要点
- arscontexta は Claude Code 用プラグインで、会話から知識システムを生成する構成
- インストールは marketplace 追加 → install → 再起動 → `/arscontexta:setup`
- 生成後、再起動して generated hooks / skills を有効化
- 常設コマンドに `/arscontexta:help`, `/arscontexta:health`, `/arscontexta:upgrade` 等がある
- セットアップ後に `/reduce`, `/reflect`, `/reweave`, `/verify`, `/ralph` などの生成コマンドが利用可能になる構成

## 重要方針
このプロトコルでは、**arscontexta を即本番導入する前提にはしません。**
まずは **隔離検証 → 小規模導入 → 既存運用との比較 → 採否判定** の順で進めます。
