# K1 RAM probe mismatch follow-up — 12:04 JST
## Follow-up 2026-11-02 12:04 JST — native memory readback

Fresh authenticated read-only probe `MemoryCapacityNativeLite` on DESKTOP-K1MMENT (`100.67.170.15`) at 12:04:53.554 JST used kernel32 `GetPhysicallyInstalledSystemMemory` and `GlobalMemoryStatusEx` (no CIM/WMI). Installed memory remains 17,179,869,184 B (16 GiB); OS-visible memory remains 16,542,035,968 B; the stable difference is 637,833,216 B and its exact cause remains UNKNOWN. OS available physical memory was 3,772,944,384 B at the observation; available commit 3,832,434,688 B, commit limit 35,487,911,936 B. This is a point sample, not a trend or FEM capacity budget. No worker/process/task/checkpoint state was queried in this probe. No settings or jobs changed; this evidence does not clear the existing dispatch hold or establish a recovery path.

Probe implementation `scripts/Invoke-K1WslReadOnly.ps1` SHA-256 `611D94F005C0D6F597E3ED3E261BB5546AEDA464CEE1762F5D0740DF6EE63B8E`. Prior boot configuration checks found no explicit BCD maxmem/removememory; that does not attribute the remaining difference. Keep installed, OS-visible, host available and WSL guest memory as separate measures. Do not increase WSL allocation or dispatch FEM based on this observation alone.

