# トラブルシューティング

## Docker APIが起動しない

```powershell
docker compose -f docker-compose.ngspice.yml logs --tail=100
```

ポート競合の場合:

```powershell
$env:SPICE_LAB_PORT=8766
docker compose -f docker-compose.ngspice.yml up -d
```

## ngspiceがエラーになる

- `.end` があるか確認
- 電源ノード、GND `0` があるか確認
- 部品名の先頭文字がSPICE規則に合っているか確認
- `.control` 内の `wrdata` 出力先が妥当か確認

## measurementsが空

`.meas` 文がログに出ていない可能性があります。まず `run.log` を確認してください。

## LTspiceが見つからない

`00_windows_ltspice/02_check_ltspice_cli.ps1` を再実行してください。見つからない場合は、LTspiceのインストール先を手動で `%USERPROFILE%\.openclaw_spice_lab\ltspice_path.txt` に記載してください。

例:

```text
C:\Program Files\ADI\LTspice\LTspice.exe
```

## PortalからAPIに接続できない

ブラウザのCORSやネットワーク経路の問題があり得ます。最初はPowerShellからAPI実行を確認してください。

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```
