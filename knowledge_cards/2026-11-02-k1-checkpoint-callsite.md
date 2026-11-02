# Sanitized checkpoint call-site finding — 2026-11-02 JST

An exact source review of an existing long-running fill worker found the input load and progress callback before the main run, while summary, history and field files are written only after the run returns. No in-case incremental checkpoint call was verified at that call site. A separate diagnostic append is not evidence of solver state recovery. External scheduler recovery was not inspected, so its existence remains unknown.

The process CPU counter continued rising while the progress log remained at the same step for about 13 minutes. This shows activity without proving useful case progress or a hang. The current bounded output inventory contained only the progress log and no checkpoint-named file. Preserve the existing task and outputs; do not stop or restart without ownership and a verified recovery path. Hold new unattended FEM dispatch until case-specific restart evidence, resource budget and authorization are satisfied.

This note omits host identity, addresses, accounts, process IDs, internal paths, raw logs and credentials. Source: reviewed note INC-K1MMENT-OF76F3A-NATIVE-OUTPUT-CALLSITE-20261102T1100JST.md.
