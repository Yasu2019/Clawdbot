# Quality Incident Report: Robot L20 Trial Output Path Bug

Date: 2026-06-20

## Incident
The first run of `run_robot_l20_motion_trials.py` failed with `FileNotFoundError` while writing `robot_l20_motion_trial_status.json`.

## Impact
The L20 trial loop did not produce dashboard evidence on the first attempt.

## 5 Whys
1. Why did the job fail?  
   It tried to write under `D:\Clawdbot_Docker_20260125\data\data\workspace\...`.
2. Why was the path duplicated?  
   `ROOT = Path(__file__).resolve().parents[4]` resolved to the repo `data` folder, not the repo root.
3. Why was the parent index wrong?  
   The script path is under `data/workspace/apps/motion_lab/05_quality_check`, so the repo root is `parents[5]`.
4. Why was this not caught before execution?  
   `py_compile` checks syntax only and cannot validate runtime output paths.
5. Why did the workflow need a fix?  
   Dashboard evidence generation must be deterministic and cannot depend on a missing output directory.

## Web Knowledge Check
Global web knowledge collection was not useful for this failure. The cause was a local path-depth bug with direct stack-trace evidence.

## Fix
Changed `ROOT` from `parents[4]` to `parents[5]`.

## Prevention
For future generated dashboard-output scripts, add a smoke run after `py_compile` and verify the absolute output paths are under the repository root, not under nested `data/data`.

