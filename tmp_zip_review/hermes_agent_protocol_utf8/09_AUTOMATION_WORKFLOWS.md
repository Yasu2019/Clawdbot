# Automation Workflows

## Workflow A: Post-task reflection
Trigger:
- task ended

Steps:
1. collect trace metadata
2. collect tool log summary
3. run reflection model
4. score lesson quality
5. store raw reflection
6. optionally store approved lesson in Qdrant

## Workflow B: Failure-first memory generation
Trigger:
- error or partial success

Steps:
1. classify failure type
2. extract root cause candidate
3. store incident lesson
4. create retrieval tags
5. flag for consolidation if repeated

## Workflow C: Repeated-lesson consolidation
Trigger:
- enough similar incidents collected

Steps:
1. cluster related memory entries
2. summarize common cause patterns
3. create stable playbook draft
4. optionally require human approval
5. publish to tool_playbooks

## Workflow D: Pre-task memory injection
Trigger:
- new task created

Steps:
1. classify task
2. fetch environment constraints
3. fetch relevant playbooks
4. fetch top past experiences
5. build compact memory context
6. inject only if thresholds pass

## Operational note
Keep memory injection compact.
Large memory dumps reduce model quality.
