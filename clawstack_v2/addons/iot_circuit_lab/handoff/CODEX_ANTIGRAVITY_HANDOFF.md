# Codex / Antigravity / Claude Code 引継ぎ指示

## 目的

既存のGMKtec NucBox K10 / Clawstack / Portal / Node-RED / Docker環境に、
LTspice → Wokwi → Node-RED の現場IoT試作協調レーンを追加する。

## 基本方針

完全融合ではなく協調にする。

```text
LTspice: 電気的安全・アナログ回路確認
Wokwi: ESP32制御・MQTT送信確認
Node-RED: データ運用・異常判定確認
Portal: 起動カード・導線
```

## 絶対禁止

1. 既存 `docker-compose.yml` を即時上書きしない
2. 既存 Node-RED `flows.json` を直接編集・上書きしない
3. 既存 Portalカードを削除しない
4. 既存Node-REDコンテナを作り直さない
5. Wokwi Public Gatewayや外部MQTTへ会社・顧客・品番・実測値を流さない
6. 実機設備の安全回路へ介入するような指示を書かない

## 作業前確認

```powershell
cd D:\Clawdbot_Docker_20260125\clawstack_v2
git status
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"
docker network ls
```

## バックアップ

Git管理されている場合:

```powershell
git add -A
git commit -m "backup before adding iot circuit lab"
```

Git管理外なら:

```powershell
.\addons\iot_circuit_lab\scripts\05_make_backup_before_merge.ps1
```

## 採用判断

### 全面採用

条件:

- 既存Mosquittoまたは追加Mosquittoが使える
- Node-REDへフローImportできる
- Portalへカード追加できる
- Wokwi Private IoT Gatewayが使える、またはWokwiはスタンドアロン試作として使える

### 部分採用

条件:

- LTspiceテンプレだけ使う
- Portalカードだけ追加する
- Node-REDのCSV Replayだけ使う
- Wokwi Private Gatewayが使えないため、WokwiはローカルMQTT接続なしで使う

### 保留

条件:

- 既存Node-REDの認証・プロジェクト機能・settings.jsが特殊
- MQTTポート衝突の解消が必要
- 会社ネットワークポリシー上、Wokwiのクラウド利用確認が必要

## 推奨マージ内容

1. `addons/iot_circuit_lab` として本ZIPを配置
2. `portal/homepage-services-snippet.yml` を既存Portal設定へ手動マージ
3. Node-RED UIから以下をImport
   - `node-red/flows_ltspice_csv_to_mqtt_import.json`
   - `node-red/flows_wokwi_adc_mqtt_import.json`
4. LTspiceテンプレを必要に応じて複製して案件別フォルダに保存
5. 変換スクリプトでADCしきい値案を生成
6. Wokwiの `sketch.ino` にしきい値を反映

## 完了条件

- LTspice CSVサンプルから calibration JSON が生成できる
- Node-REDにLTspice CSV replay payloadが流せる
- Wokwi ESP32 ADC MQTTのpayloadをNode-REDで正規化できる
- 既存Node-RED/Portal/n8n/OpenClawに悪影響がない
