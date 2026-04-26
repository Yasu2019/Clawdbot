# Cmux Orchestration

## Purpose

Use the cmux pattern to split work by role instead of asking one model to do everything.
Prefer local-first execution and explicit fallback rules.

## Current Roles

- `Orchestrator`: Antigravity
  - Routes tasks, applies fallback rules, keeps loops bounded.
- `Coder`: Codex (`gpt-5.4`)
  - Primary for implementation, refactors, scripts, and Docker-safe changes.
  - Local fallback: `qwen2.5-coder:14b`
- `Reviewer`: Claude-class review role
  - Use for design review, code review, quality concerns, and document cleanup.
  - Local fallback: `qwen3:14b`
- `Tester`: Local tools
  - Prefer `pytest`, `rspec`, `playwright`, log inspection, and direct verification over opinion.
- `Security`: Local tools plus reviewer mindset
  - Prefer `brakeman`, `bundler-audit`, `semgrep`, `bandit`.
- `DOE/Statistics`: R toolchain
  - Prefer `AlgDesign`, `DoE.base`, `FrF2`, `rsm`, `ggplot2`.
- `Local LLM Router`: Ollama
  - Lightweight: `sam860/lfm2.5:1.2b`
  - Main local reply: `qwen3:8b`
  - Higher-accuracy local fallback: `qwen3:14b`
  - Code fallback: `qwen2.5-coder:14b`
  - Vision: `minicpm-v`

## Routing Rules

1. Preprocess with a local model when possible.
2. Route implementation tasks to the coder role.
3. Route verification to local test tools before asking another model.
4. Route security-sensitive checks to local scanners first.
5. Route statistics, DOE, ANOVA, and optimization to R-based tools.
6. Only escalate to cloud/API models when local execution is insufficient.

## Fixed Route Table

- `Code implementation`
  - Primary: `gpt-5.4`
  - Fallback: `qwen2.5-coder:14b` -> `qwen2.5-coder:7b`
- `Code review / design review`
  - Primary: reviewer role
  - Fallback: `qwen3:14b` -> `qwen3:8b`
- `Testing / validation`
  - Primary: local test tools
  - Fallback: `qwen3:8b` only for explanation, never instead of real test output
- `Security`
  - Primary: local scanners
  - Fallback: reviewer role
- `DOE / statistics / optimization`
  - Primary: R toolchain
  - Fallback: `gpt-5.4` for interpretation only
- `Fast local chat / classification`
  - Primary: `sam860/lfm2.5:1.2b`
  - Fallback: `qwen3:8b`
- `Summarization / orchestration`
  - Primary: Antigravity
  - Fallback: `qwen3:8b`

## Trigger Hints

- Route to `Coder` when the request includes words like `implement`, `fix`, `patch`, `refactor`, or `script`.
- Route to `Reviewer` when the request includes `review`, `risk`, `regression`, or `design review`.
- Route to `Tester` when the request includes `test`, `verify`, `playwright`, `pytest`, or `validation`.
- Route to `Security` when the request includes `security`, `audit`, `semgrep`, `bandit`, or `brakeman`.
- Route to `DOE/Statistics` when the request includes `DOE`, `ANOVA`, `RSM`, `D-optimal`, or `statistics`.
- Route to `Local LLM` when the request is lightweight classification, routing, or fast chat handling.
- Route to `Orchestrator` when the request is about coordination, splitting work, summarization, or cmux itself.

## Task Flow

1. Local LLM or deterministic preprocessing
2. Antigravity classification
3. Codex implementation
4. Tester validation
5. Security checks
6. Reviewer pass
7. Retry loop only if a concrete defect remains

## Fallback Rules

- If Codex is unavailable:
  - use `qwen2.5-coder:14b`
  - then escalate to reviewer support only if still blocked
- If reviewer is unavailable:
  - use `qwen3:14b`
- If all cloud APIs are unavailable:
  - continue in full local mode
- If a loop exceeds 10 iterations:
  - stop autonomous retries and summarize the blocker

## Practical Guidance

- For implementation, do not ask the reviewer to write first-pass code.
- For tests, prefer actual tool output over LLM judgment.
- For email and operational workflows, preserve the existing local-first rules in `TOOLS.md`.
- For Docker changes, prefer non-invasive integration and external harnesses.

## Current Intent

This workspace uses cmux as an orchestration policy, not as a hard requirement to run multiple agents in parallel for every task.
Use the lightest route that can complete the work correctly.
