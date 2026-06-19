# Docker Self-Healing Knowledge Scout

- run_id: `self-healing-scout-20260619T213856Z`
- finished_at: `2026-06-19T21:39:11.904002+00:00`
- downloaded direct_free sources: `10` / `10`
- manual/acquisition queue: `5`
- DB: `self_healing_system_knowledge.db`

## Adoption Decision

ADOPT_PARTIAL: store knowledge and use an observation-only policy gate. Do not edit compose files or restart containers automatically from this scout.

## Downloaded Sources

- [OK] `self_healing_software_survey_arxiv_2024` - A Survey on Self-healing Software System (direct_free, open_access_pdf)
  - URL: https://arxiv.org/pdf/2403.00455
  - local: `downloads\self_healing_software_survey_arxiv_2024.pdf` sha256=`3aeb9662e6a4b7b6f884d49e544ea7f7b055bbcab73651b62268f98dfbc35eeb` bytes=`450384`
- [OK] `autonomic_microservices_mapek_icsa_2022` - A MAPE-K Approach to Autonomic Microservices (direct_free, author_open_pdf)
  - URL: https://www.cs.unibo.it/~lanese/newpublications/fulltext/icsa-c2022-autonomic.pdf
  - local: `downloads\autonomic_microservices_mapek_icsa_2022.pdf` sha256=`ba928c16ce46f6f0da644dc8608701081437a4431fe479511d27978eb0ec1312` bytes=`879428`
- [OK] `self_healing_systems_frameworks_st_andrews_2013` - A Survey of Self-Healing Systems Frameworks (direct_free, institutional_repository_pdf)
  - URL: https://research-repository.st-andrews.ac.uk/bitstream/10023/6026/1/schneider_2013_asurveyofselfhealingsystemsframeworks.pdf
  - local: `downloads\self_healing_systems_frameworks_st_andrews_2013.pdf` sha256=`4864b38f70a011bdbbf40702cd741df5c5006f9a4c576e0c47fe1e25eb523f9c` bytes=`236656`
- [OK] `kubernetes_operator_pattern_official` - Operator pattern (direct_free, official_docs)
  - URL: https://kubernetes.io/docs/concepts/extend-kubernetes/operator/
  - local: `downloads\kubernetes_operator_pattern_official.html` sha256=`e74a28b6773f160c28dd7f6cbdb49eb719c01baade3da037deb90ee12f697e5c` bytes=`494547`
- [OK] `kubernetes_pod_lifecycle_official` - Pod Lifecycle (direct_free, official_docs)
  - URL: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
  - local: `downloads\kubernetes_pod_lifecycle_official.html` sha256=`9aa6d7c49b48d54d153c01d876d964f5c016591e61113739c948b9ac4c00e4ea` bytes=`592060`
- [OK] `cncf_operator_whitepaper` - CNCF Operator White Paper (direct_free, cncf_public_web)
  - URL: https://tag-app-delivery.cncf.io/whitepapers/operator/
  - local: `downloads\cncf_operator_whitepaper.html` sha256=`25d8fc8e114f658764934a9c86382143ca1f46688569579f142f51b055e162eb` bytes=`151049`
- [OK] `docker_restart_policies_official` - Start containers automatically (direct_free, official_docs)
  - URL: https://docs.docker.com/engine/containers/start-containers-automatically/
  - local: `downloads\docker_restart_policies_official.html` sha256=`2e9a97a9180d64e1523482a7c85332874482b4205c39e3ce568bf88b0eef854b` bytes=`495008`
- [OK] `docker_compose_services_healthcheck_official` - Compose file reference: services (direct_free, official_docs)
  - URL: https://docs.docker.com/reference/compose-file/services/
  - local: `downloads\docker_compose_services_healthcheck_official.html` sha256=`6c67674c8ed65ac70a167c247bc5317acf49b1260edc8e5d5f60a18d6cce2271` bytes=`851989`
- [OK] `self_healing_systems_approaches_tuwien_2009` - A survey on self-healing systems: approaches and systems (direct_free, author_public_pdf)
  - URL: https://dsg.tuwien.ac.at/Staff/sd/papers/Zeitschrift%20Computing%20H.%20Psaier.pdf
  - local: `downloads\self_healing_systems_approaches_tuwien_2009.pdf` sha256=`4f5b79f509a68a2c0b5d4818d1ac7dfa93b27b7cf744fdc4100570a888e35b23` bytes=`805988`
- [OK] `self_adaptive_llm_multiagent_arxiv_2023` - Self-Adaptive LLM-Based Multiagent Systems (direct_free, open_access_pdf)
  - URL: https://arxiv.org/pdf/2307.06187
  - local: `downloads\self_adaptive_llm_multiagent_arxiv_2023.pdf` sha256=`69dafc0a27b8e135ab237cc57697a92e0cfdfdb85bece5b2169b4007b9d5a6a5` bytes=`986220`

## Algorithm Rules

- `mapek_phase_separation`: Keep this harness read-only until monitor/analyze evidence and a rollback plan exist.
- `docker_health_is_signal_not_repair`: Use health status to propose actions. Do not auto-restart unhealthy containers without an explicit gated executor.
- `restart_policy_scope`: Prefer checking whether existing restart policy is appropriate before adding external restart loops.
- `operator_reconciliation_idempotence`: Make any future executor idempotent and bounded: same input should yield the same proposed minimal action.
- `human_in_loop_for_high_risk`: Require approval for compose edits, destructive operations, cloud spend, data deletion, or replacing stable workflows.
- `knowledge_after_action`: Record source, evidence, proposed action, execution result, and lesson in DB/Beads/ByteRover index cards.

## Manual Review Queue

- `paid_or_subscription` IEEE Xplore papers on autonomic microservices and MAPE-K: Acquire only through authorized institutional access or user-provided entitlement.
- `manual_review` Docker autoheal and Watchtower GitHub projects: Review licenses, operational risk, and repository health before adopting any code.
- `manual_review` Vendor blog posts about container self-healing: Use as secondary hints only; confirm behavior against official Docker/Kubernetes docs.
- `manual_review` Human-in-the-loop Self-adaptive Systems - Durham repository: Automatic request returned 403; review manually in browser before any download or citation.
- `manual_review` MAPE-K Based Guidelines for Designing Reactive and Proactive Self-adaptive Systems: Automatic request returned 403; review manually in browser before any download or citation.
