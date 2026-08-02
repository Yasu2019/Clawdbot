# MF2010 全結果カタログ → CSV → DB（Play Macro）

Moldflow 結果 ID **全468件**を校正DBに載せ、NDDT+ELDT **453件**を在庫調査・可能なら CSV 化するパックです。

## DB（ローカル）
- `data/workspace/moldflow_bridge/mf_of_calibration.sqlite`
- テーブル `result_catalog` = 全 DsID（TXDT 含む）
- 再集約: `python scripts/mf_of_calibration_full_catalog.py`

## 手順（Play Macro のみ・schtasks 禁止）
1. Synergy×1、`mf_fc_warp_v2_20260720` を開く
2. **00** `C:\Users\mec21\Desktop\MF2010_AllResults_CSV_Fix\00_inventory_all_results.vbs`  
   - seed=453（30〜90分かかることがある）  
   - 出力: `Desktop\MF_AllResults_Export\`
3. **01** `01_preflight_all_results.vbs`
4. **02** `02_export_all_results.vbs`（export=1 を全節点 CSV）
5. ローカルで取り込み:
   ```
   python scripts/mf_of_calibration_full_catalog.py
   ```

## ステータス意味
| status | 意味 |
|---|---|
| available_in_db | CSV/KPI 済み |
| available_pending_csv | study 上にあるが未 CSV → 02 で取得 |
| unavailable_on_study | この Flow\|Warp に結果無し（DB のみ） |
| text_report_not_nodal | TXDT（テキスト表）節点 CSV 対象外 |
| catalog_pending_inventory | 00 未実行 / 旧 inventory |

## 禁止
schtasks / MOLDFLOW_EQUIVALENT 主張 / 全フレーム GetScalar 連打
