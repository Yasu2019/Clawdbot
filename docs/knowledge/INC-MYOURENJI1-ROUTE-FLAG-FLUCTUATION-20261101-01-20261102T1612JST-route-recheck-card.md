# Myourenji_1 route recheck ? 2026-11-02 16:12 JST

Incident: `INC-MYOURENJI1-ROUTE-FLAG-FLUCTUATION-20261101-01`.

The user reported it had come online. K10's fresh `tailscale status` at16:12:06 showed peer100.111.176.93 `offline`, last seen13h, tx8736/rx0 over DERP(tok). Three 4s Tailscale pings timed out. Strict-host-key batch SSH through `cae-myourenji-1` timed out to port22 (exit255). Authenticated control is NOT established. GUI, host power/sign-in, monitoring, worker/application, tasks/jobs/checkpoints and cause remain UNKNOWN. Preserve existing work; no restart, dispatch, cleanup or setting change. A failed VPN route does not prove host power-off.
Graph: exact Beads node and three route links verified; previous Myourenji dangling Beads edge resolved. One unrelated PowerContinuity dangling edge remains. Graphify explain/path passed.
