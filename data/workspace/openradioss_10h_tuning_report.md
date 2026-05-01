# OpenRadioss 10h Tuning Report - 2026-04-30

## Status

- Active run: `run37`
- Container: `clawstack-unified-openradioss-1`
- Active PID: recorded in `/work/engine.pid`
- Engine log: `/work/engine_run37.log`
- Backup: `backups/openradioss/run35_pre_10h_tuning_20260430/`
- Tuned local deck copy: `data/workspace/openradioss_10h_tuning/`

## Original Issue

The previous `run35` deck had:

- End time: `0.08 s`
- Minimum timestep: `5.0e-8 s`
- Estimated cycles: about `1,600,000`
- Observed progress: after about `50,200 s`, simulation time was only about `0.00124 s`
- Engine estimate: multi-week remaining time

This was not practical for an engineering feedback run on the current machine.

## Root Causes

1. The physical end time was too long for the current timestep and model size.
2. The enforced timestep produced too many cycles for a quick feedback loop.
3. The animation output requested many stress/energy/hourglass components that are not all needed for a first-pass check.
4. Starter warnings showed initial penetrations in Type25 contact; this should be reviewed separately because silently changing contact geometry can change the engineering meaning of the result.

## Changes Applied

The active engine deck was tuned for a first-pass 10-hour-or-less calculation:

- End time changed to `0.0014 s`
- Minimum nodal timestep changed to `8.0e-8 s`
- Estimated cycles reduced to about `17,500`
- Animation output interval changed to `0.00035 s`
- Heavy animation outputs removed:
  - `/ANIM/ELEM/ENER`
  - `/ANIM/ELEM/HOURG`
  - `/ANIM/ELEM/SIGX`
  - `/ANIM/ELEM/SIGY`
  - `/ANIM/ELEM/SIGZ`
  - `/ANIM/ELEM/SIGXY`
  - `/ANIM/ELEM/SIGYZ`
  - `/ANIM/ELEM/SIGZX`
  - `/ANIM/VECT/VEL`

Kept outputs:

- `/ANIM/ELEM/EPSP`
- `/ANIM/ELEM/VONM`
- `/ANIM/VECT/DISP`

## Verification Snapshot

`run37` started successfully.

Initial observed line:

```text
NC=       0 T= 0.0000E+00 DT= 8.0000E-08 ERR=  0.0% DM/M= 1.9495E+01
```

After roughly 90 seconds:

```text
NC=     100 T= 8.0000E-06 DT= 8.0000E-08 ERR= -0.0% DM/M= 1.9526E+01
ELAPSED TIME=         75.42 s  REMAINING TIME=      13122.24 s
```

The displayed remaining time is about 3.6 hours at this early checkpoint, so it is now inside the requested 10-hour class.

## Remaining Engineering Notes

- `DM/M` is about 19.5 percent, which is acceptable for quick screening but high for final validation.
- Initial penetration warnings should be corrected in a later geometry/contact pass rather than hidden by aggressive contact parameter changes.
- The current run is a fast evaluation run, not a final high-fidelity shearing validation run.
- If the result shape looks promising, the next step should be a second pass with lower mass scaling, for example `DT=6.0e-8` and a focused contact cleanup.
