# Sanitized live resource and thermal admission snapshot — 2026-11-02 JST

A Windows/WSL compute node with 16 GiB installed and about 15.42 GiB OS-visible was sampled through separate health and direct Windows sources. The health sample reported about 1.32 GiB available; a direct sample about 39 seconds later showed about 1.36 GiB in PerfOS/PSAPI, which agreed closely with the OS free-physical counter. Treat the observations as time-separated; do not combine them as simultaneous values.

Commit was about 31.42 GB of a 36.08 GB limit. An existing non-solver worker held about 24.37 GB Private Bytes and 9.57 GB working set; these are distinct measures. Automatic pagefile use was about 1.52 GB, but no paging rate was measured. The configured WSL file specifies 10 GB memory, 12 processors and 2 GB swap; no live guest RAM sample was taken, so the configured cap is not a guest allocation measurement.

The labeled Core (Tctl/Tdie) point was 92.375 C; its trailing five-minute time-weighted mean was 85.886 C against a 95 C gate and was accepted. Core Average and fan readings were unavailable. The host reported no WSL solver processes and dispatch remained disabled.

Decision: preserve existing work and hold new FEM dispatch until current guest and case-specific budgets, native recovery proof and separate authorization are satisfied. Root cause of past memory variation remains UNKNOWN. This note omits host identity, network addresses, accounts, process IDs, internal paths, logs and credentials. Source: INC-K1MMENT-RESOURCE-THERMAL-ADMISSION-20261102T1103JST.md.
