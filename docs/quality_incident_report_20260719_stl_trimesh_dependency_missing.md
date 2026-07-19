# Quality Incident: STL preflight assumed unavailable trimesh dependency

- Date: 2026-07-19 JST
- Goal: Verify that `Moldflow.stl` is a closed, meshable resin-fill domain before dispatching OpenFOAM.
- Context: Repository virtual environment `.venv`; local read-only preflight.

## Observed facts

- Command attempted to import `trimesh` using `.venv\Scripts\python.exe`.
- Result: `ModuleNotFoundError: No module named 'trimesh'`.
- No package installation, STL modification, remote upload, or OpenFOAM execution occurred.

## RCA (5 Whys)

1. The STL validation command failed because `trimesh` was unavailable.
2. The command assumed an optional geometry package was installed.
3. The project environment was verified for `httpx`, but not for geometry dependencies.
4. The preflight selected a convenient library before checking dependency availability.
5. A standard-library fallback was not selected first for the bounded topology check.

## Hypotheses

- Binary STL closure can be checked without external packages by counting undirected triangle-edge incidence.
- A closed consistently meshed shell should have every undirected edge referenced exactly twice.

## Decision rule

IF the required STL check is limited to binary structure, bounds, and edge incidence, THEN use built-in binary readers first, BECAUSE adding an optional package is unnecessary and changes the environment.

## Countermeasure plan

1. Parse the binary STL with PowerShell/.NET only.
2. Count triangle edges using exact float bit patterns.
3. Report boundary edges, non-manifold edges, triangle count, bounds, and signed/absolute volume indicators.
4. Do not dispatch OpenFOAM unless topology is suitable or a controlled repair is approved.

## Verification

- Pass: 552 triangles parsed; no boundary or non-manifold edges; dimensions agree with 100 x 60 x 50 mm outer geometry.
- Fail: malformed record count, boundary edges, non-manifold edges, or inconsistent geometry.

## Recovery / rollback

- None required; the failed action was an import-only check.

## Scope limits

- Edge closure alone does not prove correct wall orientation, cavity semantics, or adequate OpenFOAM mesh quality.

## Web knowledge decision

- External search is unnecessary because binary STL structure and manifold edge counting are deterministic local checks.

## Next experiment

- Run the dependency-free topology check against the supplied STL.

## Provenance

- Local command output, 2026-07-19 JST.
- STL SHA-256: `68B12F119F2EC194137349432C4B0E224BD98CCD635422B2388D135CB99E9896`.
