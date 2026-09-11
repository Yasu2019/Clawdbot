# OpenFOAM樹脂流動分析 — GPT-6引継ぎ

更新日: 2026-09-11  JST  
対象: `artifacts/box_roundhole_v5/`

## 現在の到達点

- OpenFOAM 2512 `compressibleInterFoam` を実行済み。
- カスタムCross-WLF粘度モデルを運動量方程式へロード済み。
- `T`, `rho`, `p/p_rgh`, `U`, `alpha.polymer`を使用。
- 粗密2ケースともソルバー完走、有限値、alpha境界、積分トレース、CalculiX連成監査PASS。
- ゲート・ベントのパッチ契約とメッシュ品質は両ケースPASS。

## 現行の粗密ケース

| 役割 | ケース | セル数 |
|---|---|---:|
| 粗 | `compressible_vof_vent_case_gmsh_coarse155` | 63,993 |
| 細 | `compressible_vof_vent_case_gmsh_refined15` | 67,165 |

両ケースの積分差は1e-3未満ですが、セル数比は1.0496であり、最低基準1.10を満たしません。したがって、正式な空間収束は未確立です。

## 重要な判定

- `SCREENING_PASS`: 仮想物性によるスクリーニング上の数値一致。
- `REVIEW`: セル数差不足。正式なメッシュ収束PASSへ昇格禁止。
- 材料係数・PVT・CTEは仮想値で、実測校正前。
- Tait EOSは現在の実装範囲と係数を再確認してから、完全連成を主張すること。

## 主な証拠ファイル

- `physics_mesh_comparison_gmsh_20260911.json`
- `mesh_pair_contract_20260911.json`
- `coupling_audit_gmsh_coarse155_20260911.json`
- `coupling_audit_gmsh_refined15_20260911.json`
- `ten_improvements_20260911.json`

## 再開時の優先順

1. 円形ゲート・4ベントの面積と法線契約を再検証。
2. 同一CAD・同一パッチでセル数比1.10以上の第3メッシュを生成。
3. `audit_mesh_pair_contract.py`で契約を監査。
4. 両ケースを同一条件で再計算。
5. 積分差、時間刻み収束、alpha境界、Cross-WLFロードを監査。
6. 基準未達なら`REVIEW`を維持し、PASSと表記しない。

## 主要コマンド

```powershell
python scripts/audit_mesh_pair_contract.py `
  --coarse artifacts/box_roundhole_v5/coupling_audit_gmsh_coarse155_20260911.json `
  --refined artifacts/box_roundhole_v5/coupling_audit_gmsh_refined15_20260911.json `
  --coarse-contract artifacts/box_roundhole_v5/patch_contract_gmsh_coarse155_20260911.json `
  --refined-contract artifacts/box_roundhole_v5/patch_contract_gmsh_refined15_20260911.json `
  --coarse-mesh artifacts/box_roundhole_v5/mesh_quality_gmsh_coarse155_20260911.json `
  --refined-mesh artifacts/box_roundhole_v5/mesh_quality_gmsh_refined15_20260911.json `
  --output artifacts/box_roundhole_v5/mesh_pair_contract_latest.json
```

## 安全方針

- 既存の監視・計算プロセスを停止、削除、上書きしない。
- 新ケースは一意のディレクトリ名で作成する。
- 実測校正前の結果は「仮想スクリーニング」と明記する。
- 目視・ログ・JSON証拠が揃わない結果を完了扱いにしない。
