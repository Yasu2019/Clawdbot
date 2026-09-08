# 穴付き箱モデル run4 充填・ウエルド候補計算

## 計算

- ケース: `artifacts/box_roundhole_v5/open_top_shell_run4_weld_qc`
- OpenFOAM `interFoam`, 4並列、0–5 s
- ゲート速度: 8 m/s、ベント境界あり
- 終了: `End`、累積連続誤差 5.39e-6
- 最終平均樹脂相率: 0.86833898
- 最終 `alpha.polymer` 最大: 1.0000013（軽微な数値オーバーシュートを記録）
- 最大Courant: 0.4996

## ウエルド候補

`postProcess -func writeCellCentres` 後、
`scripts/derive_openfoam_weldline_kpis.py` を実行。初回 `alpha.polymer >= 0.5`
到達時刻の遅い空間リッジから12候補を抽出した。

- 出力: `artifacts/box_roundhole_v5/open_top_shell_run4_weld_qc/weldline_kpis.json`
- `formal_status`: `PROXY_ONLY`
- `accuracy_band`: `PROXY_GAP`

候補はウエルド位置のスクリーニングであり、接合強度・配向・品質を保証しない。

## 目視確認と送信

初期・中間・最終フレームを目視確認し、樹脂領域の進展を確認した。
アニメーションは `artifacts/box_roundhole_v5/box100x60x50_open_top_shell_run4_weld_qc.mp4`。
目視確認後、Telegramへ送信成功。

## 制限

86.8%であり完全充填ではない。実測射出流量、材料カード、冷却・PVT校正がないため、
設計判断用の正式結果ではない。次段階は、実射出条件に合わせた流量校正と、候補場を
表示する専用ウエルドオーバーレイである。
