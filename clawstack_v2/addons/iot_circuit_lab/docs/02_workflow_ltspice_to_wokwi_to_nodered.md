# 02. LTspice → Wokwi → Node-RED 手順

## Step 1: LTspiceで回路を確認

例:

- センサー出力 0-10V をESP32 ADC 0-3.3Vへ落とす分圧
- RCローパスフィルタでノイズを落とす
- ADC入力へ保護抵抗とクランプを入れる
- リレー/ソレノイドにフライバックダイオードを入れる

確認すること:

```text
最大電圧がADC許容範囲を超えないか
RCの応答遅れが大きすぎないか
ノイズでしきい値を跨がないか
電源投入時に異常電圧が出ないか
保護部品の電流が過大でないか
```

## Step 2: LTspice波形をCSV出力

LTspiceの波形ビューアからCSV出力します。

保存先例:

```text
ltspice/exported_waveforms/sensor_frontend_result.csv
```

列名は以下を推奨します。

```csv
time,v_adc
0.000,0.100
0.010,0.110
```

複数列の場合:

```csv
time,v_sensor,v_filtered,v_adc
```

## Step 3: ADC換算・しきい値案生成

```powershell
python .\scripts\03_convert_ltspice_csv_to_calibration.py `
  --input .\ltspice\exported_waveforms\sensor_frontend_result.csv `
  --voltage-column v_adc `
  --vref 3.3 `
  --adc-bits 12 `
  --output .\wokwi\calibration\adc_calibration.generated.json
```

## Step 4: Wokwiへ反映

`wokwi/esp32-adc-mqtt-lab/sketch.ino` 内のしきい値を、生成されたJSONに合わせて調整します。

例:

```cpp
const int ADC_WARN_HIGH = 3000;
const int ADC_ALARM_HIGH = 3500;
```

## Step 5: WokwiでESP32 MQTT送信

Wokwi Private IoT Gatewayを使う場合:

```text
MQTT_HOST = "host.wokwi.internal"
MQTT_PORT = 1883
```

## Step 6: Node-REDで運用ロジック確認

Node-REDへ以下をインポートします。

```text
node-red/flows_wokwi_adc_mqtt_import.json
```

確認すること:

```text
MQTT受信できるか
ADC値が電圧へ換算されるか
warn/alarm判定が正しいか
異常時にalarm topicへ出るか
```

## Step 7: 実機へ移行

Wokwiの仮想ESP32を実機ESP32へ置き換えます。
Node-RED側topicとpayloadを合わせておけば、運用ロジックは大きく変えずに移行できます。
