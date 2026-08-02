# Quality incident report: Moldflow mixed result entity IDs

## Summary

- Date: 2026-08-02 JST
- Detection: post-export join gate after `03_export_node_coordinates.vbs`
- Impact: direct spatial packing was blocked before OpenFOAM injection. No solver case,
  Study, source CSV, or prior export was modified.
- NG evidence: 1,818 valid node coordinates; typical 3,552-row result joined only
  1,093 IDs (30.77%); four 40-row circuit fields joined 0 IDs.
- Accuracy label remains `PROXY_GAP`; no Moldflow-equivalence claim is permitted.

## 5 Why

1. Why did full spatial joining fail? Result identifiers were not all mesh-node IDs.
2. Why were they treated as nodes? The Moldflow `Get*Data` integer array was exported
   under the generic header `NodeID`.
3. Why was that ambiguous? Dataset association differs: nodal, TRI3 elemental, and
   cooling-circuit 1DET results coexist in the same study.
4. Why did 03 not solve it? 03 correctly enumerated nodes only; it had no element
   connectivity or centroids.
5. Why was this detected late? The original export gate checked row count and finite
   values, but not association type plus coordinate-join coverage.

## Fishbone / logical tree

- API semantics: integer entity array is dataset-dependent.
- Data schema: `NodeID` name erased association type.
- Geometry: nodes, TRI3 faces, and 1DET cooling circuits require different locations.
- Validation: no per-field join-fraction promotion gate existed.
- Process: coordinate export was added after result export rather than designed into
  the first manifest.

## FMEA

| Failure mode | Effect | S | O | D | Countermeasure |
|---|---|---:|---:|---:|---|
| TRI3 ID treated as node | wrong field position | 9 | 7 | 3 | export TRI3 centroid/connectivity |
| 1DET ID treated as node | Cool field absent | 9 | 6 | 2 | export 1DET centroid/connectivity |
| UDM m treated as mm | 1000x geometry error | 10 | 4 | 2 | COM reference scale gate |
| partial geometry promoted | silent sparse mapping | 9 | 3 | 2 | atomic `.part` and declared-count gates |

## Countermeasure and verification

`04_export_entity_geometry.vbs` performs a read-only temporary UDM export, parses
`NODE`, `TRI3`, and `1DET`, calculates centroids from connectivity, validates declared
UDM counts, validates UDM-to-mm scale against a live COM node, and promotes output
only when missing connectivity and malformed counts are zero.

Pass criteria after execution:

- `nodes=1818`, `tri3=3552`, `1D=40` for the current study (exact live UDM counts win).
- no `.part` or temporary UDM remains;
- all exported result IDs join 100% to the declared association geometry;
- circuit results join to `1DET`, not `NODE`;
- output remains an intermediate `PROXY_GAP` reference, not a solved OF field.

## Rollback and scope

Delete only the newly generated entity-geometry CSV/log if rejected; 00-03 and all
source results remain intact. This correction proves entity placement, not physical
equivalence, mesh interpolation accuracy, or Cool/Flow/Warp solver equivalence.

Web search was not used: the local MF2010 UDM V4 artifact contained the exact record
grammar and counts; public documentation could not supersede this version-specific
evidence.

