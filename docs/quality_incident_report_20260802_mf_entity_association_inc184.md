# INC-184: Moldflow result association misclassified as nodal

## Summary

- Date: 2026-08-02 JST
- Detection: `mf_structural_benchmark_pack.py` rejected shrinkage IDs absent from the NODE set.
- Impact: New benchmark generation stopped before manifest completion. Moldflow CSV originals, OpenFOAM runs, and the active LAVIE job were not modified.
- Accuracy label: `PROXY_GAP` remains mandatory.

## Observed facts

| Dataset | Actual association | Evidence |
|---|---:|---|
| `deflection_all_effects` | NODE | field-pack association metadata and coordinate join |
| `temperature_nodal` | NODE | field-pack association metadata and coordinate join |
| `volumetric_shrinkage_ejection` | TRI3 | 3552 rows and field-pack `association_counts.TRI3=3552` |
| residual principal stresses | TRI3 | field-pack association metadata |

The raw CSV identifier header is `NodeID` for results that are actually associated with TRI3 entities. The geometry export contains separate NODE, TRI3, and 1DET ID namespaces; IDs may overlap and therefore cannot be classified by numeric membership alone.

The current `openfoam_multiphysics_field_pack_v1/manifest.json` passes Python standard-library `json.loads`, and its Cooling STL path is valid UTF-8 JSON. The earlier PowerShell `Get-Content | ConvertFrom-Json` failure came through a Windows PowerShell text-decoding path without an explicit UTF-8 read. Python strict parsing is the authoritative gate; PowerShell consumers must use an explicit UTF-8 read.

## 5 Whys

1. Why did benchmark generation stop? Shrinkage identifiers were not present in the NODE coordinate set.
2. Why were they required to be NODE IDs? The first implementation assumed every CSV `NodeID` column was nodal.
3. Why was the header trusted? The exporter uses a common identifier header while result association varies by plot/result type.
4. Why was association metadata not consumed? The benchmark prototype read raw CSVs directly instead of an independently validated association catalog.
5. Why was this not caught before output? The gate checked foreign IDs, which correctly failed, but there was no per-field association contract test before generation.

## Fishbone / logical tree

- Data semantics: common `NodeID` label hides NODE/TRI3/1DET association.
- Identifier model: entity namespaces overlap numerically.
- Interface: benchmark input lacked an explicit `association` property per field.
- Serialization/consumer: Windows PowerShell read UTF-8 JSON without an explicit UTF-8 encoding.
- Verification: no matrix test covering nodal and elemental reference fields.

## FMEA

| Failure mode | Effect | Severity | Detection | Countermeasure |
|---|---|---:|---:|---|
| TRI3 field treated as NODE | spatially incorrect loads/reference | 10 | foreign-ID gate | explicit association catalog; never infer from header |
| overlapping entity IDs joined by number only | silent wrong geometry | 10 | association-aware join count | composite key `(association, entity_id)` |
| PowerShell encoding-dependent JSON read | false invalid-manifest diagnosis | 5 | Python strict JSON parse | require explicit UTF-8 in PowerShell consumers |
| MF reference used as CalculiX load | validation leakage | 10 | manifest policy gate | reference/load directory separation and provenance check |

## Countermeasure implementation plan

1. Verify the existing multiphysics manifest with Python `json.load`; require explicit UTF-8 for PowerShell consumers.
2. Add a field-association catalog using explicit NODE/TRI3/1DET metadata.
3. Change benchmark summaries to validate composite `(association, entity_id)` keys.
4. Emit CalculiX geometry from NODE+TRI3 only; keep every MF result in a separate `reference_only` section.
5. Add mixed-association tests for NODE deflection/temperature and TRI3 shrinkage/stress.
6. Run a zero-load CalculiX mesh smoke test, then accept physical loads only from an independently identified OpenFOAM run.

## Decision rule

IF a Moldflow result is imported, THEN its entity association must be obtained from validated result metadata and joined using `(association, entity_id)`, BECAUSE the CSV identifier header and numeric ID alone do not identify the geometry namespace.

## Verification and rollback

- Pass: all selected fields join 100% in their declared association; strict JSON parse succeeds; no Moldflow reference appears in the CalculiX load section.
- Fail: any inferred association, foreign composite key, ambiguous overlapping key, strict JSON parse failure, or reference-to-load provenance.
- Rollback: delete only the new incomplete `calculix_structural_benchmark_v1` output and revert the new benchmark script. Source exports remain read-only.

## Scope limits / next experiment

This incident does not prove OpenFOAM or CalculiX accuracy. The smallest next experiment is rebuilding the benchmark with explicit association metadata and verifying the mixed NODE/TRI3 matrix before any solver run.

## Provenance

- `data/workspace/moldflow_bridge/mf_coolflowwarp_all_results_20260802/`
- `scripts/mf_structural_benchmark_pack.py`
- `openfoam_multiphysics_field_pack_v1/manifest.json`
- Date: 2026-08-02 JST
