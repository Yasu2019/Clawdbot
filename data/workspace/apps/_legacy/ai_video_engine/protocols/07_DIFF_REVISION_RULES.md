# Differential Revision Rules

## Rule 1
Do not rewrite the entire prompt unless the concept itself failed.

## Rule 2
If the issue is camera-related, edit only:
- camera
- pose_constraints
- start_frame / end_frame

## Rule 3
If the issue is anatomy-related, edit only:
- motion
- exclusions
- quality_targets

## Rule 4
If the issue is identity drift, edit only:
- subject
- identity references
- quality_targets

## Rule 5
Log every revision in a changelog.
Recommended format:
- version
- changed block
- reason
- expected effect
- observed result
