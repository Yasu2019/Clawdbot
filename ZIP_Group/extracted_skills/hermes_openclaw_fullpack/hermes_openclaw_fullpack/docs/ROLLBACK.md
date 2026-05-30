# ロールバック手順

```bash
docker compose -f configs/docker-compose.hermes-openclaw.yml down
```

完全削除する場合のみ:

```bash
docker volume rm hermes_openclaw_fullpack_qa_pgdata hermes_openclaw_fullpack_qdrant_data
```

注意: volume削除は検証データも消えるため、人間確認後のみ。
