# Quality Incident Report: Robot L20 Launcher Redirect Bug

Date: 2026-06-20

## Incident
The first attempt to start `start_robot_l20_autonomous_loop.ps1` failed.

## Detection
PowerShell returned:

```text
Start-Process : This command cannot be run because "RedirectStandardOutput" and "RedirectStandardError" are same.
```

## Impact
The bounded autonomous Robot L20 loop did not start on the first launcher attempt.

## 5 Whys
1. Why did the launcher fail?  
   `Start-Process` rejected identical stdout and stderr redirect paths.
2. Why were paths identical?  
   The launcher used one combined log path for both streams.
3. Why was that invalid?  
   Windows PowerShell `Start-Process` requires different files when both redirect parameters are used.
4. Why was this not caught by compile checks?  
   PowerShell runtime validation occurs only when `Start-Process` is called.
5. Why did this matter?  
   The user requested immediate autonomous development start.

## Web Knowledge Check
Global web search was not needed. The error message directly identified the local PowerShell API constraint.

## Fix
Split logs into:

- `robot_l20_autonomous_loop_stdout.log`
- `robot_l20_autonomous_loop_stderr.log`

## Prevention
For future PowerShell launchers, never pass the same path to `-RedirectStandardOutput` and `-RedirectStandardError`.

