# Robotics Gait Knowledge Scout

- generated_at: 2026-06-20T12:04:17.433807+09:00
- adoption: ADOPT_PARTIAL into existing motion_lab gait QA and improvement algorithm
- legal_policy: metadata-first; direct_free downloads only; paid/unclear sources queued
- scope: humanoid/biped walking, ZMP/CoM, foot contact, IK, support polygon, gait timing

## Downloaded Direct-Free Sources

| id | category | bytes | local_path |
| --- | --- | ---: | --- |
| mit_underactuated_humanoids | course_notes | 39151 | `downloads\mit_underactuated_humanoids.html` |
| kajita_preview_control_zmp | paper | 581476 | `downloads\kajita_preview_control_zmp.pdf` |
| dekker_zmp_stable_biped | thesis_report | 4719311 | `downloads\dekker_zmp_stable_biped.pdf` |
| sardain_bessonnet_cop_zmp | paper | 334274 | `downloads\sardain_bessonnet_cop_zmp.pdf` |
| auxiliary_zmp_walking_generator | paper | 465744 | `downloads\auxiliary_zmp_walking_generator.pdf` |
| durus_dynamic_efficient_bipedal_locomotion | paper | 3834317 | `downloads\durus_dynamic_efficient_bipedal_locomotion.pdf` |
| rss_multicontact_feasibility | paper | 2877951 | `downloads\rss_multicontact_feasibility.pdf` |
| pmc_heel_contact_toe_off | paper_html | 198962 | `downloads\pmc_heel_contact_toe_off.html` |
| pmc_omnidirectional_walking_generator | paper_html | 228934 | `downloads\pmc_omnidirectional_walking_generator.html` |
| mit_littledog_dynamic_ik | paper | 731366 | `downloads\mit_littledog_dynamic_ik.pdf` |
| isaac_lab_robot_learning_docs | robot_learning_framework | 213 | `downloads\isaac_lab_robot_learning_docs.html` |
| isaac_lab_imitation_learning_docs | imitation_learning | 43238 | `downloads\isaac_lab_imitation_learning_docs.html` |
| behavior_1k_project | household_embodied_ai | 208136 | `downloads\behavior_1k_project.html` |
| behavior_1k_pmlr | household_embodied_ai_paper | 18907 | `downloads\behavior_1k_pmlr.html` |
| robocasa_project | kitchen_robot_learning | 32450 | `downloads\robocasa_project.html` |
| robocasa_github | kitchen_robot_learning_source | 313703 | `downloads\robocasa_github.html` |
| ros_industrial_home | factory_robotics | 162785 | `downloads\ros_industrial_home.html` |
| ros_industrial_training_docs | factory_robotics_training | 26248 | `downloads\ros_industrial_training_docs.html` |
| unity_ml_agents_docs | multi_agent_visual_training | 40043 | `downloads\unity_ml_agents_docs.html` |
| unreal_learning_agents_docs | high_fidelity_agent_training | 25778 | `downloads\unreal_learning_agents_docs.html` |
| micro_ros_overview | edge_robot_control | 686 | `downloads\micro_ros_overview.html` |

## Failed Direct-Free Attempts

- none

## Algorithm Rules Added

- **support_polygon_gate**: Reject or correct frames where the character appears to tip despite planted feet.
- **foot_contact_lock**: Lock planted foot, solve pelvis/knee with IK, and release at toe-off.
- **heel_toe_phase**: Add keyframe markers or foot roll constraints around contact transitions.
- **root_com_smoothing**: Low-pass smooth pelvis/root travel and keep stride distance consistent with footfall timing.
- **swing_foot_clearance**: Clamp swing arc to model scale and terrain height.
- **ik_continuity_gate**: Use bounded per-frame joint deltas and smooth correction weights across contact phases.
- **vectorized_experience_collection**: Train headless at scale, then export score, success/NG, collision, energy, and GIF/GLB evidence for dashboard inspection.
- **household_task_curriculum**: Score simple robot tasks as walk -> reach -> open/close -> sit/stand -> multi-step kitchen or care assistance.
- **factory_task_curriculum**: Add separate factory reward terms for fixture alignment, part handling, safety-zone avoidance, and failed-grasp recovery.
- **sim_to_edge_deployment_gate**: Convert learned behaviors into Raspberry Pi/ROS 2/microcontroller profiles only after offline replay and safety gates pass.

## Acquisition Queue

| id | status | next_action |
| --- | --- | --- |
| ieee_recent_humanoid_foot_placement | paid_or_subscription | Use metadata only unless institutional access/licensing is confirmed. |
| springer_zmp_chapters | paid_or_subscription | Queue for manual review; do not download chapters behind access control. |
| robotis_op3_walking_source | manual_review | Review license and extract implementation notes separately if useful. |
| drake_humanoid_examples | manual_review | Review current examples and license before importing code or formulas. |
| behavior_1k_dataset_assets | manual_review | Review license, disk size, simulator requirements, and access rules before downloading assets. |
| robocasa_kitchen_assets | manual_review | Review license/terms and size before downloading kitchen assets or demonstrations. |
| isaac_sim_installation | manual_review | Install only after GPU/driver compatibility check and user approval for large downloads. |
| raspberry_pi_ai_kit | manual_review | Official site returned HTTP 403 to automated fetch; keep metadata only and review manually in browser. |

## Motion Pipeline Use

- Score generated walks with foot contact, support polygon, root/CoM smoothness, swing clearance, and IK continuity.
- Use the score as an observation-first gate before automatic destructive edits.
- For mecha/proportion-mismatched rigs, prefer bounded correction weights over literal humanoid dynamics.
