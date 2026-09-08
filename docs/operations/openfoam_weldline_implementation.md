# OpenFOAM ウエルドライン候補の実装

`scripts/derive_openfoam_weldline_kpis.py` は、OpenFOAM の複数時刻
`alpha.polymer` とセル中心 `C` から、各セルの初回充填時刻を求め、遅い充填
フロントの空間リッジをウエルドライン候補として抽出する。

```powershell
docker run --rm --mount "type=bind,source=$((Resolve-Path $case).Path),target=/case" `
  opencfd/openfoam-dev:latest bash -lc 'cd /case && postProcess -func writeCellCentres'
py -3 scripts/derive_openfoam_weldline_kpis.py `
  --case artifacts/box_roundhole_v5/virtual_pp_thermal_r4 `
  --output artifacts/box_roundhole_v5/virtual_pp_thermal_r4/weldline_kpis.json
```

出力は `PROXY_ONLY` であり、ウエルド強度・配向・接合品質を計算したものでは
ない。候補数が0の場合も「ウエルドラインなし」とは解釈せず、複数フロントが
合流するだけの充填履歴がない、または充填が不十分である可能性を示す。

動画をTelegramへ送信する前に、少なくとも初期・中間・最終フレームを目視し、
樹脂の充填進展と候補場の表示が一致することを確認する。目視未確認の動画は
完了成果物として扱わない。
