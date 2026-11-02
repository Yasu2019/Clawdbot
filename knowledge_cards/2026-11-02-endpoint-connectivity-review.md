# Endpoint connectivity review - 2026-11-02

A user reported that a managed Windows endpoint was online, but the controller could not independently observe the source of that status.

At 10:29 JST, the controller's live tailnet view showed the peer offline with a last-seen age of about seven hours. Tailnet ping, SSH, RDP, and WinRM probes timed out. The local desktop automation browser bridge was unavailable, so no remote desktop frame or sign-in state was observed.

The endpoint's power, login state, active jobs, and the user's reported online indicator remain unknown. Route failures do not prove that the host is powered off. No remote setting, job, file, credential, or security control was changed; no job was stopped or dispatched.

For follow-up, refresh the endpoint address and tailnet state from the endpoint itself, then verify host/network reachability, authenticated worker, requested application, and an authorized desktop route as separate layers. Preserve existing jobs and do not auto-unlock or store credentials.
At 10:37 JST, a second controller-side check produced the same result: tailnet still reported offline, ping received no reply, and SSH/RDP/WinRM probes timed out. The desktop automation browser bridge was still unavailable. Host and job state remain unknown.
