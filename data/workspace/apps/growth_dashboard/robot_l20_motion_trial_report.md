# Robot L20 Natural Motion Trial Report

- Generated: 2026-07-18T20:36:49.464212+00:00
- Trials run: 166
- Target: L20
- Current estimate: L20_PROXY_CANDIDATE
- Best score: 100 (L20_CANDIDATE)
- L20 candidates: 41

## Best Trial Metrics

- motion_naturalness_mean: 0.96
- task_success_rate: 0.98
- walk_arm_leg_phase_error_deg: 3.78
- walk_foot_sliding_m: 0.0034
- door_hand_target_error_m: 0.0152
- door_torso_twist_deg: 11.73
- sit_knee_hip_sync_error: 0.061
- sit_com_support_margin_m: 0.0354
- stair_foot_clearance_m: 0.0887
- factory_pick_hand_target_error_m: 0.0145
- factory_pick_clearance_m: 0.075
- jerk_norm: 0.181
- collision_rate: 0.018
- therblig_label_coverage_pct: 99.0
- effective_therblig_ratio: 0.91
- non_effective_therblig_share: 0.099
- nva_time_ratio: 0.099
- ecrs_improvement_pct: 28.0
- most_sequence_valid: 1.0
- most_index_error_pct: 4.0
- most_cycle_efficiency_pct: 98.0
- workstudy_export_ready: 1.0
- parallel_therblig_rollout_count: 66
- therblig_task_scores: {'walk': 97.7, 'door': 93.5, 'sit_stand': 94.5, 'stairs': 100.0, 'factory_pick': 100.0}

## Task Scores

- walk: 93.7
- door: 93.6
- sit_stand: 96.5
- stairs: 100.0
- factory_pick: 100.0

## Corrections

- No high-priority corrections on the best trial.

## Next Actions

- Render the best L20 candidate as sampled PNG frames for visual review.
- Promote task-specific IK phases: approach, align, contact, act, release, recover.
- Add failure replay for foot slide, door over-twist, low stair clearance, and factory fixture collision.
- Keep real robot deployment blocked until L20 task motion is stable in simulation.
