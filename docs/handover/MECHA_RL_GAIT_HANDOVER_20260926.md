# MechaRL handover 2026-09-26 (read this first; earlier: MECHA_RL_GAIT_HANDOVER_20260914.md)

## State
- Champion walking: v139_ankle_knee010 (score 23.5). Best running: rn002 (149.7). Best stairs: 3-joint hybrid lineage.
- Truth files: C:\v50_work\autonomy\queue.json (runs), leaderboard.tsv (walk/run only), mecha_rl_findings.json (dated facts -> dashboards via D:\Clawdbot_Docker_20260125\scripts\update_mecha_rl_status.py).
- Keep >=2 real (unheld, no status.json) runs pending. If ALARM_queue.txt appears, only fallback vcont_* is running = zero progress. Add runs, then `powershell -File C:\v50_work\autonomy\watchdog_queue.ps1` evicts the fallback. Check for duplicate trainers (same --out twice; kill the newer with taskkill /F /T).

## Stairs recipe (works at 5/6.5/8/10/13 cm)
Hybrid reference: hip = human full amplitude, knee = human x0.75, ankle = human, on the policy's own reference for other DOFs (refs/v50_ref_stairs_up_hyb_hipkneeankle[_h0XX].json). Always seed from the best checkpoint of the previous riser and blend 300 iterations from the seed's own reference (--ref-blend-from/--ref-blend-iters). Never swap a whole reference abruptly (collapses the policy).
Seed quality matters: 10cm from f005 (strong 8cm) = 97% alive at 12 s; from b010 = 76-82%.
Measure with scratchpad gait_stairs_compare2.py (env STAIRS_REF = the run's own --ref-json, STEP_H = its riser). It reports L+R combined; measure legs separately for symmetry claims.
Results: g002 5cm 62/62; f005 8cm 61/62; f006 10cm 62/64; f003/f004 13cm 76-78%. Ankle range grows to ~1.8x human at >=10cm, hip shrinks below human.

## Walking
Human joints do NOT compose like stairs. wk002 knee 48.9?, wk004 ankle 46.4, wk005 knee+ankle 86.9, wk006 all three 141.5, wk007 hip+ankle 100.2, wk003 hip 172.7. Hip is the disruptive joint; hip 50% blend (wk008) = 64.3, fall 0.4%. Queued: wk009 (hip 25%), wk010 (ankle + hip 50%).
Never diagnose with a manually different --ref-json: autodiag replays each run's own ref (last argparse value wins).

## Stairs descent (blocked)
Probe scratchpad/probe_stairs_down_spawn.py: spawn z is 7.28 cm below analytic expectation, identical for all envs before any physics step. Cause: v50_walk_env.py lines ~775-794 re-settle 300 steps on the raised platform and derive stand_z from it. Fix not done (affects every terrain; validate against ascent stairs). Do this before any new descent training.

## Infra lessons
- autogen_runs.py cannot see stairs runs (leaderboard has placeholders 687/62) -> queue starved for ~30 h on 9/24-26. Real fix: make autogen stairs-aware or keep queue stocked by hand.
- chain_release.py has EXPIRE 2026-09-20 (dead). Do not rely on hold+release chains.
- Watchdog can double-launch a run within seconds; check CreationDate, kill the newer.
- Host RAM dipped to 0.4 GB on 9/25 evening; min_free_ram_gb gate waited correctly.

## Next
1. Watch wk009/wk010/stairsf007; diagnose stairs with gait_stairs_compare2.py, walking via leaderboard.
2. Continue riser curriculum beyond 13cm only from a strong 10-13cm seed.
3. Fix stairs_down spawn offset, then descent probe run.
4. Make autogen stairs-aware.
