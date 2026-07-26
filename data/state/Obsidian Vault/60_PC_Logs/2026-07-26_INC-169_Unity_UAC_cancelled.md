# INC-169 Unity UAC cancellation

## QC facts

Windows created `consent.exe`, then `Start-Process` returned
`この操作はユーザーによって取り消されました`. The F-drive target and
`Editor\Unity.exe` were both absent. Existing Unity Hub metadata was preserved.

## RCA / FMEA

Silent Unity installation still crosses the Windows elevation boundary. `/S`
removes installer questions but cannot approve UAC. The monitoring wrapper did
not catch this exception and therefore left a stale `installing` status.

| Mode | S | O | D | RPN | Action |
|---|---:|---:|---:|---:|---|
| UAC cancellation | 3 | 5 | 1 | 15 | Require visible Yes approval |
| Stale status | 5 | 5 | 2 | 50 | Catch exception and record blocked state |
| Accidental overwrite | 8 | 2 | 2 | 32 | Keep target-exists fail-closed gate |

## Countermeasure / verification / rollback

The wrapper now records `install_blocked_uac_cancelled`. Retry only when the user
is ready to approve UAC. Keep `/D` last and verify exit code, executable,
6000.0.73f1 version, and Unity Technologies signature. No rollback is required
because no files were installed.

## Final retry result

The user approved UAC. Installation completed with exit code 0 at
`F:\Unity\Hub\Editor\6000.0.73f1`. Independent verification passed:

- Unity executable present
- Product version `6000.0.73f1_a166abc3bf0e`
- Authenticode `Valid`
- Signer `Unity Technologies SF`
- Existing C-drive 6000.3.6f1 Hub metadata preserved
