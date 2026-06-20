# INC-127 Robot L20 Trial Output Path Bug

Date: 2026-06-20 JST

## Summary
The first run of the urgent Robot L20 natural-motion trial generator failed before producing dashboard evidence. The script attempted to write output under a nested `data/data/workspace` path.

## Detection
Command:

```powershell
python data\workspace\apps\motion_lab\05_quality_check\run_robot_l20_motion_trials.py
```

Observed failure:

```text
FileNotFoundError: ... D:\Clawdbot_Docker_20260125\data\data\workspace\apps\growth_dashboard\robot_l20_motion_trial_status.json
```

## Impact
- L20 trial evidence was not created on the first attempt.
- The user's urgent request to move quickly toward natural robot motion was delayed.
- The failure was contained to a new generated script. Existing dashboard files and robot demos were not damaged.

## 5 Why
1. Why did the job fail?  
   It tried to write to a path that did not exist.
2. Why was the path wrong?  
   The repository root was calculated as `parents[4]`.
3. Why was `parents[4]` wrong?  
   The script path is `data/workspace/apps/motion_lab/05_quality_check/run_robot_l20_motion_trials.py`; `parents[4]` points to `data`, not the repository root.
4. Why did pre-checks miss this?  
   `py_compile` validates syntax only and cannot prove output path correctness.
5. Why did this matter operationally?  
   Dashboard evidence generation must be deterministic and must not fail during urgent robot iteration.

## FTA
Top event: L20 trial generator fails to write evidence.

- Path computation fault
  - wrong parent index
  - output path duplicated `data`
- Missing runtime smoke test
  - syntax check passed
  - no output-path assertion before write
- No directory creation fallback
  - target path assumed valid

## FMEA
| Failure Mode | Effect | Severity | Occurrence | Detection | RPN | Countermeasure |
|---|---:|---:|---:|---:|---:|---|
| Wrong repo-root parent index | Output file write fails | 7 | 4 | 4 | 112 | Use `parents[5]` and smoke run |
| Syntax-only validation | Runtime path bug escapes | 6 | 5 | 5 | 150 | Always run generated output script once |
| Nested `data/data` path | Dashboard evidence absent | 6 | 3 | 3 | 54 | Assert output path starts with repo root and not `data/data` |

## Fishbone
- Method: parent-index path calculation used without validation.
- Machine: Windows path showed nested `data\data`, making root error visible.
- Measurement: only `py_compile` was used before runtime.
- Material: new generated script had no existing path helper.
- Human/process: urgent work increased pressure to run quickly.

## Fix
Changed:

```python
ROOT = Path(__file__).resolve().parents[5]
```

Then reran the trial generator.

## Verification
Successful run generated:

- `data/workspace/apps/growth_dashboard/robot_l20_motion_trial_status.json`
- `data/workspace/apps/growth_dashboard/robot_l20_motion_trials.html`
- `data/workspace/apps/growth_dashboard/robot_l20_motion_trial_report.md`

Result:

- Trials: 120
- Best score: 100
- Best verdict: L20_CANDIDATE
- L20 proxy candidates: 24
- Best task score floor: 82.4

Telegram:

- Text notification sent.
- HTML document sent.

## Lessons Learned
For urgent generated tooling, a syntax check is not enough. Any script that writes dashboard evidence must run once and prove its absolute output paths.

## Prevention Rule
When creating a dashboard-output script, verify:

1. `py_compile` passes.
2. A smoke execution completes.
3. Output paths are under `D:\Clawdbot_Docker_20260125`.
4. Output paths do not contain nested `data\data`.
5. Expected JSON/HTML/Markdown evidence files exist.

