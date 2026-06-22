# JPEG To Mecha Rig Scaffold RCA 2026-06-22

## Event

Initial scaffold verification failed during `py_compile`.

## 5 Whys

1. Why did `py_compile` fail?
   `from __future__ import annotations` appeared after the mandatory Windows stdout encoding block.
2. Why was that a problem?
   Python requires `from __future__` imports to appear before all executable statements.
3. Why was the file arranged that way?
   The project rule requires `sys.stdout.reconfigure(...)` at module top before other I/O imports, and the scaffold copied the common future-import pattern after it.
4. Why was this not caught before patching?
   The scaffold was written in one pass before running syntax checks.
5. Why is recurrence possible?
   Future new Python files may combine the project encoding rule with `from __future__` imports.

## FTA

Top event: scaffold verification failed.

- Syntax branch: future import after executable encoding block.
- Command branch: selftest command was run with a duplicated path from an inner working directory.
- External dependency branch: not involved.

## FMEA

| Failure mode | Effect | Detection | Countermeasure |
|---|---|---|---|
| Future import after encoding block | SyntaxError before any pipeline run | `python -m py_compile` | Do not use future imports in newly generated Python files that require the encoding block |
| Wrong cwd/path in selftest | False verification failure | command stderr | Run repo-root-relative commands from repo root |

## Web Knowledge Check

No web search was needed. The root cause was a deterministic local Python syntax rule and command path error, not an unknown library/runtime issue.

## Countermeasures

- Removed `from __future__ import annotations` from the new scaffold.
- Re-run `py_compile` before any functional test.
- Run selftest from the repo root using repo-relative paths.
