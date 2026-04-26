# Antigravity Guardrails

## Operating Principle
Even if autonomous execution is enabled, safety rules override autonomy.

## Mandatory Flow
1. Analyze task.
2. Estimate change scope.
3. If large or risky, run GitHub backup first.
4. List files to change.
5. Apply minimal diff.
6. Run relevant checks.
7. Report changed files and backup reference.

## Large Change Definition
- Multiple files
- Refactor
- Layout/UI change
- Routes change
- Dependency change
- Docker/OpenClaw orchestration change

## Forbidden Without Explicit Request
- Rails layout rewrite
- CSS/Tailwind rewrite
- routes.rb rewrite
- broad refactor
- Docker compose restructuring
- deleting files

## Backup Enforcement
Before large change:
- git add -A
- git commit -m "backup before Antigravity change"
- git push
If push fails:
- create local branch backup/antigravity-YYYYMMDD-HHMMSS
- report push failure
