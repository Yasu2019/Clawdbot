# MF2010 Cool + Flow + Warp AllResults CSV

対象Study: `mf_strip_cool_v12_20260720_1.sdy`

出力先: `C:\Users\mec21\Desktop\MF_CoolFlowWarp_AllResults_Export_20260802`

## 実行方法

Synergy 2010で対象Studyを開き、必ず `Play Macro` から次の順に実行する。

1. `00_inventory_all_results.vbs`
2. `01_preflight_all_results.vbs`
3. `02_export_all_results.vbs`

`schtasks`、SSH経由の`cscript`、Explorerからのダブルクリックは禁止。

## 合格条件

- Synergyプロセスが1個であること。
- Active Study名に `mf_strip_cool_v12_20260720_1` が含まれること。
- `01` が `PREFLIGHT PASSED` で終了すること。
- `02` の最終ログが `DONE ok=<n> fail=0` であること。
- 出力先に `.part` が残っていないこと。

Cool、Flow/Pack、Warpを同一StudyからInventoryする。利用できないDsIDは
`unavailable_on_study`として記録し、推測値をCSVへ書かない。

精度ラベルは常に `PROXY_GAP`。`MOLDFLOW_EQUIVALENT`は禁止。
