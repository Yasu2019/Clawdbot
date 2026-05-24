# 08_codex_prompt - Codex/Claude Code/Antigravityへ渡す指示文

以下を Codex CLI / Claude Code / Antigravity に渡すと、既存Portalへ統合作業しやすくなります。

```text
目的:
MiniPC Content 5-Forces Gate を既存 Portal ダッシュボードへ統合してください。

前提:
- 既存の note生成、Kindlebook生成、YouTube生成、TikTok生成、ミニゲーム生成カードの前段に追加する。
- 既存カードを壊さない。
- APIは http://localhost:8765 を想定。
- 文字コードは UTF-8 固定。
- 会社情報、Gmail、図面、顧客情報を外部APIへ送らない。
- 既存Docker Composeとポート衝突を確認する。8765が使用中なら別ポートに変更し、manifestも更新する。

作業:
1. 既存Portalのカード定義方式を確認。
2. portal-card/portal_card_manifest.json を参考に新カードを追加。
3. Docker Compose統合が必要なら既存composeへ service を追加。
4. 既存の生成カードへ渡すJSON形式を確認し、評価結果の recommended_platform と outline を渡せるようにする。
5. 破壊的変更は禁止。変更前にバックアップまたはGitコミットを作成。
6. 既存機能との衝突がある場合は、統合せずレポートに理由を書く。

完了条件:
- Portalからタイトル・読者・困りごとを入力できる。
- 採点結果、判定、推奨媒体、リスク、次のアクションが表示される。
- note/Kindle/YouTube/TikTok/minigameの各生成カードへ連携できる、または連携方法がREADMEに明記される。
- Windowsで文字化けしない。
```
