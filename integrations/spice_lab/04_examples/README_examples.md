# SPICEサンプル回路

## rc_lowpass_ngspice.cir

5Vパルス入力を1kΩ + 1µFで平滑する例です。時定数は約1msです。

## divider_tolerance_sweep.cir

分圧回路の基礎テンプレートです。Python側でR値を変更して許容差検討に使います。

## sensor_input_filter.cir

PLC/測定器/ADC入力を想定した簡易RCフィルタです。

## surge_clamp_template.cir

保護回路のたたき台です。実際のTVS/ダイオードモデルは必ずメーカーSPICEモデルに置き換えてください。
