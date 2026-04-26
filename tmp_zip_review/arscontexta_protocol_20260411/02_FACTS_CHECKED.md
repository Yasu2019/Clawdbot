# 公開情報で確認した事項

## 1. GitHub README で確認できた点
- リポジトリ説明:
  - 「A second brain for your agent.」
  - Claude Code plugin
  - 会話から knowledge system を生成
- 現時点で README 上のバージョン表記:
  - `v0.8.0`
- install 手順:
  1. `/plugin marketplace add agenticnotetaking/arscontexta`
  2. `/plugin install arscontexta@agenticnotetaking`
  3. Claude Code 再起動
  4. `/arscontexta:setup`
  5. 2〜4 問の会話
  6. knowledge system 生成
  7. 再起動
  8. `/arscontexta:help`
- three-space architecture:
  - `self/`
  - `notes/`
  - `ops/`
- setup 後に出現する生成コマンド例:
  - `/reduce`
  - `/reflect`
  - `/reweave`
  - `/verify`
  - `/validate`
  - `/seed`
  - `/ralph`
  - `/pipeline`
  - `/tasks`
  - `/stats`

## 2. 公式サイトで確認できた点
- install 記法は GitHub README と整合
- 公式サイトでも marketplace 追加 → install → restart → `/arscontexta` 系の導線が示されている

## 3. 本プロトコルでの扱い
本 ZIP は上記の公開情報を前提に作成していますが、
実導入前には **受け取り側エージェントが最新 README / plugin manifest / 互換性要件を再確認** してください。
