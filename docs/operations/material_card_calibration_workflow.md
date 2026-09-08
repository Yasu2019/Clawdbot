# 実測材料データを計算へ反映するワークフロー

このリポジトリの結果は、材料カードの係数を計算辞書へ変換してから
OpenFOAM の熱物性・Cross-WLF 粘度・Tait 密度連成へ渡す。したがって、
仮想値を実測値で置換する場合も、ソルバー本体を改造せずに同じ計算経路を
再現できる。

## 入力契約

`config/material_card_schema.json` の必須セクションを埋める。

- `thermal`: 密度、比熱、熱伝導率。温度依存値がある場合は代表値ではなく、
  温度範囲と測定ファイルをカードの `data_sources` に記録する。
- `cross_wlf`: 複数温度・せん断速度・圧力で同定した Cross-WLF 係数。
- `tait_two_domain`: PVT の比容積–温度–圧力データから同定した係数。
- `structural`: 固化後の弾性率、ポアソン比、線膨張係数。収縮・反りの基準片も
  `data_sources` に記録する。

単位は K、Pa、Pa.s、kg/m3、J/(kg.K)、W/(m.K) に統一する。測定元の単位を
  そのまま混ぜない。

## 変換とゲート

```powershell
py -3 scripts/prepare_material_card.py `
  --card config/my_measured_pp.json `
  --output artifacts/material_cards/my_measured_pp/generalizedPolymerThermo `
  --case artifacts/box_roundhole_v5/my_measured_pp_case
```

生成された `generalizedPolymerThermo` は Cross-WLF と Tait の係数を含み、
`material_card_preflight.json` はデータ状態と辞書の対応を記録する。
`--case` を指定した場合だけ、その辞書をケースの
`constant/generalizedPolymerThermo` へインストールするため、どの計算がどの
材料カードを使ったかを再現できる。
`VIRTUAL_SCREENING_ONLY` はスクリーニング専用、`MEASURED_UNCALIBRATED` は
実測値入力済みだが校正前、`CALIBRATED`/`VALIDATED` だけが設計判断用の
校正ゲートを通る。仮想カードは意図的にゲートが閉じたままである。

## 校正の順序

1. PVT から Tait 係数を同定し、圧力方程式との質量保存・密度履歴を確認する。
2. レオロジーから Cross-WLF 係数を同定し、充填圧力・流量・温度履歴を確認する。
3. 比熱・熱伝導率を入力し、熱電対または金型温度履歴で熱モデルを校正する。
4. 寸法、収縮、反り、ヒケ、エアートラップ、ウェルドラインを基準片と比較し、
   誤差と測定条件を履歴へ保存する。
5. 未使用条件のホールドアウトで再検証し、`VALIDATED` へ昇格する。

実験データが追加されるほど結果が改善するのは、単にファイルを保存するから
ではなく、上記の係数が実際に `generalizedPolymerThermo` を通って運動量・
圧力・熱方程式へ入るためである。測定点が少ない場合や条件外への外挿では、
精度向上を保証せず、誤差評価を併記する。
