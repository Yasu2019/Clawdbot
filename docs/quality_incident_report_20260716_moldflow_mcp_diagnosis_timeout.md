# Moldflow 2010 MCP diagnosis timeout and safe repair API research

Date: 2026-07-16 JST  
Scope: Dynabook `DESKTOP-UOVCG4T`, Autodesk Moldflow Insight 2010, active `moldflow_study`

## Goal

Control and verify the user's Moldflow study through MCP without modifying the
original study unexpectedly.

## Confirmed facts

- MCP and 32-bit Synergy COM preflight are healthy.
- The unmeshed `moldflow_study_(copy).sdy` inspection completed in about 14 s.
- The meshed, gated `moldflow_study.sdy` caused:
  - `DiagnosisManager.GetMeshSummary(False)` to exceed 180 s.
  - direct `GetOverlapDiagnosis` / `GetAspectRatioDiagnosis` trial to exceed
    150 s.
- No analysis was started and no study was modified by these trials.
- Dynabook contains the version-matched primary reference:
  `C:\Program Files\Autodesk\Moldflow Insight 2010\help\synapi.chm`.

## Root cause analysis

### 5 Why

1. Detailed MCP inspection timed out because the synchronous diagnosis call did
   not return.
2. The current inspector requests a full mesh summary and then exports the full
   model to UDM for gate inspection.
3. The active repaired mesh causes the Moldflow 2010 diagnosis engine to perform
   a long or blocked recalculation.
4. External scripts currently use `CreateObject("synergy.Synergy")`, which can
   attach to the oldest Synergy instance rather than the explicitly selected
   instance.
5. The MCP bridge lacks separate bounded tools for identity, entity count,
   diagnosis, gate export, duplication, and repair, so one slow stage blocks the
   entire inspection.

### Fishbone

- API routing: oldest-instance attachment risk.
- Diagnosis: synchronous full-model recalculation.
- Study state: diagnostic layers or repair display can trigger automatic
  updates.
- Tool design: mesh summary and UDM gate export are coupled.
- Safety: original study must not be the first write target.

## Moldflow 2010 API capabilities confirmed from `synapi.chm`

### Safe study handling

- `Project.DuplicateStudyByName(name)`
- `Project.DuplicateStudyByName2(name, saveBeforeDuplicate)`
- `Project.GetFirstStudyName()` / `GetNextStudyName(name)`
- `StudyDoc.Save()` / `SaveAs(name)`

### Mesh repair

- `MeshEditor.AutoFix()` returns the number of overlaps/intersections removed.
- `GlobalMerge(tolerance, fusion)`
- `RemeshArea` / `RemeshArea2`
- `SwapEdge`
- `StitchFreeEdges2`
- `SmoothNodes`
- `FlipNormals`
- `FillHole`

### Mesh diagnosis

- `GetOverlapDiagnosis(overlaps, intersections, entityIds, values)`
- `GetOverlapDiagnosis2(..., visibleOnly, ...)`
- `GetAspectRatioDiagnosis(...)`
- `GetEdgesDiagnosis2(nonManifold, visibleOnly, ...)`
- `GetOrientationDiagnosis2(visibleOnly, ...)`
- `GetZeroAreaElementsDiagnosis2(...)`

## External public evidence

| Source | Access | Lesson |
|---|---|---|
| Autodesk Moldflow Synergy API documentation | direct_free | OLE/VBS macros can automate Synergy. |
| Autodesk University, Synergy API Part 1 | direct_free | Mesh-quality inspection and API scripting are supported use cases. |
| Autodesk Community meshing API example | direct_free | `MeshGenerator` plus `StudyDoc.MeshNow(False)` is supported. |
| Autodesk mesh diagnostics guidance | direct_free | Large-model diagnostics can take longer; restrict-to-visible can reduce recalculation cost. |
| Autodesk overlapping-elements guidance | direct_free | Overlaps/intersections must be corrected before analysis. |

No paywall, login bypass, bulk download, or restricted source was used.

## Proposed safe implementation

1. Bind to the exact Synergy instance rather than the oldest instance.
2. Add a fast identity/entity-count tool that does not call diagnostics or UDM
   export.
3. Separate gate inspection from mesh inspection.
4. Add a copy-only repair tool:
   - verify active study name;
   - duplicate it with `DuplicateStudyByName2`;
   - verify the duplicate is active;
   - call `MeshEditor.AutoFix()` once;
   - save the duplicate;
   - never call analysis.
5. Run bounded post-checks individually. If diagnosis remains slow, report the
   `AutoFix()` return count and use GUI Mesh Statistics for independent
   verification.
6. Keep the original study unchanged and provide rollback by deleting only the
   generated repair copy after explicit approval.

## Pass/fail gates

- PASS: exact intended study instance and name confirmed.
- PASS: duplicate exists before `AutoFix`.
- PASS: original study timestamp/hash is unchanged.
- PASS: `AutoFix()` returns within the timeout and its removal count is recorded.
- PASS: duplicate saves successfully.
- FAIL CLOSED: any modal dialog, instance ambiguity, timeout, or unexpected
  active-study change.
- Analysis remains prohibited until overlap/intersection acceptance is proven.

## Scope limits

- The investigation proves the necessary API exists.
- It does not yet prove `AutoFix()` completes on this specific repaired mesh.
- No write-capable repair call was executed during this investigation.

## Next experiment requiring user approval

Implement and run one copy-only `MeshEditor.AutoFix()` trial against a newly
duplicated `moldflow_study`, with no analysis and with the original preserved.

## First copy-only trial result

The first trial was executed after explicit user approval.

- Original active study verification passed: `moldflow_study.sdy`.
- `DuplicateStudyByName2` succeeded.
- New project item: `Moldflow_study (copy 2)`.
- The new copy opened successfully.
- `StudyDoc.StudyName` represented the same copy as
  `moldflow_study_(copy_2).sdy`.
- The fail-closed copy identity comparison rejected the formatting difference
  and exited with code 8 before calling `MeshEditor.AutoFix()`.
- No analysis was started.
- No AutoFix or save operation was performed by the trial.

### Root cause

Project item names preserve spaces and display parentheses, while SDY filenames
normalize those characters to underscores. The first implementation compared
only case and the `.sdy` extension.

### Countermeasure requiring confirmation

Normalize both names by removing `.sdy` and all non-alphanumeric characters
before comparison. Accept the copy only when the normalized values are exactly
equal and the copy name was absent from the pre-duplication study list. Then
retry `AutoFix()` once on the already-created copy, without creating another
duplicate.

## Approved retry result

- The user approved the canonical-name fix and retry.
- The active target was verified as `moldflow_study_(copy_2).sdy`.
- No additional study was duplicated.
- `MeshEditor.AutoFix()` completed in about 73 seconds.
- Return value: `580` overlaps/intersections removed.
- `StudyDoc.Save()` returned `True`.
- Analysis was not started.
- A post-repair `GetMeshSummary(False)` check still exceeded 180 seconds.

The repair call and save are proven. The remaining overlap/intersection count is
not proven through MCP and must be checked independently in the Moldflow Mesh
Statistics UI before analysis.

## Visual quality gate result

The user visually inspected `Moldflow_study (copy 2)` and reported a hole in the
mesh after AutoFix.

- The COM operation succeeded technically, but the repaired geometry failed the
  physical/visual quality gate.
- `AUTOFIX_REMOVED=580` must not be interpreted as a successful mesh repair.
- AutoFix likely removed intersecting/overlapping triangles without restoring a
  closed surface.
- `Moldflow_study (copy 2)` is prohibited as an analysis input.
- The original `moldflow_study` was not the AutoFix target and remains the
  rollback source.

### Revised decision rule

IF `MeshEditor.AutoFix()` reports removed elements, THEN require an independent
closed-surface or visual hole check before declaring success, BECAUSE defect
removal can create missing surface triangles. Never start Fill, Pack, Cool, or
Warp on an AutoFix copy with visible holes.
