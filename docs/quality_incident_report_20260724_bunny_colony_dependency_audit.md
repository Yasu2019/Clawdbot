# INC-154 RCA: Bunny Colony desktop dependency audit

## Facts

- `npm install` completed with 383 packages.
- Game rule tests: 5 passed, 0 failed.
- Full audit: 9 high, 1 critical.
- Production-only audit: 0 vulnerabilities.
- Production npm dependency tree: empty.
- Direct development dependencies:
  - Electron 35.7.5; npm offered 43.2.0 as the fix.
  - electron-builder 26.0.12; npm offered 26.15.3 as the fix.
- Official registry current versions on 2026-07-24 matched those offered fixes.
- Windows packaging has not run.

## 5 Whys

1. The security gate failed because the resolved development graph contains 10 advisories.
2. The critical tar advisory is transitive through the older electron-builder graph.
3. The high Electron advisory requires a newer Electron major according to npm audit.
4. The manifest used initial fixed versions before a lockfile/advisory check existed.
5. The audit correctly stopped promotion before a distributable artifact was produced.

## FTA / logical tree

Top event: vulnerable build promoted.

- Prevented by audit gate: confirmed.
- Runtime npm package exposure: ruled out by empty production tree.
- Embedded Electron exposure: possible because Electron is the shipped runtime.
- Builder-only exposure: confined to the developer machine but still requires remediation.

## FMEA

| Failure mode | Effect | S | O | D | RPN | Control |
|---|---|---:|---:|---:|---:|---|
| Old Electron runtime | Shipped browser-runtime exposure | 8 | 4 | 2 | 64 | Upgrade and re-audit |
| Vulnerable builder transitive package | Build-host exposure | 6 | 4 | 2 | 48 | Upgrade builder |
| Force audit rewrite | Breaking/unreviewed dependency change | 6 | 3 | 4 | 72 | Exact manual pins only |
| Mislabel dev findings as production clean | False assurance | 8 | 3 | 5 | 120 | Record both full and production audits |

## Countermeasure plan requiring confirmation

1. Change only the two exact versions in `games/bunny-colony/package.json`.
2. Run one normal install to update the lockfile.
3. Require full audit to report zero critical/high findings.
4. Rerun 5 rule tests.
5. Only then run the Windows directory and portable builds.

## Rollback and scope

Restore the two prior version pins and the prior lockfile, or remove the isolated game directory. No existing app or service is affected. Compatibility with Electron 43 is not yet proven and must be validated by packaging and launch checks.

## External knowledge decision

No broad web search was necessary. The npm registry metadata and audit database are primary sources for package versions and advisory remediation. No third-party article influenced the countermeasure.
