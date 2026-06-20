# Robot L20 Natural Motion Trial Report

- Generated: 2026-06-20T03:54:12.177439+00:00
- Trials run: 120
- Target: L20
- Current estimate: L20_PROXY_CANDIDATE
- Best score: 100 (L20_CANDIDATE)
- L20 candidates: 24

## Best Trial Metrics

- motion_naturalness_mean: 0.928
- task_success_rate: 0.98
- walk_arm_leg_phase_error_deg: 9.66
- walk_foot_sliding_m: 0.0121
- door_hand_target_error_m: 0.0383
- door_torso_twist_deg: 13.02
- sit_knee_hip_sync_error: 0.102
- sit_com_support_margin_m: 0.0218
- stair_foot_clearance_m: 0.0782
- factory_pick_hand_target_error_m: 0.0236
- factory_pick_clearance_m: 0.0607
- jerk_norm: 0.239
- collision_rate: 0.032

## Task Scores

- walk: 82.4
- door: 83.9
- sit_stand: 88.2
- stairs: 100.0
- factory_pick: 96.0

## Corrections

- No high-priority corrections on the best trial.

## Next Actions

- Render the best L20 candidate as sampled PNG frames for visual review.
- Promote task-specific IK phases: approach, align, contact, act, release, recover.
- Add failure replay for foot slide, door over-twist, low stair clearance, and factory fixture collision.
- Keep real robot deployment blocked until L20 task motion is stable in simulation.
