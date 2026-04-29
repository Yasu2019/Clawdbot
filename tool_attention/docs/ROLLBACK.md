# ロールバック手順

```bash
docker compose -f docker-compose.yml -f docker-compose.tool-attention.yml down
rm docker-compose.tool-attention.yml
```

OpenClaw本体へパッチした場合は、GitHubのバックアップブランチから戻してください。
