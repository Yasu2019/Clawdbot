# K1 solver and thermal refresh — 2026-11-02 11:47 JST

Linked incident: `INC-K1MMENT-POWER-CONTINUITY-PROBE-TIMEOUT-20261102-01`.

- Current OpenFOAM, CalculiX, Elmer and OpenRadioss executable hashes returned over authenticated K10 SSH/WSL route (exit0); no solver was launched.
- Host snapshot: available RAM494MB; CPU16.62% over2.012s on12 logical processors; Tctl/Tdie91.875C observation-only. Wi-Fi/Internet up; FEM dispatch false; WSL solver count0. Core Average/fan unavailable.
- Five-minute time-weighted Tctl/Tdie mean83.19C from six fresh samples; thermal subgate accepted under 95C mean limit. Instantaneous91.875C below100C emergency ceiling. This does not clear RAM or production/recovery gates.
- Existing OF76_f3A remains preserved; no case-specific checkpoint/restart was freshly verified. No host setting/job/process change.

Canonical evidence retains exact values, paths and hashes.
