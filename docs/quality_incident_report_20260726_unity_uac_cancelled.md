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

The user approved the retry. Installation then completed with exit code 0.
Independent verification found
`F:\Unity\Hub\Editor\6000.0.73f1\Editor\Unity.exe`, product version
`6000.0.73f1_a166abc3bf0e`, Authenticode status `Valid`, and signer
`Unity Technologies SF`. The final harness state is
`install_verified_complete`.

Decision rule: IF a Windows installer requires elevation, THEN silent mode still
requires explicit UAC approval, BECAUSE `/S` suppresses installer UI but cannot
bypass the OS security boundary.

## Verification / rollback / web decision

Initial containment verification found the F-drive target absent. Final retry
verification passed executable, version, signature, and exit-code gates. The
original C-drive 6000.3.6f1 Hub metadata remains present. Rollback, if requested,
is the Unity uninstaller under the new F-drive installation; it was not run.
No web search was needed for cancellation diagnosis; official Unity
documentation confirmed `/S` and final `/D=PATH` syntax.
