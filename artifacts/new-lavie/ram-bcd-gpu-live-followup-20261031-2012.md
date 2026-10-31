# New LAVIE RAM resource reconciliation follow-up

Incident: INC-K1MMENT-RAM-PROBE-MISMATCH-20261031-01
Observation: 2026-10-31 20:10-20:12 JST
Host: DESKTOP-K1MMENT, authenticated SSH as mksea
Scope: read-only physical-memory, OS-visible-memory, BCD, display-adapter, and WSL configuration checks.

## Live evidence

- Win32_PhysicalMemory reports two 8-GiB Hynix DDR4-3200 DIMMs: 17,179,869,184 B combined.
- Win32_OperatingSystem and Win32_ComputerSystem report 16,542,035,968 B visible to Windows. The difference is 637,833,216 B (608.285 MiB); cause remains UNKNOWN.
- Current BCD entry reports `hypervisorlaunchtype Auto`; no `truncatememory`, `removememory`, or `badmemorylist` setting was present in the queried output.
- AMD Radeon(TM) Graphics reports `AdapterRAM=536,870,912 B` (512 MiB). This is only a proximity clue. It does not map or explain the full 608.285-MiB gap; no attribution is made.
- At 20:12:26 JST Windows available RAM was 11,578,404,864 B. This is a host value, not added to guest memory.
- `.wslconfig` specifies 10 GB, 12 processors, and 2 GB swap on D:. At 20:11:12 JST the WSL guest reported 12 processors, 10,429,976,576 B total, 9,958,612,992 B available, and 2,147,483,648 B swap total/free. Guest and host values remain separate.
- The controller and dispatch-policy gate remains closed; no solver was launched and no task, job, checkpoint, BIOS, or RAM setting was changed during this check.

## Assessment

The Windows BCD output rules out an explicit boot memory cap in the queried current entry. The GPU's dedicated-memory figure is smaller than the unexplained gap and is not a memory-map attribution. No available live evidence identifies the excluded physical range or its owner. Cause is UNKNOWN; do not use the adapter figure to clear the RAM gate.

## Required action and validation

Maintain the existing RAM reconciliation hold and separate production-authorization hold. Before any FEM dispatch, obtain authoritative firmware/OS range mapping or exact-unit NEC confirmation and verify a current controller admission sample with installed, OS-visible, and available memory kept distinct. Preserve existing jobs and checkpoints.