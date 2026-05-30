# 実装手順

## Phase 0: 解凍

```bash
unzip hermes_openclaw_fullpack.zip
cd hermes_openclaw_fullpack
```

## Phase 1: Sandbox起動

```bash
cp .env.example .env
docker compose -f configs/docker-compose.hermes-openclaw.yml up -d --build
```

確認:

```bash
curl http://localhost:8791/health
```

## Phase 2: 安全ハーネス確認

```bash
python examples/check_command.py
```

期待:

- 通常のpython実行: allow
- docker compose down: review
- git reset --hard: block
- rm -rf /: block

## Phase 3: QAメモリ確認

```bash
python examples/add_qa_memory.py
```

## Phase 4: Portal登録

`portal/cards/hermes_agent_qa_card.json` をPortal側のカード登録処理へ渡す。

## Phase 5: Hermes本体との接続

Hermes本体を導入する場合も、最初はこのBridgeを経由し、直接Shell実行を禁止する。

## Phase 6: OpenClawへの統合判断

`codex_prompts/ACCEPTANCE_REVIEW_PROMPT.md` をCodex CLIまたはClaude Codeへ渡して判定させる。
