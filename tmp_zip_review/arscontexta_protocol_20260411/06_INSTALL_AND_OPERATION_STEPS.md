# インストールと運用手順

## install 手順（公開情報ベース）
Claude Code 上で以下を実行:

```text
/plugin marketplace add agenticnotetaking/arscontexta
/plugin install arscontexta@agenticnotetaking
```

その後:
1. Claude Code を再起動
2. `/arscontexta:setup`
3. 2〜4 問程度の対話でドメイン説明
4. 生成完了後、再度 Claude Code を再起動
5. `/arscontexta:help`
6. `/arscontexta:health`

## 推奨初期チェック
- 生成ディレクトリ確認
- hooks 有効化確認
- skills 読み込み確認
- help でコマンド一覧確認
- health で初期診断

## 初回投入サンプル
以下のような 10〜15 ノートだけ入れる:
- 会議メモ 3件
- 技術検討 3件
- 動画要約 3件
- 実験メモ 3件

## 運用の基本
1. Inbox に雑に書く
2. 定期的に `/ralph`
3. `/verify` で品質確認
4. `/reflect` で MOC 更新
5. 古いノートの再接続が必要なら `/reweave`
