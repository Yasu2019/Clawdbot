# OpenClaw QA Engineering Studios

Claude Code Game Studios の「役割別エージェント組織」「スラッシュコマンド」「自動フック」「ファイルベース記憶」の思想を、OpenClaw / Clawstack の品質保証・IATF・CAE・RAG・Portal・Docker運用向けに再設計した現場投入用テンプレートです。

## 目的

OpenClaw 上で、複数AIツール（Codex CLI / Claude Code / Antigravity / ローカルLLM）に対して、同じ判断基準・同じ安全制約・同じ作業記憶を共有させます。

特に次を重視します。

- SQL Serverや既存データを壊さない読み取り専用保証
- Docker Compose / Portal 既存構成との衝突検出
- IATF 16949 / QA文書の根拠確認
- Excel/VBAの破壊的処理チェック
- Paperless / Docling / Qdrant / RAG投入品質の確認
- ACT.md によるセッション切れ後の再開性
- Codex / Claude / Antigravity への明確な引き継ぎ

## 想定配置先

標準配置先例：

```text
D:\Clawdbot_Docker_20260125\clawstack_v2\openclaw_qa_engineering_studios
```

または OpenClaw Gateway コンテナ内：

```text
/home/node/clawd/openclaw_qa_engineering_studios
```

## 基本運用

1. まず `ACT.md` を読む
2. `PORTAL_APPS.md` または既存 Portal 一覧を確認する
3. `DECISIONS.md` を見て過去判断と矛盾しないか確認する
4. 作業内容に応じて `commands/` を選ぶ
5. 変更前に `hooks/` を実行する
6. 作業後に `ACT.md` / `DECISIONS.md` / `RISKS.md` を更新する
7. Codex / Claude / Antigravity のどれに渡すかを `HANDOFF_*.md` に記録する

## レビューモード

- `solo`: 速度優先。個人検証・試作向け
- `lean`: バランス型。通常作業向け
- `full`: 本番投入前。衝突・安全・根拠チェックを最大化

## 禁止事項

- SQL Serverへの INSERT / UPDATE / DELETE / DROP / ALTER / TRUNCATE
- 既存Portalカードの無確認上書き
- Dockerポートの無確認追加
- 認証トークン・Bearer token・APIキーの平文コミット
- ACT.md 未更新のまま長時間作業を進めること
- エビデンスなしでIATF条項適合を断定すること

## 最初に実行する推奨プロンプト

```text
このリポジトリを OpenClaw QA Engineering Studios として扱ってください。
まず README.md, ACT.md, DECISIONS.md, RISKS.md, review_modes/full.yaml を読み、既存の OpenClaw / Clawstack 構成と衝突しないか確認してください。
採用・部分採用・保留を判断し、作業前に ACT.md を更新してください。
SQL Serverや既存データを書き換える処理は禁止です。
```
