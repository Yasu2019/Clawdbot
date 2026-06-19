# Fleet Intelligence Knowledge Scout

- run_id: `fleet-intelligence-scout-20260619T220126Z`
- downloaded direct_free sources: `12` / `12`
- manual/acquisition queue: `4`
- DB: `fleet_intelligence_knowledge.db`

## Adoption Decision

ADOPT_PARTIAL: use as read-only K10 fleet meta-planning knowledge. Do not replace existing dispatch/recovery loops.

## Downloaded Sources

- [OK] `ray_scheduling_official` - Ray Core Scheduling (direct_free, official_docs)
  - URL: https://docs.ray.io/en/latest/ray-core/scheduling/index.html
  - local: `downloads\ray_scheduling_official.html` sha256=`99e4a26ca2d1a436aa4c16f1214160dd54d031cd626bd6507a9ab3a3dcefa520` bytes=`190765`
- [OK] `nomad_advanced_job_scheduling` - Advanced job scheduling (direct_free, official_docs)
  - URL: https://developer.hashicorp.com/nomad/docs/job-scheduling
  - local: `downloads\nomad_advanced_job_scheduling.html` sha256=`386202f47a29cc32e0f000a1aa2b940c7c164f212781966bfe8113e9e29bdf94` bytes=`175172`
- [OK] `buildbot_workers_official` - Buildbot Workers (direct_free, official_docs)
  - URL: https://docs.buildbot.net/current/manual/configuration/workers.html
  - local: `downloads\buildbot_workers_official.html` sha256=`6bb9ee9cff76a0cb4eae33f904d4531ac35e0a17a96be824f745db14450da6b5` bytes=`36869`
- [OK] `buildbot_schedulers_official` - Buildbot Schedulers (direct_free, official_docs)
  - URL: https://docs.buildbot.net/current/manual/configuration/schedulers.html
  - local: `downloads\buildbot_schedulers_official.html` sha256=`23eea3311fa0ba6abd897697c397c85c8257c0dc2b7cf01515ac5c7a1a0b1659` bytes=`171651`
- [OK] `adaptive_async_work_stealing_arxiv_2024` - Adaptive Asynchronous Work-Stealing for Distributed Load-Balancing (direct_free, open_access_pdf)
  - URL: https://arxiv.org/pdf/2401.04494
  - local: `downloads\adaptive_async_work_stealing_arxiv_2024.pdf` sha256=`b028418001e760b20830c7310dcd0cb22c9f014dc4898c5105a277f0895f63aa` bytes=`1460308`
- [OK] `heterogeneous_multiagent_task_allocation_oaepublish_2023` - Heterogeneous multi-agent task allocation based on graph neural networks and ant colony optimization (direct_free, open_access_article)
  - URL: https://www.oaepublish.com/articles/ir.2023.33
  - local: `downloads\heterogeneous_multiagent_task_allocation_oaepublish_2023.html` sha256=`eeffac2ea772642d4a7b07a46e8bf54b85228f324b00a79c48b1bfa7e74dc844` bytes=`387375`
- [OK] `self_adaptive_llm_multiagent_arxiv_2023` - Self-Adaptive LLM-Based Multiagent Systems (direct_free, open_access_pdf)
  - URL: https://arxiv.org/pdf/2307.06187
  - local: `downloads\self_adaptive_llm_multiagent_arxiv_2023.pdf` sha256=`69dafc0a27b8e135ab237cc57697a92e0cfdfdb85bece5b2169b4007b9d5a6a5` bytes=`986220`
- [OK] `openssf_scorecard_official` - OpenSSF Scorecard (direct_free, official_project_site)
  - URL: https://scorecard.dev/
  - local: `downloads\openssf_scorecard_official.html` sha256=`e2ed41c121a06c3f8cf4911c36a5ab43f325918d14b09d9472b35d1f9caa3bcc` bytes=`175549`
- [OK] `first_epss_official` - Exploit Prediction Scoring System (direct_free, official_docs)
  - URL: https://www.first.org/epss/
  - local: `downloads\first_epss_official.html` sha256=`43384169ccf77d709c32c4e74c43881917147e16e9121827fcf45e0de15748c2` bytes=`27963`
- [OK] `first_cvss_v4_official` - CVSS v4.0 Specification Document (direct_free, official_docs)
  - URL: https://www.first.org/cvss/specification-document
  - local: `downloads\first_cvss_v4_official.html` sha256=`27940458126bb1519d3006935edd21ad9cec251fbc419c6927ef983baf755ba4` bytes=`119212`
- [OK] `opa_docs_official` - Open Policy Agent Documentation (direct_free, official_docs)
  - URL: https://openpolicyagent.org/docs
  - local: `downloads\opa_docs_official.html` sha256=`f0d1c69ff6fc56edb83612e643c4f49d75c78a4905390b182bf2be952d69fa19` bytes=`279745`
- [OK] `fleetdm_rest_api_official` - Fleet REST API (direct_free, official_docs)
  - URL: https://fleetdm.com/docs/rest-api
  - local: `downloads\fleetdm_rest_api_official.html` sha256=`8c16c9d7b42b35bfc488485390e44a51e149f18e62da08485d4e9c4571381fa8` bytes=`1638977`

## Algorithm Rules

- `meta_layer_no_replacement`: Generate plans from their outputs; do not replace or duplicate those loops.
- `compound_growth_score`: Prioritize tasks with high impact, high parallelism, high learning value, and low safety risk.
- `heterogeneous_capability_matching`: Match job class to node role, live resource state, thermal headroom, and historic success.
- `work_stealing_fallback`: Use bounded low-risk backlog pulling for idle nodes after K10 assigns protected priorities.
- `security_as_growth_multiplier`: Score CVSS/EPSS/OpenSSF/secret risk before adopting code or sending jobs to a node.
- `bounded_self_evolution`: Keep autonomous evolution in propose/dry-run mode until tests, rollback, approval, and evidence are present.

## Manual Review Queue

- `manual_review` Commercial agent orchestration products: Use only as architecture inspiration; avoid vendor lock-in and verify against local privacy/cost rules.
- `manual_review` GitHub autonomous agent frameworks: Review license, security posture, and sandbox model before cloning or executing.
- `manual_review` FleetDM/osquery deployment: Treat as design candidate only; deployment would require a separate approved implementation plan.
- `manual_review` Cranfield multi-agent task allocation survey: Automatic request returned a bot-check page; review manually before download or citation.
