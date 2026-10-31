# Windows locked-console diagnosis follow-up — 2026-10-31

A Windows compute host remained reachable through authenticated management and its network interface while WTS reported an active console session as locked. No user was returned and GUI pixels were unavailable. This is evidence of a locked session, not an offline host or proof of the exact screen.

The local Success audit for Windows Other Logon/Logoff Events was initially disabled, preventing useful 4800/4801 lock/unlock history. Success auditing was enabled and read back; Failure auditing remained disabled. A later Security query completed successfully but returned no 4800/4801 records while WTS still reported locked. No natural lock/unlock transition was confirmed, so event-generation effectiveness and the reason for the lock remain unknown.

Operational checks separated host reachability, Wi-Fi, monitoring task health, guest process telemetry, WTS state, and visible desktop state. The host was on AC power; standby timeout was disabled on AC/DC. An absent audit event must not be treated as proof of a transition or as a host outage.

For recurrence: retain audit-policy readback and sanitized event metadata, correlate with the next natural transition, and keep GUI state unknown until live screen evidence exists. Do not force lock/unlock, store credentials, enable auto-login, or disturb unrelated work to obtain evidence.
