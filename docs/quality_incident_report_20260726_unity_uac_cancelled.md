# Unity installation blocked by cancelled UAC (2026-07-26)

## Impact and observed facts

The verified Unity 6000.0.73f1 installer requested elevation. Windows created
`consent.exe` at 12:52:04 JST. The elevation request ended without approval and
PowerShell reported `この操作はユーザーによって取り消されました`.
No target directory or Unity executable was created on F:. Existing Unity Hub
metadata under C: was unchanged.

## 5 Why / FTA / Fishbone

1. Installation did not start because `Start-Process` raised.
2. It raised because the installer elevation request was cancelled.
3. Elevation was required by the signed Unity editor installer.
4. The silent installer switch suppresses installer questions but does not
   bypass Windows UAC.
5. The wrapper lacked a catch block, leaving status at `installing`.

FTA: missing installer and bad signature were ruled out by the preceding exact
size/signature gate; target collision was ruled out because the target did not
exist; disk capacity was sufficient at about 1.63 TB free.

## FMEA

| Failure mode | S | O | D | RPN | Countermeasure |
|---|---:|---:|---:|---:|---|
| UAC not approved | 3 | 5 | 1 | 15 | Notify user and require visible approval |
| Status remains `installing` | 5 | 5 | 2 | 50 | Catch start failure and write blocked state |
| Retry overwrites existing editor | 8 | 2 | 2 | 32 | Preserve target-exists fail-closed gate |

## Countermeasure and retry plan

The wrapper now catches a cancelled elevation and records
`install_blocked_uac_cancelled`. Retry only after the user is ready to click
Windows UAC `Yes`. Keep `/D=F:\Unity\Hub\Editor\6000.0.73f1` as the final
argument and retain all version, executable, and signature gates.

Decision rule: IF a Windows installer requires elevation, THEN silent mode still
requires explicit UAC approval, BECAUSE `/S` suppresses installer UI but cannot
bypass the OS security boundary.

## Verification / rollback / web decision

Verification: F-drive target absent; no Unity executable created; wrapper exited.
Rollback is unnecessary because no installation files were written. No web
search was needed for the cancellation diagnosis; the local exception and
`consent.exe` lifecycle were authoritative. Official Unity documentation was
used separately to confirm `/S` and final `/D=PATH` syntax.
