# Human Motion Retargeting Knowledge Scout

- generated_at: 2026-06-20T04:00:27.864058+09:00
- adoption: ADOPT_PARTIAL into existing motion_lab web_sourced knowledge store
- legal_policy: metadata-first; direct_free downloads only; registration/paid/unclear sources queued
- scope: human walking, mocap retargeting, root motion, foot contact, skeleton/proportion mismatch

## Downloaded Direct-Free Sources

| id | category | bytes | local_path |
| --- | --- | ---: | --- |
| cmu_bvh_readme | dataset_notes | 13248 | `downloads\cmu_bvh_readme.txt` |
| cmu_bvh_index | dataset_index | 68400 | `downloads\cmu_bvh_index.txt` |
| mwni_blender_retargeting_readme | tooling | 2759 | `downloads\mwni_blender_retargeting_readme.md` |
| contact_aware_retargeting_iccv2021 | paper | 5134509 | `downloads\contact_aware_retargeting_iccv2021.pdf` |
| non_humanoid_human_motion_disney2010 | paper | 3034499 | `downloads\non_humanoid_human_motion_disney2010.pdf` |
| correspondence_free_online_retargeting_3dv | paper | 3736218 | `downloads\correspondence_free_online_retargeting_3dv.pdf` |
| dense_geometric_interaction_retargeting_neurips2024 | paper | 17019611 | `downloads\dense_geometric_interaction_retargeting_neurips2024.pdf` |
| general_motion_retargeting_humanoid_icra | paper | 781075 | `downloads\general_motion_retargeting_humanoid_icra.pdf` |
| rokoko_blender_retargeting | tooling | 39906 | `downloads\rokoko_blender_retargeting.html` |
| sidefx_cmu_kinefx_retargeting | tooling | 62863 | `downloads\sidefx_cmu_kinefx_retargeting.html` |

## Failed Direct-Free Attempts

- none

## Practical Rules Extracted

- **retargeting_preflight**: Match or explicitly map skeleton hierarchy from root outward; mismatched shoulder/hip/clavicle assumptions are a common cause of unnatural arms and torso.
- **t_pose_baseline**: Store a clean reference pose before applying motion. CMU BVH conversions add a first-frame T-pose because retargeting quality depends on rest-pose alignment.
- **root_motion_policy**: Decide early whether root translation is preserved, baked to hips, or constrained. Natural walking needs coherent root travel; copying all object transforms blindly can launch scaled models out of frame.
- **foot_contact**: Detect stance phases and lock/support feet during ground contact to reduce sliding. Add IK foot correction when source and target proportions differ.
- **contact_geometry**: Skeleton-only retargeting misses self-contact and mesh interpenetration. For production, run geometry/contact checks for hands, feet, torso, and armor plates.
- **mecha_or_nonhuman**: For mecha/proportion-mismatched characters, use human motion as intent, not literal joint data. Build key-pose correspondences and optimize readable, physically plausible target poses.
- **frame_rate**: Preserve source frame rate metadata. CMU data was captured at 120 fps; wrong frame timing changes perceived gait weight and speed.
- **ignore_uncaptured_digits**: Ignore finger/thumb joints when the source dataset says they were not captured. Dead channels can create noisy or misleading target poses.

## Acquisition Queue

| id | status | next_action |
| --- | --- | --- |
| amass_dataset | free_registration | Review license and register/authorize before download. |
| smpl_model | free_registration | Review license; needed only if SMPL-based retargeting pipeline is adopted. |
| mixamo | free_registration | Use only through authorized account and current Adobe terms; avoid bulk scraping. |
| mocap_online_free_pack | manual_review | Review current checkout/license terms before asset download. |
| makehuman_makewalk_wiki | manual_review | Useful source, but direct download from this host returned connection refused in the bounded run; retry later or capture metadata only. |

## Indexed Motion Candidates

- CMU locomotion candidate rows: 420
- JSON export: `cmu_locomotion_candidates.json`

## Next Implementation Use

- Add a motion QA gate: foot-contact slide distance, root-travel consistency, knee/hip range, and mesh interpenetration.
- For existing Mixamo/CMU motions, prefer rotation-only bone curves plus explicit root-motion policy.
- For mecha models, use key-pose intent mapping and IK/contact correction instead of literal human joint transfer.
