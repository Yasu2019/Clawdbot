# Docker Self-Healing Knowledge

This folder stores a legal, bounded knowledge scout for Docker/system self-healing and an observation-first policy engine.

## Scope

- Collect only `direct_free` public sources automatically.
- Queue registration-only, paid, unclear-license, or high-risk code sources for manual review.
- Keep raw source metadata, local file hashes, extracted algorithm rules, and implementation recommendations separate.
- Do not modify `docker-compose*.yml`, restart containers, delete data, or replace stable workflows from this folder.

## Files

- `collect_self_healing_system_knowledge.py`: downloads direct-free sources and builds `self_healing_system_knowledge.db`.
- `docker_self_healing_policy_engine.py`: evaluates Docker evolution/self-healing gate decisions from metrics JSON.
- `self_healing_system_knowledge_report.md`: generated source and adoption report.
- `docker_self_healing_rules.json`: generated compact rules for other harnesses.
- `downloads/`: downloaded direct-free sources with hashes stored in the DB.

## Adoption

Current decision: `ADOPT_PARTIAL`.

Use the policy engine as a read-only gate before any future executor. A future mutation-capable executor must require:

- evidence capture,
- explicit approval for high-risk actions,
- backup and rollback,
- bounded retries,
- incident/knowledge recording.
