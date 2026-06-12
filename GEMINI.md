# GEMINI.md - Gemini / Gemini CLI Guardrails

## Critical Instruction
Do not rewrite, optimize, beautify, or restructure UI, layout, CSS, routes, shared partials, or application architecture unless explicitly requested by the user.

## Backup First
Before large or risky changes:
- Run a backup commit.
- Push to GitHub if possible.
- If GitHub push is unavailable, create a local backup branch.
- Report backup result before making changes.

## Forbidden Actions
- Layout rewrite
- CSS/Tailwind modification
- Routes modification
- Broad refactor
- File/folder restructuring
- Formatting-only large diff
- Dependency changes without explicit request

## Mandatory Behavior
Before coding:
- Clarify ambiguity or choose the smallest safe interpretation.
- List exact files to be changed.
- Identify protected files.

During coding:
- Apply the smallest possible diff.

After coding:
- Report changed files and reasons.
- Report tests/checks run.
- Report backup commit/branch.

## Rails Special Rule
Treat the following as immutable unless explicitly requested:
- app/views/layouts/*
- app/views/shared/*
- app/assets/*
- app/javascript/*
- config/routes.rb

## Incident & Failure Management Rule (RCA Protocol)
If a past instruction is missed, a code failure occurs, or the user points out a quality incident, the AI MUST immediately:
1. Conduct a deep Root Cause Analysis (RCA) using frameworks such as:
   - 5 Whys (なぜなぜ分析)
   - Fishbone Diagram / Ishikawa (特性要因図)
   - Fault Tree Analysis (FTA)
   - Logical Tree (ロジカルツリー)
   - FMEA (Failure Mode and Effects Analysis)
2. Document the findings in a persistent .md artifact (e.g., quality_incident_report_XXX.md).
3. Explicitly define countermeasures and strict rules to prevent recurrence.
4. Record the rule in the relevant core files (like Beads, Byterover, or this GEMINI.md).
5. Always confirm the countermeasure implementation plan with the user before resuming execution.
