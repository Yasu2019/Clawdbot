# Moldflow 材料物性データベース利用ガイド（全AIモデル共通）

## 1. 概要
Autodesk Moldflow Insight 2010 の材料データベース（全8,161件）より抽出した、Cross-WLF粘度モデル係数、2領域修正Tait pvT状態方程式係数、CRIMS収縮モデル係数、熱物性（比熱・熱伝導率）、機械物性（弾性率・ポアソン比・剛性）のリレーショナルデータベースです。

## 2. ファイル配置一覧
- **SQLite データベース**: `data/workspace/moldflow_materials.db`
- **フラット CSV**: `data/workspace/moldflow_materials_full.csv`
- **カタログ JSON**: `data/workspace/materials_catalog_normalized.json`
- **個別材料カード**: `data/workspace/moldflow_bridge/material_cards/<ID>_<TradeName>.json`
- **Turso Cloud DB**: `clawstack-knowledge` (テーブル: `moldflow_materials`, `moldflow_cross_wlf`, `moldflow_pvt_tait`, `moldflow_crims`, `moldflow_thermal_mechanical`)

## 3. SQLクエリの書き方

### ① 特定の材料（例: 住友ノーブレン AY564）の全物性を取得
```sql
SELECT 
    id, family, trade_name, manufacturer,
    wlf_n, wlf_tau_star, wlf_d1, wlf_d2_c,
    pvt_b5_c, pvt_b1m, pvt_b2m,
    crims_a1, crims_a2, crims_a3,
    cp, k, e1_mpa, nu12, g12_mpa
FROM v_materials_full 
WHERE id = 53781 OR trade_name LIKE '%AY564%';
```

### ② 物性取得済みの全材料一覧を取得
```sql
SELECT id, family, trade_name, manufacturer, wlf_n, wlf_tau_star, cp, k, e1_mpa 
FROM v_materials_full 
WHERE has_full_properties = 1;
```

### ③ Python からの直接読み込み
```python
import sqlite3
import csv

# SQLiteから読み込み
conn = sqlite3.connect("data/workspace/moldflow_materials.db")
cur = conn.cursor()
cur.execute("SELECT * FROM v_materials_full WHERE has_full_properties=1")
rows = cur.fetchall()
print(f"Loaded {len(rows)} materials from SQLite.")
```
