# Quality incident: Cool dispatch JSON quoting

## Event and impact

- Date: 2026-08-02 JST
- Command: first `lavie-mfminusx-cool-20260802-urgent01` dispatch attempt
- Failure: `JSONDecodeError: Expecting property name enclosed in double quotes`
- Impact: no worker job or solver was started; no existing process was changed.

## 5 Why / logical tree

1. Dispatch did not start because `--params-json` was not valid JSON at Python argv.
2. It was invalid because PowerShell removed/rewrote quoting at the CLI boundary.
3. The command embedded a large JSON object in a shell argument.
4. The dispatcher already supports `--params-file`, but that safer boundary was not used.
5. The urgent path lacked a rule forbidding inline structured payloads in PowerShell.

Fishbone categories: Method=inline JSON; Environment=PowerShell quoting;
Measurement=parser rejected before dispatch; Machine/LAVIE=no involvement;
Material/CAE inputs=unchanged.

## FMEA

| Failure mode | Effect | Detection | Countermeasure |
|---|---|---|---|
| Inline JSON corrupted | launch rejected | JSON parser traceback | use UTF-8 params file |
| Invalid values in file | wrong trial | parse + retained artifact | validate by dispatcher before job |
| Retry duplicates job | resource conflict | stable trial ID / worker lock | retain same trial ID; accept busy |

## Countermeasure and verification

Use `lavie_mfminusx_cool_urgent01_params.json` with `--params-file`. Pass when
the dispatcher parses it and either returns worker `busy` without a solver
launch or accepts exactly one trial. Rollback is removal of the unaccepted
parameter artifact; no running job requires rollback.

## Reusable rule

IF a PowerShell command must pass structured JSON THEN write a reviewed UTF-8
JSON artifact and use `--params-file` BECAUSE shell quoting is not a stable
serialization boundary.
