# OpenFOAM樹脂流動メッシュ収束ノウハウ

## 確立事項

- `compressibleInterFoam` + custom Cross-WLF transport plugin は、`T`、`rho`、`p/p_rgh`を参照して運動量方程式へ粘度を連成する。
- 円形ゲート・4ベントのパッチ契約は、面積・法線・パッチ名をJSON契約で監査する。
- 粗密両ケースで solver 終了、alpha境界、Cross-WLFロード、粘度場、質量/樹脂体積/熱積分、CalculiX結果を確認する。

## 収束判定の注意

- 現在の粗密セル数は63,993と67,165、比率1.0496。
- 積分値の差は1e-3未満だが、解像度差が小さいため正式な空間収束は`REVIEW`。
- 同一セル数、パッチ契約不一致、またはセル比1.10未満は、収束PASSへ昇格させない。
- 未校正の樹脂係数・PVT・CTEは仮想スクリーニングとして表示する。

## 再利用する監査

- `scripts/audit_mesh_pair_contract.py`
- `scripts/compare_openfoam_integral_runs.py`
- `scripts/audit_cross_wlf_shrinkage_coupling.py`
- `scripts/run_ten_improvements.py`

## 証拠

- `artifacts/box_roundhole_v5/physics_mesh_comparison_gmsh_20260911.json`
- `artifacts/box_roundhole_v5/mesh_pair_contract_20260911.json`
- `artifacts/box_roundhole_v5/ten_improvements_20260911.json`

## 次の改善

同一CAD・同一ゲート/ベント面積を維持したまま、セル比1.10以上の第3メッシュを生成し、同一物性・射出条件で再計算する。

記録先: Beads issue、Obsidian Markdown、ByteRover local context、graphify corpus、GitHub。Tursoは資格情報と対象スキーマを確認できた場合のみ同期する。
