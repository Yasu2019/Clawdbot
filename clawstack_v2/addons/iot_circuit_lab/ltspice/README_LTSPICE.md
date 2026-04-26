# LTspiceテンプレート

このフォルダは、Wokwi/Node-REDの前段で使う回路検証テンプレート置き場です。

## 使い方

1. LTspiceで `.cir` を開く
2. 回路定数を現物に合わせる
3. シミュレーション
4. 波形をCSV保存
5. `scripts/03_convert_ltspice_csv_to_calibration.py` でADC換算
6. WokwiのESP32しきい値へ反映

## テンプレート

```text
sensor_rc_filter/
  sensor_rc_filter.cir

voltage_divider_adc_protection/
  voltage_divider_adc_protection.cir

thermistor_divider/
  thermistor_divider.cir

relay_flyback/
  relay_flyback.cir
```

## 注意

このテンプレートは設計の出発点です。
実機投入前には、実部品の定格、絶縁、設備側仕様、ノイズ環境、安全要求を必ず確認してください。
