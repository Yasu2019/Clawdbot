# Quality Incident: LAVIE exec_bridge HTTP 500 during r32 field retrieval

Date: 2026-08-01 JST

## Goal and impact

Retrieve OpenFOAM r32 cell centres for Moldflow full-field mapping. The LAVIE
job worker and previously generated MF/OF artifacts were not modified. Impact
is limited to blocking remote cell-centre retrieval; local field-pack creation
completed independently.

## Observed facts

- The LAVIE worker health endpoint returned status `ok` earlier in the session.
- Every command sent through `:5679/webhook/exec_bridge` returned HTTP 500.
- Ten bounded read-only probes failed identically, including file existence,
  directory listing, WSL listing, and log reads.
- No remote stop, delete, overwrite, solver launch, or container mutation ran.

## RCA

### 5 Whys

1. Cell centres were not retrieved because remote commands returned HTTP 500.
2. Commands could not execute because the n8n exec_bridge workflow failed before returning output.
3. Exact workflow-node failure is unknown because the endpoint returned no diagnostic body.
4. Retrieval depends on one n8n bridge although worker health is independent.
5. The artifact-return contract exposes no read-only completed-run file API.

### FTA / Fishbone summary

- Transport: n8n webhook/workflow failure is confirmed at HTTP layer.
- Command quoting: ruled out as sole cause; simple `dir` probes also failed.
- Solver/converter: ruled out; local converter tests passed without LAVIE.
- Network: endpoint was reachable and returned HTTP 500, not timeout/refusal.
- Web knowledge: not useful for a private workflow/configuration failure with direct local evidence.

## Countermeasures

1. Keep CSV conversion independent from remote case retrieval.
2. Add a bounded read-only completed-artifact endpoint or worker return bundle.
3. Keep `PROXY_GAP` until target-cell mapping and interpolation gates pass.
4. Do not restart n8n or LAVIE while unrelated jobs may exist.

## Verification and scope limits

- Local 16-field pack passed; all coordinate joins are complete.
- Remote r32 cell centres were not retrieved.
- The exact failing n8n node remains unknown; its execution log is the smallest next experiment.

## Recovery / rollback

No remote state changed. Removing only the new local field-pack folder rolls
back generated artifacts; source CSVs and r32 remain intact.

## Provenance

- Issue: `Clawdbot_Docker_20260125-zyko`
- Backup: `94f11b33ee5bd8b502276287a447905b76d0cb70`
- Script: `scripts/mf_csv_to_openfoam_field_pack.py`
- Output: `data/workspace/moldflow_bridge/mf_minusx_copy_results_20260801/openfoam_field_pack_v1/`
