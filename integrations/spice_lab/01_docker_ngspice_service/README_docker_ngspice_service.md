# Docker側 ngspice解析サービス

## 起動

```bat
cd 01_docker_ngspice_service
docker compose -f docker-compose.ngspice.yml up -d --build
```

確認:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```

## サンプル実行

PowerShell:

```powershell
$ex = Invoke-RestMethod http://127.0.0.1:8765/examples/rc_lowpass
$body = @{ name = 'rc_lowpass'; netlist = $ex.netlist } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri http://127.0.0.1:8765/simulate -Method POST -Body $body -ContentType 'application/json'
```

curl:

```bash
curl http://127.0.0.1:8765/health
```

## データ保存先

```text
01_docker_ngspice_service/work/runs/<run_id>_<name>/
```

## OpenClawから使う想定

- `/examples/{name}` でテンプレ回路を取得
- `/simulate` にネットリストをPOST
- 戻り値の `measurements` / `log_tail` / `files` をOpenClaw Gateway側で要約
- 必要に応じて `run.log` / `metadata.json` / CSV をPaperlessまたはQdrantへ登録

## セキュリティ

- ポートは `127.0.0.1` にのみ公開
- `.shell` を含むネットリストは拒否
- シミュレーション時間にタイムアウトあり
- 既定では外部ネットワーク公開しない
