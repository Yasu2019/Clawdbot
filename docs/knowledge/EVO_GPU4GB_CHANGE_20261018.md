# EVO GPU 4GiB change — 2026-10-18

Authorization: user explicitly requested GPU32GiB ->4GiB because GPU workloads are not currently required. Related Beads Clawdbot_Docker_20260125-jrth.

## Verified safe preparation
At22:09 JST, signed installed AMD ADLX runtime1.5.0.124 accepted IADLXSystem3 and reported VGM supported, currentHigh32GB and an exactCustom4GB option. Used official SDK ABI and never guessed registry writes or firmware offsets. Source https://gpuopen.com/manuals/adlx/adlx-sdk-references/adlx-interfaces/system/iadlxvariablegraphicsmemory/setoption/ documents that SetOption triggers restart.

P43 run2(nt12,MPI1) and P44 run2(nt6,MPI1) were inspected in procfs and matched existing running task actions. Both stopped using native /CHKPT + /STOP only. NORMAL TERMINATION/USER BREAK confirmed. Fresh restart~2.325GB percase, CHECK_DATA /RERUN/.../2, original0/1 known-good files preserved. Snapshot copies and all inputs/binary hashes verified at22:11:30 JST. Saved checkpoints:
- P1r43f cycle29900, time0.0001045015; /srv/evo-hpc/gpu4gb-maintenance-20261018/P1r43f
- P1r44f cycle17650, time0.00001931110; /srv/evo-hpc/gpu4gb-maintenance-20261018/P1r44f

Radioss rewrites the .ctl request to RUN CONTROL FILE acknowledgement. The new verifier initially assumed contents unchanged and halted; corrected to verify ownership through the exact hardlink inode and preserve the native acknowledgement. No additional stop/restart requests were issued. This invocation's processed control file alone was archived after native exit.

Two unique startup S4U resume owners were registered with1minute delay. Each guards Windows-visible>=56GiB, exactactiveGPU4GiB, native snapshot/live hashes, input/binary/MPI/thread compatibility, no existingengine and exclusive owner. It then runs samebinary -i CHECK_DATA -nt12/6 and logs engine_gpu4gb_resume.log. Older tasks, data and services were not removed or overwritten.

## Change and current verification boundary
ADLXSetOption returned0 at22:11:48 JST. Windows System/User32 event1074 confirmed restart request. SSH became unreachable during restart; at22:15:18 JST, SSH still timed out. New memory capacity and solver resumption are NOT yet verified. Asked user to report current physical display to distinguish boot wait/login from any required firmware/recovery interaction. Do not issue repeated resets or claim successful application from setter returnalone.
WSL config remains memory20GB/processors24/swap8GB. No claim that FEM can already use48/64GB.

Evidence: controller artifacts/evo-vgm-20261018/checkpoint-state.json; EVO C:/ProgramData/Clawstack/EvoGpu4GB-20261018/checkpoint-state.json and gpu4gb-set-intent.json; native /srv/evo-hpc/gpu4gb-maintenance-20261018/state.json and percase manifests.

Next verification: live boot timestamp, ADLX read-only currentoption4GB, PNP-mapped active GPU reservation, DIMM/OS visible/free/WSL layers, each startup owner result, each actualsolver cwd/PID/log and numerical time advancement beyond savedpoint. Retain checkpoints and do not forcekill or delete oldwork.
## Verified completion — 2026-10-18 22:40 JST

Direct live audit at22:37:25 JST confirms activeGPU reservation4,294,967,296B=4GiB and Windows-visible64,045,780,992B=59.65GiB, increased exactly28GiB. ADLX-supported Windows change therefore took effect; no BIOS GUI editing or firmware flash was required. Tailscale andsshd are Running/Automatic and TailscaleForceDaemon=true at22:37.

System logs show subsequent restart events and a Kernel-Power41/6008 event during the disconnected interval. Do not infer exact cause/initiator from these IDs. First maintenance resume ran at22:14 and progressed to43cycle33300/44cycle19700, but was no longer active on reconnection. Preserved oldlogs,ownerfiles and status rather than deleting staleevidence.

Postboot integrity audit:44 live restart and all inputs match immutable snapshot.43 live restart hash differs, validity unknown; source snapshot still matches its manifest. Copied verified replacement, archived the changed43 native restart and corresponding0002.out under /srv/evo-hpc/panel-P1r43f-20261018/recovery/gpu4gb-postboot-2238 (preserved SHAfcea4feb057946f5920181a2ef52b1ed3aa1d0ae142f0ddfd6fdad933985df42), and restored known-good SHA236b053d4cdf1642388f6e306ddcbde5de35d3f90f5c2484d9f326473605c911. No data deleted or arbitrary checkpoint accepted. Preserved native0/1 checkpoints and immutable maintenance snapshot.

Disabled only this operation's earlier maintenance startup tasks after verifying neither running, and exported theirXML before changingenabledstate. They failedclosed on oldownership/checkpoint changes; unrelated oldrun2 tasks/services/watchdogs not changed. Created unique manualS4U Resume2 owners with no executiontime limit and no duplicate launches. Input/binary/restart hashes verified again before start.

Live22:40:16 JST: P43 enginePID359 nt12/MPI1 advanced from29900/T0.0001045015 to30000/T0.00010460; P44 PID360 nt6/MPI1 advanced from17650/T0.00001931110 to17700/T0.000019361. Both processes live; continuation proven, neither calculation scientifically complete. Source: directprocfs and new engine_gpu4gb_resume.after-reboot-2238.log percase. New output logs do not overwrite previousattemptlogs.

WSL configured memory remains20GB/processors24/swap8GB. Increased Windows capacity does not mean WSL can use48/64GB yet. Any futureWSL expansion requires its own live budget and checkpoint-preserving stop/restart plan.