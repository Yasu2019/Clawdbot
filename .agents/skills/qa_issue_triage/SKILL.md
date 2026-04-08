---
name: qa_issue_triage
description: "Use when triaging customer complaints, quality issues, inspection anomalies, or first-pass defect reports in this project. Focus on separating confirmed facts, missing information, likely next checks, and safe immediate actions before deeper root-cause work."
---

# QA Issue Triage Skill

Use this skill for first-pass quality issue triage before full Why-Why, FMEA, or corrective-action work.

## Workflow

1. Separate the intake into:
   - observed symptoms
   - confirmed facts
   - missing information
   - immediate containment ideas
2. Identify whether the issue is closer to:
   - customer complaint
   - internal defect
   - inspection anomaly
   - process drift
3. Avoid premature root-cause claims.
4. Produce next-step checks that a human can execute:
   - lot / trace check
   - photo / evidence request
   - process history review
   - temporary containment
5. If the user is moving toward Why-Why or FMEA, hand off a clean triage summary instead of mixing phases.

## Rules

- Do not invent evidence.
- Keep confirmed facts and hypotheses separate.
- Prefer practical next actions over long theory.
- Escalate uncertainty clearly when images, lot info, or measurements are missing.

## Read first when relevant

- `clawstack_v2/docker/quality_dashboard/app.py`
- `data/workspace/email_search_query.py`
- `data/workspace/complaint_query_quality_status.json`

