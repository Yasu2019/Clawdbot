# Quality Incident: Freshness Script `--help` Side Effect

Date: 2026-07-25 JST

## Event

`scripts/check_and_heal_dashboard_freshness.py --help` was executed to inspect
usage. The script has no argument parser and ignored `--help`, starting its
self-healing workflow.

## Impact

Two wrapper processes represented one parent/child execution chain. The exact
freshness launcher processes were stopped. Its already-started IATF thumbnail
indexer was allowed to finish because refreshing that index was in scope for
the user's dashboard-currentness request. No unrelated worker or simulation was
stopped.

## 5 Whys

1. Why did a check start mutations? The script executes `main()` regardless of
   unknown command-line arguments.
2. Why was `--help` not safe? No `argparse` or explicit help guard exists.
3. Why was this assumed? Most operational scripts in this repository implement
   standard help behavior.
4. Why was the side effect detected? The command timed out and process
   inspection showed the freshness and child indexer commands.
5. Why was impact limited? Exact PIDs and command lines were verified before
   containment; unrelated processes were preserved.

## Countermeasure

For legacy scripts, inspect the bottom-level entry point or search for
`argparse` before invoking `--help`. Treat `--help` as potentially mutating
until argument handling is proven.

## Verification

- Exact freshness launcher PIDs no longer run.
- The single child indexing chain completed.
- Updated IATF status is valid JSON.
- All 12 indexed video URLs return HTTP 200/206 from port 8088.

## Scope limit

The legacy script itself was not redesigned in this task; changing its CLI
contract is separate work.
