# INC-186: LAVIE minus-X pipeline monitoring gap

## Summary

r35 completed at 11:09 JST, but its one-shot waiter ended and no dedicated state machine advanced the campaign to thermo fill. General tri-track activity was mistakenly treated as sufficient monitoring. No result data was lost; cooling calibration was delayed.

## 5 Why

1. The r35 waiter terminated after success. 2. Completion and progression were separate scripts. 3. General status did not represent the minus-X phase. 4. The old cooling waiter was obsolete and cancelled. 5. No live campaign-status gate was required before claiming dedicated monitoring.

## Countermeasures and verification

- Add a bounded, single-instance monitor with an atomic status file.
- Expose `waiting_pressure_repeat` and `ready_for_thermo_fill` explicitly.
- Forbid the obsolete continuous 35 s dispatch.
- Require a live PID and fresh status before reporting active monitoring.
- Remain observation-only until thermo parameters pass their physical gate.
- Unit tests must prevent advancement without successful r35 and keep `PROXY_GAP`.

Scope: this corrects monitoring continuity only; it does not validate cooling or defect accuracy.
