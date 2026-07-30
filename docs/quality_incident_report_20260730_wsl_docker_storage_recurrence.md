# INC-177 Permanent Countermeasure: WSL/Docker Storage Recurrence

Date: 2026-07-30 JST  
Beads: `Clawdbot_Docker_20260125-t101`

## Outcome

The host reached the emergency storage range again after the initial recovery:
E free space fell from 120.2 GB to 51.47 GB, and the Ubuntu VHD grew from about
325 GB to 395.28 GB. New CAE dispatch is now designed to fail closed whenever E
has less than 100 GB or 10% free. Ubuntu and WSL swap are being relocated to F.

## Root cause

Two independent Linux container stores were retained on E:

1. Native Docker in Ubuntu used `/var/lib/docker-native` inside
   `E:\WSL\Ubuntu\ext4.vhdx`.
2. Docker Desktop used
   `E:\DockerData\DockerDesktopWSL\disk\docker_data.vhdx`.

The Ubuntu native Docker store contains millions of overlay2 inodes and caused
rapid VHD growth. WSL/Docker VM state also remained after workloads stopped,
which prevented clean Ubuntu recovery when E was exhausted. Existing monitoring
reported RAM under the label `free_gb`; it did not enforce host disk capacity.

## Permanent controls

- Relocate the Ubuntu VHD and WSL swap to F, retaining a verified rollback VHD.
- Inspect E/F free bytes, percentages, and known VHD sizes every five minutes.
- Warn below 150 GB or 15%; block new CAE dispatch below 100 GB or 10%;
  declare emergency below 60 GB or 6%.
- Clear a block only after hysteresis recovery: E at least 175 GB/18% and F at
  least 175 GB/16%. F warning remains 15%; the extra 1 point prevents flapping.
- Never delete user data, Docker volumes, or containers automatically.
- Run weekly native Docker GC only for old BuildKit cache and dangling images,
  and defer it while a CAE process is active.
- Permit at most one bounded WSL service recovery, only when no CAE process is
  active. Use normal Docker Desktop stop, `wsl --shutdown`, WslService restart,
  and Docker restoration. Never loop or force-delete VM state.

## Preservation and rollback

- Pre-change repo backup:
  `backup/inc177-permanent-storage-guard-20260730`
  at commit `5326f6d646d567384b1b302c7918e0117b80c531`.
- Pre-change WSL/native Docker configuration and container inventories:
  `F:\ClawstackArchive\INC177_permanent_20260730`.
- Ubuntu export/rollback location:
  `F:\WSL\Ubuntu-20260730\ubuntu-inc177-backup.vhdx`.
- The old Ubuntu registration must not be removed until the F export and working
  copy have both been verified.

## Legacy-task decision

The user explicitly approved stopping the continuing CAE orchestrator and its
monitor children for this maintenance. Only the confirmed process family rooted
at PIDs 23684/24800 and monitor children 29292/20784/10984 was stopped.
Unrelated Windows work was left intact. Native Docker's seven running containers
and Docker Desktop were stopped normally for the approved WSL maintenance.

## Verification checklist

- [x] F backup VHD export completed and validated at 395.28 GB
- [x] Ubuntu imported in place from F and boots with systemd healthy
- [x] Native Docker restored seven containers during verification
- [x] Docker Desktop restored 74 containers
- [x] E free capacity recovered from 51.56 GB to 446.84 GB
- [x] Scheduled storage guard and safe GC tasks installed
- [x] CAE preflight rejects an active storage block and clears when healthy
- [x] WSL swap created on F
- [x] Beads and durable incident note updated

## Final implementation evidence

- Active Ubuntu registration:
  `F:\WSL\Ubuntu-20260730\ubuntu-inc177-backup.vhdx`
- Preserved rollback VHD:
  `F:\WSL\INC177_Rollback_20260730\ext4-original.vhdx`
- Rollback transfer: 395.284 GB copied, 0 failures, 0 mismatches; E source was
  removed only by Robocopy `/MOV` after copy success.
- Final capacity: E 446.84 GB free (47.97%); F 327.92 GB free (17.60%).
- Native `containerd.service` was disabled because it duplicated the embedded
  containerd owned by `docker-native.service` and left a start job blocking
  `multi-user.target`.
- Native Docker startup can take about two minutes while overlay2 containers
  are restored. A temporary WSL keepalive was used only for verification and
  was removed afterward; Ubuntu is allowed to stop when idle.
- Docker Desktop remains the persistent desktop engine and returned 74
  containers.
- After the 14:05 storage check returned healthy and removed the dispatch
  block, the existing supervisor automatically restarted the prior CAE
  orchestrator command as PIDs 33812/4184. The maintenance did not start a new
  job manually and did not stop this resumed process. It runs the current
  orchestrator containing the storage preflight gate.
- A task-created incomplete VHD remains quarantined at
  `F:\WSL\Ubuntu-Active\INCOMPLETE-DO-NOT-USE.vhdx`. Automatic deletion was
  rejected by the execution policy, so it is not used or registered. It is the
  exact follow-up cleanup target; no unrelated F data may be removed with it.
