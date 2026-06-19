# Robotics Gait Knowledge Scout

- generated_at: 2026-06-20T06:13:18.247071+09:00
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

## Failed Direct-Free Attempts

- none

## Algorithm Rules Added

- **support_polygon_gate**: Reject or correct frames where the character appears to tip despite planted feet.
- **foot_contact_lock**: Lock planted foot, solve pelvis/knee with IK, and release at toe-off.
- **heel_toe_phase**: Add keyframe markers or foot roll constraints around contact transitions.
- **root_com_smoothing**: Low-pass smooth pelvis/root travel and keep stride distance consistent with footfall timing.
- **swing_foot_clearance**: Clamp swing arc to model scale and terrain height.
- **ik_continuity_gate**: Use bounded per-frame joint deltas and smooth correction weights across contact phases.

## Acquisition Queue

| id | status | next_action |
| --- | --- | --- |
| ieee_recent_humanoid_foot_placement | paid_or_subscription | Use metadata only unless institutional access/licensing is confirmed. |
| springer_zmp_chapters | paid_or_subscription | Queue for manual review; do not download chapters behind access control. |
| robotis_op3_walking_source | manual_review | Review license and extract implementation notes separately if useful. |
| drake_humanoid_examples | manual_review | Review current examples and license before importing code or formulas. |

## Motion Pipeline Use

- Score generated walks with foot contact, support polygon, root/CoM smoothness, swing clearance, and IK continuity.
- Use the score as an observation-first gate before automatic destructive edits.
- For mecha/proportion-mismatched rigs, prefer bounded correction weights over literal humanoid dynamics.
