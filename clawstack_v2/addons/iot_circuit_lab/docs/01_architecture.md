# 01. 全体アーキテクチャ

## 採用する協調構成

```text
[LTspice / Windows]
  - センサー入力回路
  - RCフィルタ
  - 分圧回路
  - 保護ダイオード
  - リレー/ソレノイド保護
  - 電源ノイズ
  ↓
  CSV / PWL / 回路定数 / しきい値案

[Wokwi / Browser or VS Code]
  - ESP32 ADC
  - MQTT publish
  - Wi-Fi接続
  - 仮想LED/ブザー
  ↓

[Mosquitto / Docker]
  - MQTT Broker
  ↓

[Node-RED / Docker]
  - データ受信
  - 正規化
  - 異常判定
  - Dashboard/DB/n8n/OpenClaw連携
```

## なぜ完全融合しないか

LTspiceはアナログ回路・電源・信号品質の検証に強く、Wokwiはマイコン制御・通信の検証に強く、Node-REDは運用データ処理に強いです。

したがって、無理に1つの画面や1つのコンテナへ統合するより、成果物を受け渡す方が堅牢です。

## 受け渡し成果物

| 前工程 | 後工程 | 受け渡すもの |
|---|---|---|
| LTspice | Wokwi | 電圧範囲、応答遅れ、RC時定数、ノイズ幅、ADCしきい値 |
| LTspice | Node-RED | CSV波形、異常判定テスト用データ |
| Wokwi | Node-RED | MQTT JSON |
| Node-RED | OpenClaw/n8n/Grafana | 正規化データ、アラーム、履歴 |

## 推奨MQTT Topic

```text
factory/lab/esp32-adc-001/telemetry
factory/lab/esp32-adc-001/status
factory/lab/esp32-adc-001/cmd
factory/lab/ltspice-replay-001/telemetry
factory/lab/alarm/text
```
