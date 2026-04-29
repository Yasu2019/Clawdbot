# Operations Runbook

## 1. 単独テスト

```bash
docker compose -f docker-compose.julia-worker.standalone.yml up --build
```

別ターミナル:

```bash
curl http://localhost:8096/health
curl http://localhost:8097/health
```

## 2. レベラー計算

```bash
curl -X POST http://localhost:8097/leveler/estimate \
  -H "Content-Type: application/json" \
  -d '{"thickness_mm":0.8,"yield_mpa":85,"roller_diameter_mm":12,"pitch_mm":16,"entry_gap_mm":0.7,"exit_gap_mm":1.1,"stages":11,"friction":0.05}'
```

## 3. DOE生成

```bash
curl -X POST http://localhost:8097/doe/latin_hypercube \
  -H "Content-Type: application/json" \
  -d '{"n":12,"variables":{"entry_gap_mm":[0.5,1.5],"exit_gap_mm":[0.5,1.5],"friction":[0.02,0.15]}}'
```

## 4. グリッド探索

```bash
curl -X POST http://localhost:8097/optimize/leveler_grid \
  -H "Content-Type: application/json" \
  -d '{"thickness_mm":0.8,"yield_mpa":85,"roller_diameter_mm":12,"pitch_mm":16,"entry_gap_range":[0.5,1.5,0.1],"exit_gap_range":[0.5,1.5,0.1],"stages":11}'
```

## 5. よくあるトラブル

### Juliaコンテナの初回起動が遅い

Juliaパッケージのprecompileが入るため、初回buildは遅くなります。
2回目以降は速くなります。

### PortalからAPIにアクセスできない

確認点:

- `API_BASE` が正しいか
- 8097がhostに公開されているか
- ブラウザのCORS制限に引っかかっていないか
- nginx経由にするならreverse proxy設定が必要

### 既存Clawstackネットワークに入らない

`docker network ls` で既存ネットワーク名を確認し、
`docker-compose.julia-worker.override.example.yml` の `clawstack_net` を修正してください。

## 6. ロールバック

```bash
docker compose -f docker-compose.julia-worker.standalone.yml down
```

統合後に戻す場合:

```bash
git status
git restore <変更したファイル>
```
