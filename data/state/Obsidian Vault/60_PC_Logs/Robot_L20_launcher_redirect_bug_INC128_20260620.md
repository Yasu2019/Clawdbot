# INC-128 Robot L20 Autonomous Launcher Redirect Bug

Date: 2026-06-20 JST

## Summary
The first attempt to start the bounded Robot L20 autonomous development loop failed because the PowerShell launcher redirected stdout and stderr to the same file.

## Detection
Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File data\workspace\apps\motion_lab\05_quality_check\start_robot_l20_autonomous_loop.ps1
```

Error:

```text
Start-Process : This command cannot be run because "RedirectStandardOutput" and "RedirectStandardError" are same.
```

## Impact
- The autonomous loop did not start on the first attempt.
- The issue delayed the user's urgent self-running robot development request.
- No robot data, dashboard file, or existing infrastructure was damaged.

## 5 Why
1. Why did the launcher fail?  
   `Start-Process` rejected the redirect parameters.
2. Why did it reject them?  
   stdout and stderr pointed to the same log path.
3. Why was that invalid?  
   Windows PowerShell requires different files for `-RedirectStandardOutput` and `-RedirectStandardError`.
4. Why was the issue not caught earlier?  
   The launcher had not been smoke-run before use.
5. Why did this matter?  
   The user explicitly asked to start self-running development immediately.

## FTA
Top event: autonomous loop does not start.

- Launcher parameter error
  - stdout log path equals stderr log path
- Missing launcher smoke test
  - script was created and immediately run
- Platform-specific PowerShell behavior
  - `Start-Process` forbids same redirect file

## FMEA
| Failure Mode | Effect | Severity | Occurrence | Detection | RPN | Countermeasure |
|---|---:|---:|---:|---:|---:|---|
| Same stdout/stderr redirect path | Launcher fails | 6 | 4 | 2 | 48 | Use separate log files |
| No smoke launcher test | Runtime bug reaches user workflow | 6 | 4 | 4 | 96 | Run launcher once and inspect status |

## Fix
Split logs:

- `robot_l20_autonomous_loop_stdout.log`
- `robot_l20_autonomous_loop_stderr.log`

## Verification
Relaunch succeeded.

- Launcher status file created.
- PID: 19316
- Autonomous status: `state=running`
- First cycle completed.

## Prevention Rule
For all future PowerShell background launchers, never set `-RedirectStandardOutput` and `-RedirectStandardError` to the same path. Always smoke-run launchers and verify the status JSON.

