# 穴付き箱型モデル仮想PP熱連成計算 r4

## 実行

- モデル: 開口箱 100 x 60 x 50 mm、底面φ20 mm貫通穴、φ4 mmゲート2個、φ2 mmベント2個
- ケース: `artifacts/box_roundhole_v5/virtual_pp_thermal_r4`
- 材料: `VIRTUAL_SCREENING_ONLY` の代表PPカード（実験校正なし）
- ソルバー: custom `polymerInterFoam`（Cross-WLF粘度、Tait密度、熱方程式）
- 時間: 0–0.0002 s、Δt=1e-7 s、2000 step、`End`

## 数値結果

- 最終 `alpha.polymer` phase-1 volume fraction: 0.00072089993
- 最終温度bound: 489.48749–503.49194 K（温度イベントは記録するが計算は継続）
- 最大速度: 0.34685643 m/s
- `p_rgh`: 101022.54–101882.25 Pa
- 最終 max Courant: 0.00017560279

## 出力

- VTK: `artifacts/box_roundhole_v5/virtual_pp_thermal_r4/VTK`
- アニメーション: `artifacts/box_roundhole_v5/box100x60x50_virtual_pp_thermal_r4.mp4`
- Telegram: 動画送信成功（約0.03 MB）

## 注意

これは実測材料で校正していないスクリーニング結果であり、実製品の充填時間・収縮・反り・ヒケを保証しない。実測カード投入後、同じケースを再実行し、温度・圧力・収縮・反りの実験値比較を行う。
