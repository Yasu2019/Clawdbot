# Robot L20 Natural Motion Trial Report

- Generated: 2026-06-20T07:41:45.647477+00:00
- Trials run: 166
- Target: L20
- Current estimate: L20_PROXY_CANDIDATE
- Best score: 100 (L20_CANDIDATE)
- L20 candidates: 40

## Best Trial Metrics

- motion_naturalness_mean: 0.96
- task_success_rate: 0.98
- walk_arm_leg_phase_error_deg: 4.09
- walk_foot_sliding_m: 0.0049
- door_hand_target_error_m: 0.0179
- door_torso_twist_deg: 11.17
- sit_knee_hip_sync_error: 0.069
- sit_com_support_margin_m: 0.045
- stair_foot_clearance_m: 0.0939
- factory_pick_hand_target_error_m: 0.015
- factory_pick_clearance_m: 0.075
- jerk_norm: 0.175
- collision_rate: 0.011

## Task Scores

- walk: 92.6
- door: 92.5
- sit_stand: 96.9
- stairs: 100.0
- factory_pick: 100.0

## Corrections

- No high-priority corrections on the best trial.

## Next Actions

- Render the best L20 candidate as sampled PNG frames for visual review.
- Promote task-specific IK phases: approach, align, contact, act, release, recover.
- Add failure replay for foot slide, door over-twist, low stair clearance, and factory fixture collision.
- Keep real robot deployment blocked until L20 task motion is stable in simulation.
