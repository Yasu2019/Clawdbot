# 検証チェックリスト

## Windows LTspice

- [ ] 公式ページからインストールした
- [ ] `02_check_ltspice_cli.ps1` で実行ファイル検出OK
- [ ] `03_run_ltspice_batch_example.ps1` で `.raw` / `.log` 生成OK

## Docker ngspice

- [ ] `docker compose -f docker-compose.ngspice.yml up -d --build` OK
- [ ] `http://127.0.0.1:8765/health` OK
- [ ] `/examples/rc_lowpass` OK
- [ ] `/simulate` OK
- [ ] `work/runs` にログ保存OK

## OpenClaw Portal

- [ ] 既存Portalカードと名前競合なし
- [ ] `circuit_sim_hub` が表示される
- [ ] API baseを変更できる
- [ ] サンプル実行できる

## 品質・監査観点

- [ ] シミュレーション条件を保存している
- [ ] モデル限界を明記している
- [ ] 実測確認の代替ではないと明記している
- [ ] 顧客提出時は検証者・日付・モデル出典を追記する

## セキュリティ

- [ ] 127.0.0.1バインド
- [ ] タイムアウトあり
- [ ] `.shell` ブロックあり
- [ ] 外部公開していない
