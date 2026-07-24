# INC-155 RCA: Packaged Electron app launched in Node mode

## Observed facts

- Windows unpacked package generation succeeded.
- Initial probe PID exited within five seconds.
- Logged development launch failed at `app.setName("Bunny Colony")`.
- `require("electron")` did not expose Electron main-process APIs in the launched process.
- Host environment contains `ELECTRON_RUN_AS_NODE=1`.
- Runtime printed `Node.js v24.18.0`.

## 5 Whys

1. The app exited because the Electron `app` object was undefined.
2. The object was undefined because the executable ran as Node.
3. It ran as Node because `ELECTRON_RUN_AS_NODE=1` was inherited.
4. It was inherited because the validation harness used the host environment unchanged.
5. The preflight did not enumerate Electron-specific environment variables.

## FTA and Fishbone

Top event: packaged GUI exits before ready.

- Source syntax defect: unsupported by evidence; main loaded and failed on Electron API access.
- Package omission: unsupported; executable and app.asar exist.
- Runtime incompatibility: not proven.
- Host environment contamination: confirmed.

Contributors: environment (confirmed), harness method (confirmed), source/package/network (not implicated).

## FMEA

| Mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| Electron forced to Node | Immediate exit | 8 | 4 | 2 | 64 | Sanitize child environment |
| Machine-wide variable removed | Existing tooling regression | 8 | 3 | 4 | 96 | Never alter global setting |
| Probe checks only PID | False launch failure/success | 6 | 4 | 5 | 120 | Check window title and responsiveness |
| Broad process cleanup | Unrelated app termination | 8 | 2 | 3 | 48 | Match exact executable path |

## Countermeasure plan requiring confirmation

1. In one validation shell only, set `ELECTRON_RUN_AS_NODE` to null.
2. Start the packaged executable.
3. After five seconds, require a responsive process with title `Bunny Colony`.
4. Terminate only executable-path-matched test processes.
5. Build the portable artifact only after the launch gate passes.

## Rollback and scope

No game source change is required. The host's persistent environment is explicitly protected. If the sanitized probe still fails, collect the new log and reopen root-cause analysis rather than changing Electron versions blindly.
