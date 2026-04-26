# IoT Circuit Lab: LTspice → Wokwi → Node-RED 協調パッケージ

目的:
現場IoT試作を、以下の3段構えで安全に進めるための協調テンプレートです。

```text
LTspiceで電気的に安全か確認
  ↓
WokwiでESP32制御・MQTT送信を確認
  ↓
Node-REDでデータ運用・しきい値判定・通知・記録を確認
```

## 重要方針

このZIPは、LTspiceをDockerに無理に入れたり、Wokwiとリアルタイム連成したりするものではありません。

- LTspice: Windows側で回路検証
- Wokwi: ESP32/Arduino制御の仮想検証
- Node-RED: MQTT受信、運用ロジック、異常判定
- Portal: 起動カード、導線、テンプレ置き場

という疎結合の協調構成です。

## 既存環境への影響

既存の以下は上書きしません。

- 既存 docker-compose.yml
- 既存 Node-RED flows.json
- 既存 Portal services.yaml
- 既存 OpenClaw / n8n / Grafana

必要なものだけを手動でマージ・インポートします。

## 含まれるもの

```text
docs/
  01_architecture.md
  02_workflow_ltspice_to_wokwi_to_nodered.md
  03_safety_checklist.md
  04_equipment_examples.md

ltspice/
  templates/
    sensor_rc_filter/
    voltage_divider_adc_protection/
    thermistor_divider/
    relay_flyback/
  exported_waveforms/
    sample_sensor_waveform.csv
  README_LTSPICE.md

wokwi/
  esp32-adc-mqtt-lab/
    sketch.ino
    diagram.json
    libraries.txt
  calibration/
    adc_calibration.example.json

node-red/
  flows_ltspice_csv_to_mqtt_import.json
  flows_wokwi_adc_mqtt_import.json

portal/
  homepage-services-snippet.yml
  iot_circuit_lab_card.html

scripts/
  01_prepare_folders.ps1
  02_find_ltspice.ps1
  03_convert_ltspice_csv_to_calibration.py
  04_publish_ltspice_csv_to_mqtt.py
  05_make_backup_before_merge.ps1

handoff/
  CODEX_ANTIGRAVITY_HANDOFF.md
```

## 最短導入手順

1. ZIPを展開します。

推奨先:

```powershell
D:\Clawdbot_Docker_20260125\clawstack_v2\addons\iot_circuit_lab
```

2. フォルダ準備:

```powershell
.\scripts\01_prepare_folders.ps1
```

3. LTspiceの場所確認:

```powershell
.\scripts\02_find_ltspice.ps1
```

4. Node-REDへ以下をインポート:

```text
node-red/flows_ltspice_csv_to_mqtt_import.json
node-red/flows_wokwi_adc_mqtt_import.json
```

5. Portalに以下のsnippetを手動マージ:

```text
portal/homepage-services-snippet.yml
```

6. Wokwiで以下を使う:

```text
wokwi/esp32-adc-mqtt-lab/
```

7. 既存のMosquitto MQTT Brokerへ送信:

```text
host.wokwi.internal:1883
```

## 使い方のイメージ

```text
LTspiceでRCフィルタや保護回路を確認
  ↓ CSV出力
scripts/03_convert_ltspice_csv_to_calibration.py
  ↓ ADC換算・しきい値案生成
Wokwi ESP32でADC読み取り・MQTT送信
  ↓
Node-REDで受信、異常判定、Dashboard/DB/n8n/OpenClawへ展開
```

## 注意

- LTspiceはWindows側アプリとして使う前提です。
- Node-REDの既存フローを直接編集しないでください。必ずUIからImportしてください。
- WokwiからローカルMQTTに接続するには、原則としてWokwi Private IoT Gatewayが必要です。
- Public MQTT Brokerに会社情報・設備情報・品番・顧客情報・実測値を送らないでください。
