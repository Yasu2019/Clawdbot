# 任意3D・7現象CAE 実装記録 2026-09-20

## 1. Goal

任意のSTL/STEP形状について、OpenFOAMの充填履歴を起点にCalculiX/Elmerへ履歴を渡し、樹脂充填、反り、収縮、ヒケ、ボイド、エアートラップ、ウエルドラインを、代理表示と直接・連成計算を混同せず最後まで判定できる構成にする。

## 2. Context

- Machine: K10 / Windows、repository `D:/Clawdbot_Docker_20260125`
- Branch: `feature/inc187-snappy-thermo-fix-20260803`
- OpenFOAM target: v14系の非等温・圧縮性VOF
- Structural target: CalculiX。Elmerは独立比較
- Material: 現在は仮想データ。実測校正前のため工学的妥当性は主張しない
- Protected concurrent work: `k10_tri_track_cae_orchestrator.py` と `k10_thinkpad_dxf2step_loop.py` は停止・上書きしない

## 3. Observed facts

- 旧OpenFOAM production runnerは、既存時刻フォルダとCLI指定の収支誤差0だけで `COMPLETED` にできた。
- 旧任意形状extractorはSTEPを拒否し、face index JSONだけを出し、HOLDでもexit 0だった。
- 旧CalculiX履歴deckはeigenstrain CSVをコメントとして残すだけで、構造荷重に適用していなかった。
- OpenFOAM cell ID、CalculiX node ID、element IDが同じID列として扱われ得る断線があった。
- 修正後の対象テストは `62 passed in 6.47s`。隔離先は `artifacts/pytest_tmp_cae_completion_r5`。
- 途中で `numpy.bool_` がJSON化できない回帰を1件検出し、標準 `bool` へ正規化して再試験した。
- CalculiX公式仕様では、時系列固有ひずみは `*INITIAL CONDITIONS, TYPE=PLASTIC STRAIN` の後に各stepで `*INITIAL STRAIN INCREASE` を加算できる。
- Docker `calculix/ccx:latest` (CalculiX 2.16) で単一C3D4・2段階固有ひずみを実solveし、return code 0、DAT/FRD/STA非空、FRD DISPありを確認した。
- 第2段階 `E=-0.01` の自由辺長はCalculiX `0.0098994949 m`、Green-Lagrange解析解 `0.0098994949366 m`、軸変位 `-1.005051e-4 m`であり、設定した許容帯をPASSした。
- 7現象truth gateを追加し、同一geometry/mesh/history ID、実solver証拠、収束性、現象別空間・時系列evidenceをfail-closedで検査できるようにした。

Sources:

- CalculiX `*INITIAL STRAIN INCREASE`: https://feacluster.com/CalculiX/ccx_2.18/doc/ccx/node290.html
- CalculiX `*TEMPERATURE`: https://www.feacluster.com/CalculiX/ccx_2.18/doc/ccx/node339.html
- CalculiX `*EXPANSION`: https://www.feacluster.com/CalculiX/ccx_2.18/doc/ccx/node270.html

## 4. Hypotheses

- Hypothesis H1: 実OpenFOAM履歴にsolver log、solver由来収支、mesh/history SHA、複数時刻、full-fill指標を必須化すれば、仮想VTUや途中時刻を本番完走と誤認する経路を閉じられる。
- Hypothesis H2: CAD/process semanticsでgate/ventを明示し、surface topologyとpatch面積を照合すれば、座標固定のケースより任意形状へ一般化できる。
- Hypothesis H3: 固化収縮total strainをframe差分へ変換してCalculiX integration pointへ加算すれば、履歴の二重加算を避けられる。

## 5. Decision rule

- IF raw multi-time OpenFOAM history、full-fill、solver終了ログ、solver由来mass/energy audit、mesh/history fingerprintの一つでも欠ける THEN OpenFOAM結果はHOLD BECAUSE 時刻フォルダの存在だけでは完走証拠にならない。
- IF gate/vent/wallがJSONに宣言されただけでsurface topologyとpatch artifactがない THEN arbitrary-3D boundaryはHOLD BECAUSE patch名は実mesh境界を証明しない。
- IF `shrinkage_counting=eigenstrain_only` なのにeigenstrain履歴、element ID、integration-point map、strain measure、reference configurationの一つでも欠ける THEN deck生成を拒否する BECAUSE nodal temperatureとelement eigenstrainは別のID空間・物理量である。
- IF outputがproxy/candidateである THEN production completeへ昇格しない BECAUSE 可視化候補は欠陥の直接予測ではない。

## 6. Procedure

1. `extract_arbitrary_model_boundaries.py` でSTL/STEPを読み、watertight、manifold、orientation、enclosed volumeを検査する。
2. sidecar selectorでgate/vent/holeを定義し、各groupを個別STLとBoundaryContractへ出力する。
3. OpenFOAM solve後、`run_openfoam_production_history.py` にraw logとsolver由来balance auditを渡す。
4. manifest gateがPASSした履歴だけを `run_multiphysics_coupling_package.py` へ渡す。
5. `cte_only` はnode mapping、`eigenstrain_only` はelement/IP mappingとして分離する。
6. eigenstrain total historyを差分化し、CalculiX deckへ初期strainとstep incrementとして出力する。
7. CalculiXとElmerを独立solveし、FRD/DAT/Elmer result、mesh/time convergence、geometry/history ID一致を検証する。
8. 各現象のmanifestをtruth gateへ渡し、screeningとengineering validationを分離する。

## 7. Verification

- Unit/regression: 次のコマンドがexit 0かつ62件PASS。

  `python -m pytest tests/test_cae_multiphysics_contract.py tests/test_ccx_continuous_reanalysis_deck.py tests/test_run_multiphysics_coupling_package.py tests/test_openfoam_production_history_runner.py tests/test_arbitrary_model_boundaries.py tests/test_cae_multiphysics_readiness_gate.py tests/test_run_cae_7track_acceptance.py -q --basetemp artifacts/pytest_tmp_cae_completion_r5`

- Boundary PASS条件: required patch非空、全face一意分類、watertight、manifold、orientation consistent、nonzero volume、model/spec SHA、patch STLあり。
- OpenFOAM PASS条件: `T,p,alpha,U,rho`、時刻2以上、単調時刻、alpha bound、mean/filled-cell full-fill、終了ログ、収支許容内、fingerprint一致。
- CalculiX固有ひずみPASS条件: C3D4、IP=1、element ID一致、total Green-Lagrange normal strain、stress-free geometry、各step差分。
- CalculiX実行スモーク: `python scripts/verify_ccx_eigenstrain_smoke.py --output-dir artifacts/ccx_eigenstrain_smoke_root_20260920_1225 --solve --timeout-s 300`。`SOLVED_ANALYTICAL_SMOKE_PASS`。
- 7現象truth gate単体試験: `python -m pytest tests/test_cae_seven_phenomena_truth_gate.py -q`。`5 passed, 3 subtests passed`。
- 本番完了にはactual OpenFOAM full-fill、actual ccx、actual Elmer、収束性、動画目視QAが別途必要。

## 8. Failure signatures

- `FOAM FATAL ERROR`、`SIGFPE`、`Negative initial temperature`: solver完走証拠を拒否する。
- `declared_cli_unverified`: mass/energy値がsolver由来でないためHOLD。
- `eigenstrain history is required when shrinkage_counting=eigenstrain_only`: 収縮履歴未接続。
- `target_entity` mismatch: nodeとelement IDの混同。
- `Object of type bool is not JSON serializable` かつ実型が `numpy.bool_`: JSON前の標準型変換漏れ。
- `WinError 5` at shared pytest cleanup: 共有basetemp競合。個別 `--basetemp` で再実行する。

## 9. Recovery / rollback

- 編集前baseline: commit `eb846de579`。
- 第1改善: commit `e6b434ec59`。
- 問題発生時は破壊的resetを使わず、対象commitから必要ファイルを別worktreeへ取り出して比較する。
- 既存解析プロセスは停止せず、case directoryとPIDを確認して別artifact pathで試験する。

## 10. Scope limits

- 現時点でactual arbitrary-geometry full-fill solveは未証明。
- 固有ひずみ直接適用はC3D4、IP=1、等方Green-Lagrange strainに限定。
- eigenstrain pathの物理温度はelement CSV監査保持であり、nodal temperatureとの同時適用は未完了。
- pressure face load、内外面方向、fixture release、Elmer同一履歴solveは本番証拠が未完了。
- sink、airtrap、weldline、voidの既存多くはproxy/candidate/reduced physicsであり、production defect predictionではない。
- 実測PVT/Cross-WLF/CTE未校正のため、完走しても `UNCALIBRATED_SCREENING` とする。

## 11. Next experiment

1. 単一C3D4拘束モデルをDocker `calculix/ccx:latest` でsolveし、負の固有ひずみに対する変位符号と倍率を解析解比較する。
2. BoundaryContract patch STLをsnappyHexMesh builderへ接続し、生成後のpatch face数・面積を契約と照合する。
3. 同一geometry/history IDを要求する7現象truth gateを通し、不足項目を機械的に次の実装対象へする。

進捗: 1と3の実装・単体検証は完了。2のOpenFOAM case builder接続とElmer独立solveを実行中。

## 12. Provenance

- Date: 2026-09-20 JST
- Beads: `Clawdbot_Docker_20260125-7y81`
- Commits: `eb846de579`, `e6b434ec59` (本追記時点の追加実装は未commit)
- Primary files: `scripts/run_openfoam_production_history.py`, `scripts/cae_multiphysics_contract.py`, `scripts/extract_arbitrary_model_boundaries.py`, `scripts/build_ccx_continuous_reanalysis_deck.py`, `scripts/cae_multiphysics_readiness_gate.py`
- Added verification: `scripts/verify_ccx_eigenstrain_smoke.py`, `scripts/cae_seven_phenomena_truth_gate.py`
- CalculiX evidence: `artifacts/ccx_eigenstrain_smoke_root_20260920_1225/ccx_eigenstrain_smoke_report.json`
- Graphify: existing graph queried for arbitrary geometry, fill, warpage, shrinkage, sink, void, airtrap, weldline dependencies
- External references: CalculiX official/manual mirrors listed above
