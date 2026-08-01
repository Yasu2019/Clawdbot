# INC-181: OpenFOAM Cool CAD prebuild missing gate_count

## Event / impact

- Trial: `lavie-mfminusx-cool-20260802-urgent01`
- Signature: `Moldflow CAD build failed: gate_spec_path or gate_count required for CAD build`
- Impact: empty run directory; solver never started; no LAVIE compute time consumed.

## RCA / FMEA

5 Why: CAD builder stopped -> no gate declaration -> minus-X direction was
present but count/spec was absent -> launch parameters assumed direction implied
existence -> preflight correctly requires explicit topology. Fishbone:
Method=partial gate contract; Measurement=empty run directory; Solver/mesh not
involved. FMEA countermeasure: require `gate_count=1` alongside direction and
retain full worker log in the wait status artifact.

## Correction and verification

`urgent02` adds `gate_count=1`, preserves `[-1,0,0]` inflow, and records
`log_snippet/stdout_tail/stderr_tail`. Pass criterion is non-empty case build,
cooling precheck PASS, solver boundedness, and generated cooling KPIs. Until
then status remains `PROXY_GAP`.
