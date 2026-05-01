# Incident Log 窶・繝医Λ繝悶Ν險倬鹸繝ｻ蜀咲匱髦ｲ豁｢蜿ｰ蟶ｳ

譛ｬ繝輔ぃ繧､繝ｫ縺ｯ縲√す繧ｹ繝・Β縺ｫ逋ｺ逕溘＠縺滄囿螳ｳ繝ｻ荳榊・蜷医→縺昴・譬ｹ譛ｬ蜴溷屏繝ｻ菫ｮ豁｣蜀・ｮｹ繝ｻ蜀咲匱髦ｲ豁｢遲悶ｒ險倬鹸縺励∪縺吶・菫ｮ豁｣繧定｡後▲縺溷�ｴ蜷医・縲∝ｿ・★縺薙・繝輔ぃ繧､繝ｫ縺ｫ繧ｨ繝ｳ繝医Μ繧定ｿｽ蜉�縺励※縺上□縺輔＞縲・
---

## INC-019: Local self-growth and scout loops were incomplete and inconsistent
| Item | Details |
|---|---|
| **Date** | 2026-04-12 |
| **Detected By** | Follow-up audit of self-growth, scout freshness, and Qdrant hygiene |
| **Impact** | The system had partial self-improvement parts, but they were not fully aligned: local scout refresh depended on brittle n8n patching, approved RL skills were syncing to `universal_knowledge` instead of `agent_self_growth_memory`, and startup retrieval verification was not recorded. |
| **Root Cause (5 Why)** | **Why1**: The project had design intent for self-growth and memory hygiene, but not a complete local-only operational loop. **Why2**: AI Scout safe-source patching still depended on an n8n API path that could fail independently of the actual local collection logic. **Why3**: RLAnything skill sync used a generic knowledge collection instead of the dedicated self-growth collection named in governance. **Why4**: No pre-tool or start-of-session verification existed to prove that stored self-growth memory was being queried on future sessions. **Why5**: Memory hygiene thresholds were documented, but no active archive guard was enforcing them on the actual collection. |
| **Fix Summary** | Added a local no-API-cost scout runner and freshness watchdog, added a self-growth memory hygiene guard for `agent_self_growth_memory`, redirected RL skill sync to `agent_self_growth_memory`, and added a `PreToolUse` hook to record first-use retrieval attempts per session. |
| **Files Changed** | `data/workspace/run_ai_strategy_scout_local.py`, `data/workspace/ai_strategy_scout_watchdog.py`, `scripts/start_ai_strategy_scout_watchdog.ps1`, `data/workspace/agent_self_growth_memory_hygiene.py`, `scripts/start_agent_self_growth_memory_hygiene.ps1`, `data/workspace/rl_anything/hook_pre_tool_use.py`, `data/workspace/rl_anything/qdrant_sync.py`, `.claude/settings.json`, `docs/INCIDENT_LOG.md` |
| **Validation** | Local scout refresh can run without n8n API writes, self-growth Qdrant sync now targets `agent_self_growth_memory`, hygiene status can report thresholds without deleting healthy data, and startup retrieval verification writes per-session status with top hits or errors. |
| **Lessons Learned** | For self-improving systems, 窶徇emory exists窶・is not enough. The store, retrieval path, and hygiene path must target the same collection, and there should be an explicit log proving that startup retrieval was attempted. |
| **Recurrence Prevention** | Keep AI Scout on local/no-cost collection paths where possible, enforce a dedicated hygiene script on the actual self-growth collection, and keep first-use retrieval verification enabled through repo-local hook config. |
 
---
 
## INC-053: n8n API authentication failure (401) and patrol weakness persistence
| Field | Detail |
|---|---|
| **Date** | 2026-04-25 11:50 JST |
| **Detection** | `continuous_system_improvement.py` reported high-severity weakness: `n8n API authentication failed (401)`. System health summary showed persistent failure even after credentials were updated in `.env`. |
| **Impact** | Automated n8n maintenance tasks (scheduled report sync, workflow healer, etc.) could fail silently due to auth drift. Patrol summaries stayed "dirty" with high-risk alerts, masking other potential issues. |
| **Root Cause (5 Why)** | **Why1**: n8n v2.6.4 (containerized) requires API keys to be explicitly generated in the UI; environment-variable keys are ignored if not in the DB. **Why2**: The user's `.env` password `Foxconnjpn75` was correct, but the patrol script used `admin@clawstack.local` as a default email for the fallback login, which was incorrect. **Why3**: The fallback login process in the patrol script did not correctly manage sessions/cookies, causing the subsequent `/rest/workflows` check to fail with 401 even after a successful login. **Why4**: The patrol script had redundant reporting: it both probed n8n auth explicitly and included it in a generic host-api-inventory loop, causing double-reporting of weaknesses. **Why5**: The patrol logic lacked a robust multi-strategy auth resolver (API Key -> Cookie Session -> User/PW fallback) that accounted for specific n8n backend behavior. |
| **Fix** | Updated `data/workspace/continuous_system_improvement.py` to: (1) Use `requests.Session` for cookie-based fallback. (2) Explicitly pass the `n8n-auth` cookie in subsequent requests. (3) Prioritize the correct user email `y.suzuki.hk@gmail.com`. (4) Exclude `n8n_auth` from the generic reporting loop to avoid double-alerts. Updated `scheduled_report_search.py` to improve error logging and follow the same auth fallback logic. |
| **Files** | `data/workspace/continuous_system_improvement.py`, `data/workspace/scheduled_report_search.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python data/workspace/continuous_system_improvement.py --once` now reports `n8n API authentication is valid: url=http://127.0.0.1:5679/rest/workflows status=200`. Weakness count dropped from 3 to 1. `scheduled_report_search.py` manual run confirmed sync capability. |
| **Lessons Learned** | For n8n on this machine, API Keys are unreliable. Always implement a robust Cookie-based session fallback using the user's primary email. Patrol reporting must be de-duplicated when a component has both a dedicated probe and a generic inventory check. |
| **Prevention** | Standardize n8n auth helpers across all maintenance scripts. Ensure the patrol summary uses a single canonical source for each component's health status. |

---

## INC-001: C 繝峨Λ繧､繝門ｮｹ驥乗椡貂・ｼ・ost_gmail_incremental_* 荳譎ゅヵ繧ｩ繝ｫ繝譛ｪ蜑企勁・・
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-05 |
| **逋ｺ隕区婿豕・* | Docker 繧ｨ繝ｳ繧ｸ繝ｳ縺後ヵ繝ｪ繝ｼ繧ｺ縺励∝・繧ｳ繝ｳ繝・リ縺悟●豁｢縲・ 繝峨Λ繧､繝匁ｮ句ｮｹ驥上′縺ｻ縺ｼ 0 繝舌う繝医・|
| **蠖ｱ髻ｿ遽・峇** | Docker Desktop 蜈ｨ菴難ｼ・ATF System, QA Dashboard, Gateway 遲峨☆縺ｹ縺ｦ縺ｮ繧ｳ繝ｳ繝・リ・榎
| **譬ｹ譛ｬ蜴溷屏** | `data/workspace/host_gmail_incremental_sync.py` 縺ｮ 110 陦檎岼縺ｧ `tempfile.mkdtemp(prefix="host_gmail_incremental_")` 縺ｫ繧医ｊ荳譎ゅョ繧｣繝ｬ繧ｯ繝医Μ繧剃ｽ懈・縺吶ｋ縺後～finally` 繝悶Ο繝・け縺ｫ `shutil.rmtree()` 縺檎┌縺上∝・逅・ｮ御ｺ・ｾ後ｂ繝輔か繝ｫ繝縺梧ｮ句ｭ倥よｯ主・邏・370MB ﾃ・1 蛟九・繝壹・繧ｹ縺ｧ闢・ｩ阪＠縲∵焚譎る俣縺ｧ謨ｰ蜊√懈焚逋ｾ GB 縺ｫ蛻ｰ驕斐・|
| **菫ｮ豁｣蜀・ｮｹ** | `finally` 繝悶Ο繝・け縺ｫ `shutil.rmtree(tempdir, ignore_errors=True)` 繧定ｿｽ蜉�縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | [host_gmail_incremental_sync.py](file:///d:/Clawdbot_Docker_20260125/data/workspace/host_gmail_incremental_sync.py) L221-228 |
| **讀懆ｨｼ邨先棡** | 菫ｮ豁｣蠕・4 蛻・俣逶｣隕・竊・譁ｰ隕上ざ繝溘ヵ繧ｩ繝ｫ繝 0 蛟九・8.12 GB 繧貞叉譎りｧ｣謾ｾ縲・|
| **霑ｽ蜉�蟇ｾ遲・* | (1) 謇句虚貂・祉繧ｹ繧ｯ繝ｪ繝励ヨ `scripts/clawstack_janitor.ps1` 繧帝・蛯吶・2) QA Dashboard 縺ｫ縲粂ost Maintenance縲阪き繝ｼ繝峨ｒ霑ｽ蜉�縲・|
| **蜀咲匱髦ｲ豁｢** | 譛ｬ繧､繝ｳ繧ｷ繝・Φ繝医ｒ螂第ｩ溘↓ AGENTS.md 縺ｫ縲御ｿｮ豁｣蠕後・險倬鹸鄒ｩ蜍吶阪Ν繝ｼ繝ｫ繧定ｿｽ蜉�縲・|

### 謨呵ｨ難ｼ・essons Learned・・
1. **`tempfile.mkdtemp()` 繧剃ｽｿ縺・�ｴ蜷医・縲∝ｿ・★ `try...finally` 縺ｧ `shutil.rmtree()` 繧貞・繧後ｋ縺薙→縲・* Python 縺ｮ `tempfile.TemporaryDirectory()` 繧ｳ繝ｳ繝・く繧ｹ繝医・繝阪・繧ｸ繝｣繧剃ｽｿ縺医・閾ｪ蜍募炎髯､縺輔ｌ繧九・2. **螳壽悄螳溯｡鯉ｼ・ron / daemon・峨せ繧ｯ繝ｪ繝励ヨ縺ｯ 1 蝗槭≠縺溘ｊ縺ｮ繝・ぅ繧ｹ繧ｯ菴ｿ逕ｨ驥上′蟆上＆縺上※繧ゅ∬塘遨阪☆繧九→閾ｴ蜻ｽ逧・↓縺ｪ繧九・* 譁ｰ縺励＞螳壽悄螳溯｡後せ繧ｯ繝ｪ繝励ヨ繧呈嶌縺城圀縺ｯ縲∝ｿ・★縲悟ｾ檎援莉倥￠縲阪さ繝ｼ繝峨・譛臥┌繧偵Ξ繝薙Η繝ｼ縺吶ｋ縺薙→縲・3. **繝・ぅ繧ｹ繧ｯ譫ｯ貂・・騾｣骼夜囿螳ｳ繧貞ｼ輔″襍ｷ縺薙☆縲・* Docker 繧ｨ繝ｳ繧ｸ繝ｳ縲￣ostgreSQL縲ヽedis縲ヽails 縺吶∋縺ｦ縺悟ｷｻ縺肴ｷｻ縺医〒蛛懈ｭ｢縺吶ｋ縲よ掠譛滓､懃衍縺ｮ莉慕ｵ・∩・・ptime Kuma 縺ｮ繝・ぅ繧ｹ繧ｯ逶｣隕也ｭ会ｼ峨ｒ讀懆ｨ弱☆繧九・
---

## INC-002: IATF Rails 繧｢繝励Μ 500 繧ｨ繝ｩ繝ｼ・・B_PORT 荳堺ｸ閾ｴ・・
| 鬆・岼 | 蜀・ｮｹ |
| --- | --- |
| **逋ｺ逕滓律** | 2026-04-05 |
| **逋ｺ隕区婿豕・* | `http://127.0.0.1:3003/users/sign_in` 縺ｫ繧｢繧ｯ繧ｻ繧ｹ縺吶ｋ縺ｨ HTTP 500 縺瑚ｿ斐ｋ縲ゅΘ繝ｼ繧ｶ繝ｼ縺九ｉ縺ｮ蝣ｱ蜻翫・|
| **蠖ｱ髻ｿ遽・峇** | IATF16949 蜩∬ｳｪ邂｡逅・す繧ｹ繝・Β・・ails 繧｢繝励Μ・牙・讖溯・縺悟茜逕ｨ荳榊庄縲・|
| **逋ｺ逕溽ｵ檎ｷｯ** | INC-001・・ 繝峨Λ繧､繝匁椡貂・ｼ峨↓繧医ｊ Docker Desktop 縺悟●豁｢縲ょｾｩ譌ｧ縺ｮ縺溘ａ Docker 繧貞・襍ｷ蜍輔＠縲～docker-compose.production.yml` 縺ｧ IATF 繧ｹ繧ｿ繝・け繧貞・讒区・縲ゅさ繝ｳ繝・リ閾ｪ菴薙・襍ｷ蜍輔＠縺溘′縲ヽails 縺・DB 縺ｫ謗･邯壹〒縺阪★ 500 繧ｨ繝ｩ繝ｼ縺ｨ縺ｪ縺｣縺溘・|
| **譬ｹ譛ｬ蜴溷屏・・Why・・* | **Why1**: Rails 縺・DB 縺ｫ謗･邯壹〒縺阪↑縺・竊・**Why2**: `host.docker.internal:5432` 縺ｫ謗･邯壹＠繧医≧縺ｨ縺励※縺・ｋ 竊・**Why3**: `database.yml` 縺・`DB_PORT` 迺ｰ蠅・､画焚・医ョ繝輔か繝ｫ繝・5432・峨ｒ菴ｿ逕ｨ 竊・**Why4**: `docker-compose.production.yml` 縺ｮ `web` 繧ｵ繝ｼ繝薙せ縺ｫ `DB_PORT` 縺梧悴螳夂ｾｩ 竊・**Why5**: DB 繧ｳ繝ｳ繝・リ縺ｮ繝昴・繝医・繝・ヴ繝ｳ繧ｰ縺・`5436:5432`・医・繧ｹ繝亥・ 5436・峨↑縺ｮ縺ｫ縲ヽails 縺ｯ繝・ヵ繧ｩ繝ｫ繝医・ 5432 縺ｧ謗･邯壹ｒ隧ｦ陦後・*繝昴・繝医・繝・ヴ繝ｳ繧ｰ縺ｨ迺ｰ蠅・､画焚縺ｮ荳肴紛蜷医・* |
| **菫ｮ豁｣蜀・ｮｹ** | `docker-compose.production.yml` 縺ｮ `web` 縺翫ｈ縺ｳ `sidekiq` 繧ｵ繝ｼ繝薙せ縺ｮ `environment` 縺ｫ `DB_PORT=5436` 繧定ｿｽ蜉�縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | [docker-compose.production.yml](file:///d:/Clawdbot_Docker_20260125/iatf_system/docker-compose.production.yml) L66, L99 |
| **讀懆ｨｼ邨先棡** | 菫ｮ豁｣蠕・`curl` 縺ｧ HTTP 200 繧堤｢ｺ隱阪ゅヶ繝ｩ繧ｦ繧ｶ縺ｧ繝ｭ繧ｰ繧､繝ｳ繝壹・繧ｸ縺梧ｭ｣蟶ｸ陦ｨ遉ｺ・医梧磁邯壹ユ繧ｹ繝・ 騾夂衍繧ｷ繧ｹ繝・Β縺梧ｭ｣蟶ｸ縺ｫ蜍穂ｽ懊＠縺ｦ縺・∪縺吶阪・邱代ヰ繝翫・陦ｨ遉ｺ・峨・|
| **蜀咲匱髦ｲ豁｢** | 荳玖ｨ倥梧蕗險薙榊盾辣ｧ縲・|

### 謨呵ｨ難ｼ・essons Learned・・
1. **`docker-compose.yml` 縺ｧ繝帙せ繝育ｵ檎罰・・host.docker.internal`・峨・DB謗･邯壹ｒ菴ｿ縺・�ｴ蜷医√・繝ｼ繝医・繝・ヴ繝ｳ繧ｰ・・5436:5432`・峨・繝帙せ繝亥・繝昴・繝医ｒ `DB_PORT` 迺ｰ蠅・､画焚縺ｫ譏守､ｺ縺吶ｋ縺薙→縲・* 繝・ヵ繧ｩ繝ｫ繝亥､・・432・峨・繧ｳ繝ｳ繝・リ蜀・Κ縺ｮ繝昴・繝医〒縺ゅｊ縲√・繧ｹ繝育ｵ檎罰縺ｧ縺ｯ荳閾ｴ縺励↑縺・・2. **Docker 蜀崎ｵｷ蜍募ｾ後・縲√さ繝ｳ繝・リ縺ｮ襍ｷ蜍暮�・ｺ上↓豕ｨ諢上☆繧九・* DB 縺ｮ縲罫eady to accept connections縲阪Ο繧ｰ繧堤｢ｺ隱阪＠縺ｦ縺九ｉ Web 繧定ｵｷ蜍輔＠縺ｪ縺・→縲ヽails 縺・DB 襍ｷ蜍穂ｸｭ・・database system is starting up"・峨↓謗･邯壹ｒ隧ｦ縺ｿ縲√◎縺ｮ縺ｾ縺ｾ謗･邯壹・繝ｼ繝ｫ縺悟｣翫ｌ縺溽憾諷九〒蜍輔″邯壹￠繧九・3. **蠕ｩ譌ｧ菴懈･ｭ譎ゅ・ `docker compose logs --tail N <service>` 縺ｧ繧ｨ繝ｩ繝ｼ縺ｮ蜈ｨ譁・ｒ遒ｺ隱阪☆繧九％縺ｨ縲・* 莉雁屓縺ｯ縲継ort 5432縲阪∈縺ｮ謗･邯壼､ｱ謨励Ο繧ｰ縺悟・縺ｦ縺・◆縺後√ち繝ｼ繝溘リ繝ｫ縺ｮ蜃ｺ蜉帙ヨ繝ｩ繝ｳ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ縺ｧ隕玖誠縺ｨ縺励′逋ｺ逕溘＠縺溘・
---

## INC-003: Gateway 繝輔Μ繝ｼ繧ｺ縲＾bsidian 騾｣謳ｺ繧ｿ繧､繝�繧｢繧ｦ繝・
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-10 |
| **逋ｺ隕区婿豕・* | Obsidian Claudian 繝励Λ繧ｰ繧､繝ｳ縺ｫ縺ｦ `Request timeout: initialize (120000ms)` 繧ｨ繝ｩ繝ｼ縲・|
| **蠖ｱ髻ｿ遽・峇** | OpenClaw Gateway 蜈ｨ菴難ｼ・I, API, MCP 騾｣謳ｺ荳榊庄・・|
| **逋ｺ逕溽ｵ檎ｷｯ** | 蜑肴律・・4-09・峨・繝ｭ繧ｰ繧呈怙蠕後↓ gateway 縺ｮ譖ｴ譁ｰ縺悟●豁｢縲Ａcurl` 縺ｫ繧医ｋ繝倥Ν繧ｹ繝√ぉ繝・け繧ょｿ懃ｭ斐＠縺ｪ縺上↑縺｣縺溘・|
| **譬ｹ譛ｬ蜴溷屏・域耳貂ｬ・・* | 蟄舌・繝ｭ繧ｻ繧ｹ・・ummary cache builder・峨′ defunct 縺ｨ縺ｪ繧翫√Γ繧､繝ｳ縺ｮ gateway 繝励Ο繧ｻ繧ｹ縺ｮ繧､繝吶Φ繝医Ν繝ｼ繝励′繝・ャ繝峨Ο繝・け縺ｾ縺溘・繝悶Ο繝・く繝ｳ繧ｰ迥ｶ諷九↓髯･縺｣縺溷庄閭ｽ諤ｧ縲ゅΜ繧ｽ繝ｼ繧ｹ・・PU/MEM/DISK・峨・騾ｼ霑ｫ縺ｯ隕九ｉ繧後↑縺・・|
| **菫ｮ豁｣蜀・ｮｹ** | `docker restart clawstack-unified-clawdbot-gateway-1` 縺ｫ繧医ｋ蠑ｷ蛻ｶ蜀崎ｵｷ蜍輔・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | N/A (驕狗畑謫堺ｽ懊↓繧医ｋ蠕ｩ譌ｧ) |
| **讀懆ｨｼ邨先棡** | 蜀崎ｵｷ蜍募ｾ後√Ο繧ｰ縺・`2026-04-10.log` 縺ｫ豁｣蟶ｸ逕滓・縺輔ｌ縲～ws://0.0.0.0:18789` 縺ｧ縺ｮ蠕・女繧堤｢ｺ隱阪・|
| **蜀咲匱髦ｲ豁｢** | (1) Gateway 縺ｮ繝倥Ν繧ｹ繝√ぉ繝・け・・iveness Probe・峨ｒ Docker Compose 蛛ｴ縺ｾ縺溘・逶｣隕悶せ繧ｯ繝ｪ繝励ヨ縺ｫ讀懆ｨ弱・2) defunct 繝励Ο繧ｻ繧ｹ縺ｮ逋ｺ逕溘ｒ髦ｲ縺舌◆繧√∝ｭ舌・繝ｭ繧ｻ繧ｹ縺ｮ繝上Φ繝峨Μ繝ｳ繧ｰ蜃ｦ逅・ｒ隕狗峩縺吶・|

### 謨呵ｨ難ｼ・essons Learned・・
1. **繧ｳ繝ｳ繝・リ縺・`Up` 縺ｧ繧ゅい繝励Μ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ螻､縺後ヵ繝ｪ繝ｼ繧ｺ縺励※縺・ｋ蝣ｴ蜷医′縺ゅｋ縲・* `docker ps` 縺�縺代〒縺ｯ荳榊香蛻・〒縲√Ο繧ｰ縺ｮ譖ｴ譁ｰ譌･譎ゅｄ API 縺ｮ蠢懃ｭ皮｢ｺ隱阪′蠢・ｦ√・2. **defunct 繝励Ο繧ｻ繧ｹ・医だ繝ｳ繝難ｼ峨・逋ｺ逕溘・逡ｰ蟶ｸ縺ｮ蜈・吶・* 蟄舌・繝ｭ繧ｻ繧ｹ繧・fork 縺吶ｋ險ｭ險医・蝣ｴ蜷医√す繧ｰ繝翫Ν繝上Φ繝峨Μ繝ｳ繧ｰ繧・waitpid 遲峨・驕ｩ蛻・↑蠕悟・逅・′谺�縺代ｋ縺ｨ繧ｾ繝ｳ繝薙′闢・ｩ阪＠縲∬ｦｪ繝励Ο繧ｻ繧ｹ縺ｫ蠖ｱ髻ｿ繧貞所縺ｼ縺吶％縺ｨ縺後≠繧九・3. **縲景nitialize縲阪ち繧､繝�繧｢繧ｦ繝医・ MCP/LSP 繝上Φ繝峨す繧ｧ繧､繧ｯ螟ｱ謨励ｒ遉ｺ縺吶・* 繧ｯ繝ｩ繧､繧｢繝ｳ繝亥・・・bsidian・峨・繧ｨ繝ｩ繝ｼ繝｡繝・そ繝ｼ繧ｸ縺九ｉ縲√←縺ｮ繝励Ο繝医さ繝ｫ縺ｮ縺ｩ縺ｮ谿ｵ髫弱〒豁｢縺ｾ縺｣縺ｦ縺・ｋ縺九ｒ謗ｨ貂ｬ縺ｧ縺阪ｋ縲・
---

## INC-004: 繧ｾ繝ｳ繝薙・繝ｭ繧ｻ繧ｹ闢・ｩ阪→ Paperless 逡ｰ蟶ｸ縺ｫ繧医ｋ Gateway 騾｣邯壼●豁｢

| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-10 |
| **逋ｺ隕区婿豕・* | Obsidian Claudian 蜀榊ｺｦ縺ｮ `Request timeout: initialize`縲ょ・襍ｷ蜍輔°繧・譎る俣蠕後↓蜀咲匱縲・|
| **蠖ｱ髻ｿ遽・峇** | Gateway, LiteLLM, Paperless 騾｣謳ｺ蜈ｨ菴・|
| **逋ｺ逕溽ｵ檎ｷｯ** | INC-003 縺ｧ縺ｮ蜊倥↑繧・`docker restart` 縺ｧ縺ｯ譬ｹ譛ｬ蜴溷屏縺瑚ｧ｣豸医＆繧後★縲∵焚譎る俣蠕後↓蜀咲匱縲・ateway 蛛ｴ縺ｧ縺ｮ繧ｾ繝ｳ繝薙・繝ｭ繧ｻ繧ｹ闢・ｩ阪√♀繧医・螟夜Κ E: 繝峨Λ繧､繝紋ｸ翫・ Paperless 繝・ぅ繝ｬ繧ｯ繝医Μ豸亥､ｱ縺ｫ繧医ｋ Liveness Probe 螟ｱ謨励′驥阪↑繧翫√す繧ｹ繝・Β縺後ワ繝ｳ繧ｰ縺励◆縲・|
| **譬ｹ譛ｬ蜴溷屏** | (1) `docker-compose.yml` 縺ｧ `init: true` 縺梧悴險ｭ螳壹・縺溘ａ縲∝ｭ､遶九＠縺溷ｭ舌・繝ｭ繧ｻ繧ｹ縺・PID 1 (OpenClaw) 縺ｫ蝗槫庶縺輔ｌ縺壽ｻ樒蕗縲・2) Paperless 縺ｮ繝槭え繝ｳ繝亥・・・: 繝峨Λ繧､繝・Junction・峨↓繝・ぅ繝ｬ繧ｯ繝医Μ縺悟ｭ伜惠縺帙★縲￣aperless 縺瑚ｵｷ蜍輔お繝ｩ繝ｼ・・ileExistsError・峨〒蛛懈ｭ｢縲・3) `ingest_watchdog.py` 縺檎焚蟶ｸ迥ｶ諷九・ Paperless 縺ｫ蟇ｾ縺励Μ繝医Λ繧､繧堤ｹｰ繧願ｿ斐＠縲√Μ繧ｽ繝ｼ繧ｹ縺ｾ縺溘・繝励Ο繧ｻ繧ｹ蛻ｶ蠕｡縺ｫ蠖ｱ髻ｿ縲・|
| **菫ｮ豁｣蜀・ｮｹ** | (1) `docker-compose.yml` 縺ｫ `init: true` 繧定ｿｽ蜉�縲・2) E: 繝峨Λ繧､繝紋ｸ翫・ Paperless 讒矩�繧貞ｾｩ譌ｧ縲・3) `ingest_watchdog.py` 縺ｫ謖・焚繝舌ャ繧ｯ繧ｪ繝包ｼ・xponential Backoff・峨ｒ螳溯｣・・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | [docker-compose.yml](file:///d:/Clawdbot_Docker_20260125/docker-compose.yml), [ingest_watchdog.py](file:///d:/Clawdbot_Docker_20260125/data/workspace/ingest_watchdog.py) |
| **讀懆ｨｼ邨先棡** | Gateway 縺ｮ PID 1 縺・`docker-init` 縺ｫ縺ｪ縺｣縺ｦ縺・ｋ縺薙→繧堤｢ｺ隱阪１aperless 縺ｮ Healthy 蛻ｰ驕斐♀繧医・ Watchdog 縺ｮ豁｣蟶ｸ繝昴・繝ｪ繝ｳ繧ｰ繧堤｢ｺ隱阪・|
| **蜀咲匱髦ｲ豁｢** | (1) 蜈ｨ縺ｦ縺ｮ髟ｷ譛溷ｮ溯｡後さ繝ｳ繝・リ縺ｧ `init: true` 縺ｾ縺溘・ `tini` 縺ｮ菴ｿ逕ｨ繧呈､懆ｨ弱・2) 繝帙せ繝亥・縺ｮ Junction 蜈茨ｼ亥､紋ｻ倥￠繝峨Λ繧､繝厄ｼ峨・豁ｻ豢ｻ逶｣隕悶∪縺溘・襍ｷ蜍募燕繝√ぉ繝・け繧貞ｼｷ蛹悶・|

### 謨呵ｨ難ｼ・essons Learned・・
1. **PID 1 蝠城｡後・驥崎ｦ∵ｧ**・哢ode.js 遲峨・繝ｩ繝ｳ繧ｿ繧､繝�繧堤峩謗･ PID 1 縺ｧ蜍輔°縺吶→縲√だ繝ｳ繝薙・繝ｭ繧ｻ繧ｹ縺ｮ蝗槫庶縺後お繝ｳ繧ｸ繝ｳ縺ｮ螳溯｣・↓萓晏ｭ倥＠縲∵э蝗ｳ縺励↑縺・ワ繝ｳ繧ｰ繧呈魚縺上Ａinit: true` 縺ｮ蛻ｩ逕ｨ縺碁延蜑・・2. **螟夜Κ繝峨Λ繧､繝夜｣謳ｺ縺ｮ繝ｪ繧ｹ繧ｯ**・哽unction 繧剃ｽｿ逕ｨ縺励◆螟夜Κ繝槭え繝ｳ繝医・縲√ラ繝ｩ繧､繝悶・蛻・妙繧・ｧ矩�螟画峩縺ｫ蠑ｱ縺・りｵｷ蜍墓凾縺ｫ繝・ぅ繝ｬ繧ｯ繝医Μ縺ｮ蟄伜惠繝√ぉ繝・け繧定｡後≧遲峨・亟蠕｡逧・ｮ溯｣・′蠢・ｦ√・3. **繝舌ャ繧ｯ繧ｪ繝輔・谺�螯ゅ↓繧医ｋ莠梧ｬ｡陲ｫ螳ｳ**・壻ｾ晏ｭ倥し繝ｼ繝薙せ縺梧ｭｻ繧薙〒縺・ｋ髫帙↓縲√・繝ｼ繝ｪ繝ｳ繧ｰ蛛ｴ縺悟・蜉帙〒繝ｪ繝医Λ繧､繧堤ｶ壹￠繧九→縲∵ｭ｣蟶ｸ縺ｪ繧ｳ繝ｳ繝・リ縺ｾ縺ｧ雋�闕ｷ繧・Ο繧ｰ縺ｮ蠅怜､ｧ縺ｧ驕馴｣繧後↓縺ｪ繧句庄閭ｽ諤ｧ縺後≠繧九・
---

*谺｡縺ｮ繧､繝ｳ繧ｷ繝・Φ繝医・ INC-005 縺ｨ縺励※霑ｽ險倥＠縺ｦ縺上□縺輔＞縲・

---

## INC-005: Claudian Codex 襍ｷ蜍募､ｱ謨励→ initialize 繧ｿ繝ｼ繧ｲ繝・ヨ荳堺ｸ閾ｴ
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | Obsidian Claudian 縺ｧ `Request timeout: initialize (120000ms)` 縺ｮ蠕後～Codex target mismatch` 縺碁｣骼悶・|
| **蠖ｱ髻ｿ遽・峇** | `data/state/Obsidian Vault/.obsidian/plugins/claudian` 驟堺ｸ九・ Codex 騾｣謳ｺ縲７ault 蜀・°繧・Codex 繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ蛻晄悄蛹悶′螟ｱ謨励・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Codex 繝励Ο繧ｻ繧ｹ縺瑚ｵｷ蜍輔○縺・initialize 縺・120 遘偵〒繧ｿ繧､繝�繧｢繧ｦ繝医＠縺溘・**Why2**: Windows 閾ｪ蜍戊ｧ｣豎ｺ縺・`codex.cmd` / `codex.bat` 繧呈爾邏｢蟇ｾ雎｡縺ｫ蜷ｫ繧√※縺・↑縺九▲縺溘・**Why3**: Vault 繝励Λ繧ｰ繧､繝ｳ驟堺ｸ九↓縺ｯ `codex.cmd` 繝ｩ繝・ヱ繝ｼ縺後≠繧翫￣ATH 縺ｫ縺ｯ蟄伜惠縺励※縺・◆縺瑚ｧ｣豎ｺ縺ｧ縺阪↑縺九▲縺溘・**Why4**: 縺溘→縺・`.cmd` 繧定ｦ九▽縺代※繧ゅ仝indows 縺ｧ縺ｯ `spawn(..., { shell: false })` 縺ｮ縺ｾ縺ｾ縺ｧ縺ｯ襍ｷ蜍穂ｺ呈鋤諤ｧ縺悟ｼｱ縺・・**Why5**: 襍ｷ蜍募ｾ後ｂ `codex_bridge.js` 縺ｮ initialize 蠢懃ｭ斐↓ `platformOs` / `platformFamily` 縺後↑縺上√ち繝ｼ繧ｲ繝・ヨ讀懆ｨｼ縺ｧ蛻･繧ｨ繝ｩ繝ｼ縺ｫ縺ｪ縺｣縺ｦ縺・◆縲・|
| **菫ｮ豁｣蜀・ｮｹ** | Windows 縺ｮ CLI 謗｢邏｢縺ｫ `codex.cmd` / `codex.bat` 繧定ｿｽ蜉�縺励～.cmd` / `.bat` 縺瑚ｧ｣豎ｺ縺輔ｌ縺溷�ｴ蜷医・ sibling 縺ｮ `codex_bridge.js` 繧・`node` 縺ｧ逶ｴ謗･襍ｷ蜍輔☆繧九ｈ縺・ｿｮ豁｣縲ゅ＆繧峨↓ bridge initialize 蠢懃ｭ斐∈ `platformOs=windows` 縺ｨ `platformFamily=windows` 繧定ｿｽ蜉�縺励√Ο繧ｰ繝・ぅ繝ｬ繧ｯ繝医Μ繧定・蜍穂ｽ懈・縺吶ｋ繧医≧菫ｮ豁｣縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:60884`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:60905`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:61858`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js:11`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js:37` |
| **讀懆ｨｼ邨先棡** | 繧ｽ繝ｼ繧ｹ遒ｺ隱阪〒 Windows 謗｢邏｢蟇ｾ雎｡縺ｫ `.cmd` / `.bat` 縺瑚ｿｽ蜉�縺輔ｌ縺溘％縺ｨ縲～.cmd` 隗｣豎ｺ譎ゅ↓ `node + codex_bridge.js` 縺ｮ逶ｴ謗･襍ｷ蜍輔∈蛻・ｊ譖ｿ繧上ｋ縺薙→縲｜ridge initialize 蠢懃ｭ斐↓ target 諠・�ｱ縺瑚ｼ峨ｋ縺薙→繧堤｢ｺ隱阪ょ刈縺医※ `codex_bridge.js` 蜊倅ｽ薙・ initialize 蠢懃ｭ斐ユ繧ｹ繝医〒 `platformOs` / `platformFamily` 繧定ｿ斐☆縺薙→繧堤｢ｺ隱阪・|
| **蜀咲匱髦ｲ豁｢遲・* | Windows 蝗ｺ譛峨・螳溯｡悟ｽ｢蠑・(`.cmd` / `.bat`) 繧・CLI 閾ｪ蜍戊ｧ｣豎ｺ縺九ｉ螟悶＆縺ｪ縺・Ｊnitialize 蠢懃ｭ斐・蠢・�医ヵ繧｣繝ｼ繝ｫ繝峨ｒ谺�縺九＆縺ｪ縺・ｈ縺・｜ridge 螟画峩譎ゅ・襍ｷ蜍募燕縺ｮ JSON-RPC 繧ｹ繝｢繝ｼ繧ｯ繝・せ繝医ｒ邯ｭ謖√☆繧九・|

### Lessons Learned
1. Windows 邵ｺ・ｧ邵ｺ・ｯ邵ｲ險鄭TH 邵ｺ・ｫ邵ｺ繧・ｽ狗ｸｲ髦ｪ笆｡邵ｺ莉｣縲堤ｸｺ・ｯ闕ｳ讎企ｦ呵崕繝ｻ縲堤ｸｲ・枹pawn` 邵ｺ・ｮ陞ｳ貅ｯ・｡謔滂ｽｽ・｢陟台ｸ橸ｽｷ・ｮ邵ｺ・ｾ邵ｺ・ｧ髫穂ｹ晢ｽ玖�｢繝ｻ・ｦ竏壺ｲ邵ｺ繧・ｽ狗ｸｲ繝ｻ2. `initialize` 邵ｺ・ｯ郢ｧ・ｿ郢ｧ・､郢晢｣ｰ郢ｧ・｢郢ｧ・ｦ郢晏現笆｡邵ｺ莉｣縲堤ｸｺ・ｪ邵ｺ荳環竏晢ｽｿ諛・ｽｭ譁舌○郢ｧ・ｭ郢晢ｽｼ郢晄ｨ費ｽｸ讎奇ｽ咏ｸｺ・ｧ郢ｧ繧・ｽｺ譴ｧ・ｮ・ｵ騾ｶ・ｮ邵ｺ・ｮ鬮ｫ諛ｷ・ｮ・ｳ郢ｧ螳夲ｽｵ・ｷ邵ｺ阮吮・邵ｺ貅假ｽ∫ｸｲ竏ｬ・ｵ・ｷ陷崎ｼ披・陟｢諛・ｽｭ譁舌・闕ｳ・｡隴・ｽｹ郢ｧ雋樣・隴弱ｅ竊楢ｮ諛・ｽｨ・ｼ邵ｺ蜷ｶ・狗ｸｲ繝ｻ3. 隴鯉ｽ｢陝・･ﾎ帷ｹ昴・繝ｱ郢晢ｽｼ (`codex.cmd`) 郢ｧ蜻茨ｽｴ・ｻ邵ｺ荵昶・隲｡・｡陟托ｽｵ邵ｺ・ｮ隴・ｽｹ邵ｺ蠕個竏晄肩驍会ｽｻ驍ｨ・ｱ邵ｺ・ｮ隘搾ｽｷ陷肴・・ｵ迹夲ｽｷ・ｯ郢ｧ雋橸ｽ｢蜉ｱ・・ｸｺ蜷ｶ・育ｹｧ髮・ｽｮ迚吶・邵ｺ・ｫ陝・ｸｻ繝ｻ邵ｺ・ｧ邵ｺ髦ｪ・狗ｸｲ繝ｻ

## INC-017: `email_search.db` 遐ｴ謳肴凾縺ｮ閾ｪ蜍穂ｿｮ蠕ｩ邨瑚ｷｯ繧定ｿｽ蜉�
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-12 |
| **逋ｺ隕区婿豕・* | `email_continuous_watchdog_status.json` 縺ｨ `email_continuous_ingest_status.json` 縺ｧ `temp integrity_check failed` / `database disk image is malformed` 繧堤｢ｺ隱・|
| **蠖ｱ髻ｿ遽・峇** | Gmail incremental ingest 縺悟､ｱ謨励Ν繝ｼ繝励↓蜈･繧翫『atchdog 縺・daemon 繧貞・襍ｷ蜍輔＠縺ｦ繧ょ屓蠕ｩ縺励↑縺・憾諷・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: `email_search.db` 縺ｫ freelist 荳肴紛蜷医′蜈･繧・`PRAGMA integrity_check` 縺悟､ｱ謨励＠縺溘・**Why2**: `host_gmail_incremental_sync.py` 縺ｯ temp DB 縺ｮ讀懈渊縺ｧ逡ｰ蟶ｸ繧呈､懃衍縺励※繧ゅ‥aemon 蛛ｴ縺ｫ菫ｮ蠕ｩ蛻・ｲ舌′縺ｪ縺九▲縺溘・**Why3**: `continuous_email_ingest_daemon.py` 縺ｯ螟ｱ謨玲凾縺ｫ `error` 繧呈嶌縺・※蠕・ｩ溘☆繧九□縺代〒縲∫�ｴ謳阪す繧ｰ繝翫Ν縺ｨ荳闊ｬ繧ｨ繝ｩ繝ｼ繧貞玄蛻･縺励※縺・↑縺九▲縺溘・**Why4**: 譌｢蟄倥・ `repair_email_search_db.py` 縺ｯ縺ゅ▲縺溘′縲‥aemon 蜀・°繧牙ｮ牙・縺ｫ蜻ｼ縺ｶ驟咲ｷ壹′縺ｪ縺九▲縺溘・**Why5**: watchdog 繧・`db repair` 繧帝壼ｸｸ繧ｨ繝ｩ繝ｼ縺ｨ蛹ｺ蛻･縺励↑縺・燕謠舌〒縲∽ｿｮ蠕ｩ荳ｭ縺ｮ菫晁ｭｷ縺御ｸ崎ｶｳ縺励※縺・◆縲・|
| **菫ｮ豁｣蜀・ｮｹ** | `data/workspace/continuous_email_ingest_daemon.py` 縺ｫ DB 遐ｴ謳阪す繧ｰ繝翫Ν讀懃衍縲∽ｿｮ蠕ｩ蜻ｼ縺ｳ蜃ｺ縺励〉epair cooldown縲〉epair 迥ｶ諷倶ｿ晏ｭ倥ｒ霑ｽ蜉�縲・`data/workspace/repair_email_search_db.py` 縺ｫ `--skip-stop-processes` 繧定ｿｽ蜉�縺励‥aemon 縺九ｉ螳牙・縺ｫ inline 螳溯｡後〒縺阪ｋ繧医≧縺ｫ縺励◆縲・`data/workspace/email_continuous_watchdog.py` 縺ｧ `stage == "db_repair"` 繧貞▼蜈ｨ謇ｱ縺・↓縺励※縲∽ｿｮ蠕ｩ荳ｭ縺ｮ辟｡鬧・↑蜀崎ｵｷ蜍輔ｒ髦ｲ豁｢縲・縺昴・蠕・`python data/workspace/repair_email_search_db.py --restart-watchdog` 繧貞ｮ溯｡後＠縺ｦ螳・DB 繧剃ｿｮ蠕ｩ縲・|
| **讀懆ｨｼ邨先棡** | 菫ｮ蠕ｩ邨先棡 `email_search_db_repair_status.json` 縺ｯ `stage=completed`縲・蠕ｩ譌ｧ蠕後・ DB 縺ｯ `integrity_check=ok`, `quick_check=ok`, `emails=22688`, `tasks=9065` 繧堤｢ｺ隱阪・watchdog 縺ｯ PID `10428`縲‥aemon 縺ｯ PID `11748` 縺ｧ蜀崎ｵｷ蜍墓ｸ医∩縲・|
| **Lessons Learned** | 菫ｮ蠕ｩ繧ｹ繧ｯ繝ｪ繝励ヨ縺悟ｭ伜惠縺励※縺・※繧ゅ∫焚蟶ｸ蛻・｡槭→蜻ｼ縺ｳ蜃ｺ縺礼ｵ瑚ｷｯ縺檎┌縺代ｌ縺ｰ迴ｾ蝣ｴ縺ｧ縺ｯ蝗槫ｾｩ縺励↑縺・・遐ｴ謳咲ｳｻ縺ｯ荳闊ｬ螟ｱ謨励→蛻・￠縲《tatus JSON 縺ｨ watchdog 縺ｮ荳｡譁ｹ縺ｧ蟆ら畑迥ｶ諷九ｒ謖√▽縺ｹ縺阪・|
| **蜀咲匱髦ｲ豁｢遲・* | daemon 蛛ｴ縺ｧ DB 遐ｴ謳阪ｒ讀懃衍縺励◆繧芽・蜍穂ｿｮ蠕ｩ縺ｸ蛻・ｲ舌☆繧九・watchdog 縺ｯ `db_repair` 繧貞・襍ｷ蜍募ｯｾ雎｡縺九ｉ螟悶☆縲・莉･蠕後・ DB 遐ｴ謳阪・ backup 縺ｨ repair status 繧呈ｮ九＠縺ｪ縺後ｉ蝗槫ｾｩ繧定ｩｦ縺ｿ繧九・|

## INC-018: mini PC 蟶ｸ鬧舌ワ繝ｼ繝阪せ縺ｮ譛ｪ謗･邯壹→隱､隴ｦ蝣ｱ繧呈紛逅・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-12 |
| **逋ｺ隕区婿豕・* | system hardening 轤ｹ讀懊〒縲～docker_desktop_ui_watchdog` 縺・observe-only縲～claudian_watchdog` 縺梧悴蟶ｸ鬧舌～minipc_optimizer` 縺ｫ閾ｪ蜍募・蜿｣縺檎┌縺・～n8n` API 繧ｭ繝ｼ縺後せ繧ｯ繝ｪ繝励ヨ縺ｸ逶ｴ譖ｸ縺阪～continuous_system_improvement` 縺御ｸ驛ｨ繧定ｪ､縺｣縺ｦ high risk 謇ｱ縺・＠縺ｦ縺・ｋ縺薙→繧堤｢ｺ隱・|
| **蠖ｱ髻ｿ遽・峇** | Docker UI 荳崎ｪｿ譎ゅ↓閾ｪ蜍募屓蠕ｩ縺励↑縺・，laudian/mini PC 霆ｽ驥丞喧縺ｮ逶｣隕悶′蛻・ｌ縺ｦ繧よｰ励▼縺阪↓縺上＞縲《ystem summary 縺悟ｮ滄圀繧医ｊ蜊ｱ髯ｺ縺ｫ隕九∴繧九∫ｧ伜ｯ・ュ蝣ｱ縺ｮ繝ｭ繝ｼ繝・・繧ｷ繝ｧ繝ｳ縺碁屮縺励＞ |
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: watchdog 繧・optimizer 閾ｪ菴薙・蟄伜惠縺励※繧ゅ∝ｸｸ鬧占ｵｷ蜍輔ｄ逶ｸ莠定｣懷ｮ後・驟咲ｷ壹′荳崎ｶｳ縺励※縺・◆縲・**Why2**: Docker UI watchdog 縺ｯ `allowUiReset=false` 縺ｮ縺ｾ縺ｾ髟ｷ譎る俣 failure 繧堤ｩ阪ｓ縺ｧ縺・◆縲・**Why3**: Claudian watchdog 縺ｯ蜿､縺・Ο繧ｰ繧呈怙霑代・螟ｱ謨励→縺励※隗｣驥医＠縲・撕豁｢迥ｶ諷九〒繧・error 縺ｫ縺ｪ繧雁ｾ励◆縲・**Why4**: mini PC optimizer 縺ｯ謇句虚 CLI 縺ｮ縺ｿ縺ｧ縲∝ｸｸ鬧舌・逶｣隕門ｽｹ縺悟ｭ伜惠縺励↑縺九▲縺溘・**Why5**: n8n API 繧ｭ繝ｼ縺後せ繧ｯ繝ｪ繝励ヨ蜀・↓蝓九ａ霎ｼ縺ｾ繧後∬ｨｭ螳壼､画峩繧・・蛻ｩ逕ｨ譎ゅ↓繧ｳ繝ｼ繝臥ｷｨ髮・′蠢・ｦ√□縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `data/workspace/docker_desktop_ui_watchdog.py` 縺ｫ髟ｷ譛・failure 譎ゅ・蠑ｷ蛻ｶ reset 蛻・ｲ舌ｒ霑ｽ蜉�縺励～docker_desktop_ui_watchdog_config.json` 繧・`quietMode=true`, `allowUiReset=true`, `consecutiveFailuresForReset=12` 縺ｸ譖ｴ譁ｰ縲・`data/workspace/claudian_watchdog.py` 繧偵〉ecent activity 縺檎┌縺・商縺・bridge/spawn 繝ｭ繧ｰ縺ｧ縺ｯ error 繧貞・縺輔↑縺・ｈ縺・｣懷ｼｷ縲・`data/workspace/minipc_optimizer_watchdog.py` 縺ｨ `scripts/start_minipc_optimizer_watchdog.ps1` 繧定ｿｽ蜉�縺励∽ｽ弱Γ繝｢繝ｪ譎ゅ□縺・`apply-lite` 繧貞ｮ溯｡後☆繧玖ｻｽ驥・watchdog 繧呈眠險ｭ縲・`data/workspace/continuous_system_improvement.py` 縺ｨ `data/workspace/auto_repair_allowed.py` 繧呈峩譁ｰ縺励．ocker UI / Claudian / mini PC watchdog 縺ｮ蟶ｸ鬧千｢ｺ隱阪→蜀崎ｵｷ蜍輔ｒ霑ｽ蜉�縲・`data/workspace/add_ai_scout_safe_sources.py` 縺ｨ `scripts/setup_n8n_changedetection_flow.ps1` 縺ｯ `N8N_API_KEY` 繧・`.env` / 迺ｰ蠅・､画焚縺九ｉ隱ｭ繧譁ｹ蠑上∈螟画峩縲・|
| **讀懆ｨｼ邨先棡** | `docker_desktop_ui_watchdog.py`, `claudian_watchdog.py`, `minipc_optimizer_watchdog.py` 縺ｯ縺吶∋縺ｦ `py_compile` 謌仙粥縲・螳溘・繝ｭ繧ｻ繧ｹ縺ｨ縺励※ 3 譛ｬ縺ｮ watchdog 襍ｷ蜍輔ｒ遒ｺ隱阪・`claudian_watchdog.py --once` 縺ｯ `stage=healthy`縲・`minipc_optimizer_watchdog_status.json` 縺ｧ縺ｯ free memory `35.14GB`, `freePercent=73.6`, `stage=healthy` 繧堤｢ｺ隱阪・Docker UI watchdog 縺ｯ `lastAction=reset_frontend_cache` 縺ｾ縺ｧ騾ｲ縺ｿ縲∽ｻ･蠕後・ status 縺ｧ reset 縺梧怏蜉ｹ蛹悶＆繧後◆縺薙→繧堤｢ｺ隱阪・|
| **Lessons Learned** | 逶｣隕悶Ο繧ｸ繝・け縺ｯ縲悟ｭ伜惠縺吶ｋ縺薙→縲阪ｈ繧翫悟ｸｸ鬧舌＠邯壹￠繧九％縺ｨ縲阪→縲悟商縺・､ｱ謨励ｒ迴ｾ蝨ｨ縺ｮ髫懷ｮｳ縺ｨ縺励※謇ｱ繧上↑縺・％縺ｨ縲阪′驥崎ｦ√・菴手ｲ�闕ｷ遶ｯ譛ｫ縺ｧ縺ｯ縲∝ｸｸ鬧舌ヤ繝ｼ繝ｫ繧貞｢励ｄ縺吶ｈ繧翫ｂ霆ｽ驥・watchdog 縺ｧ谿ｵ髫主宛蠕｡縺吶ｋ譁ｹ縺悟ｮ牙・縲・|
| **蜀咲匱髦ｲ豁｢遲・* | system summary 縺ｨ auto repair 縺ｫ watchdog 蟶ｸ鬧舌メ繧ｧ繝・け繧呈ｮ九☆縲・Docker UI 縺ｯ observe-only 縺ｫ謌ｻ縺輔★谿ｵ髫・reset 繧堤ｶ咏ｶ壹☆繧九・遘伜ｯ・ュ蝣ｱ縺ｯ `.env` / 迺ｰ蠅・､画焚縺ｸ蟇・○縲√せ繧ｯ繝ｪ繝励ヨ逶ｴ譖ｸ縺阪ｒ蠅励ｄ縺輔↑縺・・|

---

## INC-013: Antigravity `Notify file events failed` 騾｣謇薙↓繧医ｋ IDE 繝輔Μ繝ｼ繧ｺ
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | Mini PC 縺悟壕蠕後°繧画妙邯夂噪縺ｫ繝輔Μ繝ｼ繧ｺ縺励ヽemote Desktop 荳翫〒 Antigravity 縺ｮ `Notify file events failed.` 縺梧焚遘偵＃縺ｨ縺ｫ蜃ｺ邯壹￠繧九％縺ｨ繧堤｢ｺ隱阪・|
| **蠖ｱ髻ｿ遽・峇** | Antigravity 邱ｨ髮・判髱｢縺ｮ謫堺ｽ懈ｧ菴惹ｸ九，PU 菴ｿ逕ｨ邇・ｸ頑・縲√Ο繧ｰ閧･螟ｧ蛹悶３emote Desktop 閾ｪ菴薙・謗･邯夂ｶｭ謖√＆繧後ｋ縺後！DE 縺ｮ蠢懃ｭ疲ｧ縺梧が蛹悶・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Antigravity 諡｡蠑ｵ繝帙せ繝医〒 `Notify file events failed.` 縺碁｣邯夂匱逕溘＠縺ｦ縺・◆縲・**Why2**: 蜷後§繝ｭ繧ｰ逶ｴ蜑阪↓ `Client is not running` 縺檎ｹｰ繧願ｿ斐＠蜃ｺ縺ｦ縺翫ｊ縲∬ｨ隱槭し繝ｼ繝舌・蜀崎ｵｷ蜍募ｾ後ｂ繝輔ぃ繧､繝ｫ逶｣隕夜夂衍縺�縺代′谿狗蕗縺励※縺・◆縲・**Why3**: 縺薙・繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ縺ｯ `data/workspace` 驟堺ｸ九↓ `node_modules`縲∬､・焚縺ｮ `venv`縲＾bsidian Vault縲∫函謌千黄縲√Ο繧ｰ縲》mp 繧貞､ｧ驥上↓謚ｱ縺医※縺翫ｊ縲∫屮隕門ｯｾ雎｡縺碁℃螟ｧ縺�縺｣縺溘・**Why4**: `.vscode/settings.json` 縺ｫ watcher 髯､螟悶ｄ讀懃ｴ｢髯､螟悶′縺ｪ縺上！DE 縺悟ｷｨ螟ｧ繝・ぅ繝ｬ繧ｯ繝医Μ鄒､繧偵◎縺ｮ縺ｾ縺ｾ逶｣隕悶＠縺ｦ縺・◆縲・**Why5**: 逶｣隕冶ｲ�闕ｷ縺ｮ鬮倥＞逕滓・迚ｩ縺ｨ螳滄圀縺ｫ邱ｨ髮・☆繧九さ繝ｼ繝蛾�伜沺縺ｮ蛻・屬繝昴Μ繧ｷ繝ｼ縺梧悴險ｭ螳壹〒縲∝・襍ｷ蜍墓凾縺ｫ蜷後§逶｣隕冶ｲ�闕ｷ縺悟・迴ｾ縺励※縺・◆縲・|
| **菫ｮ豁｣蜀・ｮｹ** | `.vscode/settings.json` 縺ｫ `files.watcherExclude`縲～search.exclude`縲～python.analysis.exclude` 繧定ｿｽ蜉�縺励～node_modules`縲∽ｻｮ諠ｳ迺ｰ蠅・＾bsidian Vault縲∫函謌千黄縲》mp縲√Ο繧ｰ邉ｻ繝・ぅ繝ｬ繧ｯ繝医Μ繧堤屮隕悶・讀懃ｴ｢蟇ｾ雎｡縺九ｉ髯､螟悶＠縺溘・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `.vscode/settings.json`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | Antigravity 繝ｭ繧ｰ縺ｧ `Notify file events failed.` 縺・`Client is not running` 逶ｴ蠕後°繧臥ｶ咏ｶ夂匱逕溘＠縺ｦ縺・ｋ縺薙→縲，PU 荳贋ｽ阪↓ Antigravity 譛ｬ菴薙→ `remoting_host` 縺御ｸｦ繧薙〒縺・ｋ縺薙→縲∫屮隕門ｯｾ雎｡縺ｫ蟾ｨ螟ｧ繝・ぅ繝ｬ繧ｯ繝医Μ縺悟性縺ｾ繧後※縺・ｋ縺薙→繧堤｢ｺ隱阪＠縺溘りｨｭ螳壼渚譏�蠕後・ Antigravity 縺ｮ `Developer: Reload Window` 縺ｾ縺溘・繧｢繝励Μ蜀崎ｵｷ蜍輔〒譁ｰ縺励＞ watcher 險ｭ螳壹′譛牙柑蛹悶＆繧後ｋ迥ｶ諷九↓縺励◆縲・|
| **Lessons Learned** | Remote Desktop 繧呈ｭ｢繧√ｉ繧後↑縺・憾豕√〒縺ｯ縲√∪縺・IDE 縺ｮ watcher 雋�闕ｷ繧貞・繧企屬縺呎婿縺悟ｮ牙・縺ｧ蜉ｹ譫懊′鬮倥＞縲ょｷｨ螟ｧ縺ｪ逕滓・迚ｩ繧・Vault 繧貞酔荳繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ縺ｧ髢九￥蝣ｴ蜷医∵､懃ｴ｢髯､螟悶□縺代〒縺ｪ縺・watcher 髯､螟悶ｂ譛蛻昴°繧牙・繧後※縺翫￥蠢・ｦ√′縺ゅｋ縲・|
| **蜀咲匱髦ｲ豁｢遲・* | 譁ｰ縺励＞螟ｧ螳ｹ驥上ョ繧｣繝ｬ繧ｯ繝医Μ繧偵％縺ｮ repo 驟堺ｸ九∈霑ｽ蜉�縺吶ｋ髫帙・縲～.vscode/settings.json` 縺ｮ watcher 髯､螟悶↓蜷梧凾霑ｽ蜉�縺吶ｋ縲・DE 繝輔Μ繝ｼ繧ｺ邉ｻ縺ｮ髫懷ｮｳ縺ｧ縺ｯ縲～logs/.../7-antigravity.log` 縺ｮ `Client is not running` 縺ｨ `Notify file events failed.` 縺ｮ邨・∩蜷医ｏ縺帙ｒ蛻晏虚遒ｺ隱埼�・岼縺ｫ縺吶ｋ縲・|

## INC-014: Antigravity 縺ｮ R 諡｡蠑ｵ縺・`cmd.exe` 繝昴ャ繝励い繝・・繧帝｣邯夊ｵｷ蜍・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-12 |
| **逋ｺ隕区婿豕・* | Antigravity 蠕ｩ譌ｧ蠕後ｂ `CMD` 繧ｦ繧｣繝ｳ繝峨え縺梧焚遘偵＃縺ｨ縺ｫ髢九＞縺ｦ髢峨§繧九％縺ｨ繧堤｢ｺ隱阪ょｮ溯｡御ｸｭ繝励Ο繧ｻ繧ｹ縺ｮ隕ｪ蟄宣未菫ゅ→繧ｳ繝槭Φ繝峨Λ繧､繝ｳ繧定ｪｿ譟ｻ縺励◆縲・|
| **蠖ｱ髻ｿ遽・峇** | Mini PC 謫堺ｽ懈ｧ菴惹ｸ九∫判髱｢縺ｮ縺｡繧峨▽縺阪、ntigravity 蛻ｩ逕ｨ荳ｭ縺ｮ髮・ｸｭ髦ｻ螳ｳ縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: `cmd.exe` 縺悟捉譛溽噪縺ｫ襍ｷ蜍輔＠縺ｦ縺・◆縲・**Why2**: 繧ｳ繝槭Φ繝峨Λ繧､繝ｳ縺ｯ `cmd.exe /c ... Rterm.exe ... helpServer.R` 縺ｨ `languageServer.R` 縺ｧ縲、ntigravity 縺ｮ R 諡｡蠑ｵ縺瑚ｵｷ轤ｹ縺�縺｣縺溘・**Why3**: 繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ蜀・・ R 髢｢騾｣繝輔ぃ繧､繝ｫ讀懃衍縺ｧ R 諡｡蠑ｵ縺・activation 縺輔ｌ縲∬ｨ隱槭し繝ｼ繝舌→ help server 繧定・蜍戊ｵｷ蜍輔＠縺ｦ縺・◆縲・**Why4**: 縺薙・ repo 縺ｧ縺ｯ R 繧剃ｸｻ隕∫畑騾斐→縺励※菴ｿ縺｣縺ｦ縺・↑縺・ｸ譁ｹ縲～.vscode/settings.json` 縺ｫ縺ｯ `r.rpath.windows` 縺ｮ縺ｿ縺後≠繧翫∬・蜍戊ｵｷ蜍輔ｒ謚代∴繧玖ｨｭ螳壹′縺ｪ縺九▲縺溘・**Why5**: 髱樔ｽｿ逕ｨ諡｡蠑ｵ縺ｮ閾ｪ蜍墓ｩ溯・繧偵Ρ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ蜊倅ｽ阪〒邨槭ｋ驕狗畑縺梧悴謨ｴ蛯吶〒縲∽ｸ崎ｦ√↑陬懷勧繝励Ο繧ｻ繧ｹ縺悟ｸｸ譎りｵｷ蜍輔＠縺ｦ縺・◆縲・|
| **菫ｮ豁｣蜀・ｮｹ** | `.vscode/settings.json` 縺ｫ `r.lsp.enabled=false`縲～r.sessionWatcher=false`縲～r.helpPanel.previewLocalPackages=[]`縲～r.session.viewers.viewColumn.*=Disable`縲～r.alwaysUseActiveTerminal=true` 繧定ｿｽ蜉�縺励ヽ 諡｡蠑ｵ縺ｮ閾ｪ蜍戊ｨ隱槭し繝ｼ繝舌・Help/Plot 繝薙Η繝ｼ繧｢襍ｷ蜍輔ｒ蛛懈ｭ｢縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `.vscode/settings.json`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | 螳溯｡御ｸｭ `cmd.exe` 縺ｮ繧ｳ繝槭Φ繝峨Λ繧､繝ｳ縺・Antigravity 驟堺ｸ九・ `reditorsupport.r-2.8.8-universal` 繧呈欠縺励※縺・ｋ縺薙→縲∵怙譁ｰ繝ｭ繧ｰ縺ｫ `R Language Server ... started` 縺悟・縺ｦ縺・ｋ縺薙→繧堤｢ｺ隱阪＠縺溘りｨｭ螳壼渚譏�蠕後・ Antigravity 縺ｮ繧ｦ繧｣繝ｳ繝峨え蜀崎ｪｭ縺ｿ霎ｼ縺ｿ縺ｾ縺溘・蜀崎ｵｷ蜍輔〒譁ｰ險ｭ螳壹′譛牙柑縺ｫ縺ｪ繧九・|
| **Lessons Learned** | IDE 繝輔Μ繝ｼ繧ｺ隱ｿ譟ｻ縺ｧ縺ｯ縲√ヵ繧｡繧､繝ｫ watcher 縺�縺代〒縺ｪ縺乗僑蠑ｵ縺瑚｣上〒遶九■荳翫￡繧玖｣懷勧繝励Ο繧ｻ繧ｹ縺ｾ縺ｧ隕九ｋ縺ｨ蜴溷屏縺ｫ譌ｩ縺丞ｱ翫￥縲ゆｽｿ縺｣縺ｦ縺・↑縺・ｨ隱樊僑蠑ｵ縺ｯ縲∫┌蜉ｹ蛹悶〒縺阪↑縺・�ｴ蜷医〒繧ゅΡ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ險ｭ螳壹〒閾ｪ蜍墓ｩ溯・繧呈ｭ｢繧√ｋ縺�縺代〒螳牙ｮ壽ｧ縺御ｸ翫′繧九・|
| **蜀咲匱髦ｲ豁｢遲・* | 譁ｰ縺励＞ IDE 諡｡蠑ｵ繧貞ｸｸ逕ｨ縺吶ｋ蜑阪↓縲∬・蜍戊ｵｷ蜍輔☆繧玖ｨ隱槭し繝ｼ繝舌”elp server縲『atcher 縺ｮ譛臥┌繧堤｢ｺ隱阪☆繧九ゆｻ雁屓縺ｮ繧医≧縺ｪ `cmd.exe` 轤ｹ貊・′蜃ｺ縺溷�ｴ蜷医・縲√∪縺夊ｦｪ繝励Ο繧ｻ繧ｹ縺ｨ繧ｳ繝槭Φ繝峨Λ繧､繝ｳ縺九ｉ諡｡蠑ｵ蜷阪ｒ迚ｹ螳壹＠縺ｦ繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ險ｭ螳壹〒謚大宛縺吶ｋ縲・|

## INC-015: R 諡｡蠑ｵ險ｭ螳壹□縺代〒縺ｯ `cmd.exe` 轤ｹ貊・ｒ豁｢繧√″繧後★縲∵僑蠑ｵ譛ｬ菴薙ｒ辟｡蜉ｹ蛹・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-12 |
| **逋ｺ隕区婿豕・* | INC-014 縺ｮ險ｭ螳壼､画峩蠕後↓ Antigravity 繧貞・襍ｷ蜍輔＠縺ｦ繧・`cmd.exe` 繝昴ャ繝励い繝・・縺檎ｶ咏ｶ壹よ怙譁ｰ繝ｭ繧ｰ `20260412T000423` 縺ｨ `cmd.exe` 縺ｮ繧ｳ繝槭Φ繝峨Λ繧､繝ｳ繧貞・遒ｺ隱阪＠縺溘・|
| **蠖ｱ髻ｿ遽・峇** | 繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ險ｭ螳壼､画峩縺�縺代〒縺ｯ R 諡｡蠑ｵ縺ｮ閾ｪ蜍戊ｵｷ蜍輔′谿九ｊ縲∫判髱｢轤ｹ貊・→謫堺ｽ憺仆螳ｳ縺檎ｶ咏ｶ壹＠縺溘・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: `r.lsp.enabled=false` 縺ｨ `r.sessionWatcher=false` 繧貞・繧後※繧・`cmd.exe /c ... Rterm.exe ... helpServer.R` 縺悟・逋ｺ縺励◆縲・**Why2**: R 諡｡蠑ｵ縺ｯ `workspaceContains` 縺ｫ繧医ｊ activation 縺輔ｌ縲∬ｨｭ螳夂┌蜉ｹ蛹門ｾ後ｂ Help server 蛛ｴ縺ｮ襍ｷ蜍慕ｵ瑚ｷｯ縺梧ｮ九▲縺ｦ縺・◆縲・**Why3**: 縺薙・繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ縺ｫ縺ｯ R 髢｢騾｣繝輔ぃ繧､繝ｫ讀懃衍譚｡莉ｶ縺後≠繧翫∵僑蠑ｵ閾ｪ菴薙・隱ｭ縺ｿ霎ｼ縺ｿ繧帝∩縺代ｉ繧後↑縺九▲縺溘・**Why4**: Antigravity 蛛ｴ縺ｧ縺薙・諡｡蠑ｵ繧偵Ρ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ蜊倅ｽ阪↓邁｡蜊倥↓ disable 縺ｧ縺阪★縲∬ｨｭ螳壹□縺代〒縺ｯ螳悟・蛛懈ｭ｢縺ｫ螻翫°縺ｪ縺九▲縺溘・**Why5**: 髱樔ｽｿ逕ｨ險隱樊僑蠑ｵ縺ｫ蟇ｾ縺吶ｋ譛邨よ焔谿ｵ縺ｨ縺励※縲悟庄騾・↑諡｡蠑ｵ騾驕ｿ縲阪ｒ驕狗畑謇矩�・↓謖√▲縺ｦ縺・↑縺九▲縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | Antigravity 繧貞●豁｢縺励◆荳翫〒 `C:\\Users\\yasu\\.antigravity\\extensions\\reditorsupport.r-2.8.8-universal` 繧・`...universal.disabled` 縺ｸ繝ｪ繝阪・繝�縺励ヽ 諡｡蠑ｵ譛ｬ菴薙ｒ蜿ｯ騾・↓辟｡蜉ｹ蛹悶＠縺溘・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | 辟｡蜉ｹ蛹門ｾ後∵僑蠑ｵ荳隕ｧ荳翫・ `reditorsupport.r-2.8.8-universal.disabled` 縺ｨ縺励※騾驕ｿ縺輔ｌ縲、ntigravity 蜀崎ｵｷ蜍墓凾縺ｫ蠖楢ｩｲ諡｡蠑ｵ縺後Ο繝ｼ繝牙ｯｾ雎｡縺九ｉ螟悶ｌ繧狗憾諷九↓縺励◆縲・|
| **Lessons Learned** | IDE 諡｡蠑ｵ縺ｮ閾ｪ蜍戊ｵｷ蜍輔・縲∬ｨｭ螳壼､繧医ｊ繧・activation event 縺悟・縺ｫ蜉ｹ縺丞�ｴ蜷医′縺ゅｋ縲ゆｸ崎ｦ∵僑蠑ｵ縺悟ｮ牙ｮ壽ｧ繧貞ｴｩ縺吶→縺阪・縲∝庄騾・↑繝輔か繝ｫ繝騾驕ｿ縺梧怙繧る溘￥螳牙・縺ｪ豁｢陦遲悶↓縺ｪ繧九・|
| **蜀咲匱髦ｲ豁｢遲・* | 髱樔ｽｿ逕ｨ諡｡蠑ｵ縺瑚｣懷勧繝励Ο繧ｻ繧ｹ繧・watcher 繧貞享謇九↓襍ｷ蜍輔☆繧句�ｴ蜷医・) 險ｭ螳壹〒謚大宛縲・) 縺�繧√↑繧画僑蠑ｵ譛ｬ菴薙ｒ騾驕ｿ縲√・鬆・〒蟇ｾ蜃ｦ縺吶ｋ縲ょｾｩ蟶ｰ縺悟ｿ・ｦ√↓縺ｪ縺｣縺溷�ｴ蜷医・ `.disabled` 繧貞・蜷阪↓謌ｻ縺励※蜀崎ｵｷ蜍輔☆繧九・|

## INC-016: `continuous_email_ingest_daemon.py` 縺悟ｭ・Python 繧偵さ繝ｳ繧ｽ繝ｼ繝ｫ莉倥″縺ｧ襍ｷ蜍・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-12 |
| **逋ｺ隕区婿豕・* | R 諡｡蠑ｵ繧堤┌蜉ｹ蛹悶＠縺溷ｾ後ｂ譁ｰ縺励＞ `CMD` 縺悟・逋ｺ縲よ怙譁ｰ `conhost.exe` 縺ｮ隕ｪ蟄宣未菫ゅｒ霑ｽ縺｣縺溘→縺薙ｍ縲～python.exe -> host_gmail_incremental_sync.py` 縺ｫ蛻ｰ驕斐＠縺溘・|
| **蠖ｱ髻ｿ遽・峇** | 謨ｰ蛻・＃縺ｨ縺ｫ `CMD` 繧ｦ繧｣繝ｳ繝峨え縺・1 縺､髢九″縲√Θ繝ｼ繧ｶ繝ｼ謫堺ｽ懊ｒ螯ｨ縺偵◆縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: 譁ｰ縺励＞ `conhost.exe` 縺檎函謌舌＆繧後※縺・◆縲・**Why2**: 隕ｪ縺ｯ `python.exe` 縺ｧ縲～host_gmail_incremental_sync.py` 繧貞ｮ溯｡後＠縺ｦ縺・◆縲・**Why3**: 縺昴・隕ｪ縺ｯ `continuous_email_ingest_daemon.py` 縺ｧ縲～subprocess.Popen()` 縺ｫ繧医ｊ蟄・Python 繧定ｵｷ蜍輔＠縺ｦ縺・◆縲・**Why4**: Windows 蜷代￠縺ｮ `CREATE_NO_WINDOW` 謖・ｮ壹′縺ｪ縺上∵里螳壹〒繧ｳ繝ｳ繧ｽ繝ｼ繝ｫ莉倥″襍ｷ蜍輔↓縺ｪ縺｣縺ｦ縺・◆縲・**Why5**: 蟶ｸ鬧舌ワ繝ｼ繝阪せ縺九ｉ蟄舌・繝ｭ繧ｻ繧ｹ繧定ｵｷ蜍輔☆繧矩圀縺ｮ縲碁撼陦ｨ遉ｺ襍ｷ蜍輔阪Ν繝ｼ繝ｫ縺後さ繝ｼ繝峨↓邨・∩霎ｼ縺ｾ繧後※縺・↑縺九▲縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `data/workspace/continuous_email_ingest_daemon.py` 縺ｮ `subprocess.Popen()` 縺ｫ Windows 縺ｧ縺ｯ `creationflags=subprocess.CREATE_NO_WINDOW` 繧呈ｸ｡縺吶ｈ縺・ｿｮ豁｣縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/workspace/continuous_email_ingest_daemon.py`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `conhost.exe PID 13652` 縺ｮ隕ｪ縺・`python.exe PID 6160`縲√◎縺ｮ隕ｪ縺・`continuous_email_ingest_daemon.py` 縺ｧ縺ゅｋ縺薙→繧堤｢ｺ隱阪よ里蟄倥・ `python.exe` / `conhost.exe` 縺ｯ蛛懈ｭ｢貂医∩縺ｧ縲∵ｬ｡蝗櫁ｵｷ蜍輔°繧峨・髱櫁｡ｨ遉ｺ繝輔Λ繧ｰ莉倥″縺ｧ蟄舌・繝ｭ繧ｻ繧ｹ縺瑚ｵｷ蜍輔☆繧区ｧ区・縺ｫ縺励◆縲・|
| **Lessons Learned** | Windows 蟶ｸ鬧舌せ繧ｯ繝ｪ繝励ヨ縺悟挨縺ｮ Python 繧定ｵｷ蜍輔☆繧句�ｴ蜷医∬｡ｨ遉ｺ譛臥┌縺ｯ譏守､ｺ縺励↑縺・→譌｢螳壽嫌蜍輔↓蠑輔″縺壹ｉ繧後ｋ縲６I 繧呈戟縺溘↑縺・｣懷勧繝励Ο繧ｻ繧ｹ縺ｯ縲∝ｸｸ縺ｫ髱櫁｡ｨ遉ｺ襍ｷ蜍輔ｒ繝・ヵ繧ｩ繝ｫ繝医↓縺吶ｋ譁ｹ縺悟ｮ牙・縲・|
| **蜀咲匱髦ｲ豁｢遲・* | Windows 縺ｧ `subprocess.Popen()` / `run()` 繧剃ｽｿ縺・ｸｸ鬧千ｳｻ繧ｹ繧ｯ繝ｪ繝励ヨ縺ｯ縲√さ繝ｳ繧ｽ繝ｼ繝ｫ荳崎ｦ√↑繧・`CREATE_NO_WINDOW` 繧呈ｨ呎ｺ門喧縺吶ｋ縲よ眠縺励＞ `conhost.exe` 縺悟・縺溷�ｴ蜷医・隕ｪ蟄宣未菫ゅｒ縺溘←繧翫√∪縺・daemon 縺九ｉ縺ｮ蟄占ｵｷ蜍輔°繧堤｢ｺ隱阪☆繧九・|

---

## INC-010: Claudian 蜷檎ｨｮ髫懷ｮｳ縺ｮ閾ｪ蜍墓､懃衍谺�螯・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | 繝ｦ繝ｼ繧ｶ繝ｼ縺九ｉ縲悟酔遞ｮ髫懷ｮｳ繧定・蜍墓､懃衍縺吶ｋ繝√ぉ繝・け鬆・岼縺ｾ縺ｧ霑ｽ蜉�縲阪→隕∵悍縲よ里蟄倥・蠕ｩ譌ｧ蠕後ｂ縲～claudian-spawn.log` 縺ｨ `claudian-bridge.log` 繧呈焔蜍輔〒隱ｭ繧驕狗畑縺ｫ萓晏ｭ倥＠縺ｦ縺・◆縲・|
| **蠖ｱ髻ｿ遽・峇** | Claudian 縺ｮ Windows 襍ｷ蜍輔｜ridge response shape縲＾llama 逶ｴ邨占ｨｭ螳壹∬ｿ皮ｭ泌ｾ・■驕・ｻｶ縺ｮ蜀咲匱繧貞叉譎ゅ↓讀懃衍縺ｧ縺阪★縲∝・縺ｳ縲檎┌蜿榊ｿ懊阪↓隕九∴繧九Μ繧ｹ繧ｯ縺梧ｮ九▲縺ｦ縺・◆縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: 蠕ｩ譌ｧ繧ｳ繝ｼ繝峨・蜈･縺｣縺ｦ縺・◆縺後∝・逋ｺ蜈・吶ｒ邯咏ｶ夂屮隕悶☆繧・watchdog 縺後↑縺九▲縺溘・**Why2**: `spawn EINVAL`縲～undefined.id`縲～model not found`縲∫ｩｺ霑皮ｭ斐｝ending turn 縺悟挨繝ｭ繧ｰ縺ｫ謨｣蝨ｨ縺励※縺・◆縲・**Why3**: 蜿､縺・､ｱ謨励Ο繧ｰ縺梧ｮ九ｋ縺溘ａ縲∝腰邏・grep 縺ｧ縺ｯ隱､讀懃衍縺励ｄ縺吶￥縲梧怙蠕後・謌仙粥縺梧怙蠕後・螟ｱ謨励ｒ荳雁屓縺｣縺溘°縲阪・蛻､螳壹′蠢・ｦ√□縺｣縺溘・**Why4**: 荳谺｡蠕ｩ譌ｧ繧貞━蜈医＠縺溽ｵ先棡縲・°逕ｨ observability 縺ｮ螳溯｣・′蠕悟屓縺励↓縺ｪ縺｣縺ｦ縺・◆縲・**Why5**: Claudian 蟆ら畑縺ｮ `status.json` / `harness_status.json` 繧貞・縺吝､紋ｻ倥￠繝上・繝阪せ縺梧悴謨ｴ蛯吶□縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `data/workspace/claudian_watchdog.py` 繧定ｿｽ蜉�縺励・1) `.claudian/claudian-settings.json` 縺ｨ plugin `data.json` 縺ｮ險ｭ螳壽紛蜷域ｧ縲・2) spawn log 縺ｮ `spawn EINVAL` 蜀咲匱譛臥┌縺ｨ configured path 蝗槫ｾｩ縲・3) bridge log 縺ｮ `undefined.id` / `model 'openai/qwen3:8b' not found` / 遨ｺ霑皮ｭ・/ pending turn / 鬮倬≦蟒ｶ縲・4) Ollama `/api/tags` 縺ｫ繧医ｋ `qwen3:8b` 蟄伜惠遒ｺ隱阪ｒ閾ｪ蜍募愛螳壹☆繧九ｈ縺・↓縺励◆縲ゅ≠繧上○縺ｦ `scripts/start_claudian_watchdog.ps1` 繧定ｿｽ蜉�縺励∝､紋ｻ倥￠蟶ｸ鬧占ｵｷ蜍輔ｒ蜿ｯ閭ｽ縺ｫ縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/workspace/claudian_watchdog.py`, `scripts/start_claudian_watchdog.ps1`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `python data/workspace/claudian_watchdog.py --once` 縺ｧ status JSON 繧堤函謌舌＠縲・縺､縺ｮ繝√ぉ繝・け縺悟・蜉帙＆繧後ｋ縺薙→繧堤｢ｺ隱阪☆繧九Ａspawn EINVAL` 縺ｯ縲悟ｱ･豁ｴ縺ゅｊ縺�縺悟屓蠕ｩ貂医∩縲阪｜ridge 縺ｯ recent completed turn 縺ｨ latency縲＾llama 縺ｯ `qwen3:8b` 縺ｮ蟄伜惠繧貞愛螳壹〒縺阪ｋ讒区・縲・|
| **Lessons Learned** | 蠕ｩ譌ｧ縺�縺代〒邨ゅ∴繧九→縲∝・逋ｺ譎ゅ・蛻晏虚縺後∪縺滓焔蜍輔Ο繧ｰ隱ｿ譟ｻ縺ｫ謌ｻ繧九８indows wrapper 繧・bridge contract 縺ｮ繧医≧縺ｪ蠅・阜髫懷ｮｳ縺ｯ縲∽ｿｮ豁｣縺ｨ蜷梧凾縺ｫ watchdog / status JSON 縺ｾ縺ｧ蜈･繧後※蛻昴ａ縺ｦ驕狗畑蜩∬ｳｪ縺ｫ縺ｪ繧九・|
| **蜀咲匱髦ｲ豁｢遲・* | `claudian_watchdog.py` 繧貞ｮ壽悄螳溯｡後∪縺溘・蟶ｸ鬧舌＆縺帙～data/workspace/claudian_watchdog_status.json` 縺ｮ `stage` / `findings` 繧堤屮隕門ｯｾ雎｡縺ｫ縺吶ｋ縲ゆｻ雁ｾ・Claudian 髢｢騾｣菫ｮ豁｣繧貞・繧後ｋ縺溘・縺ｫ縲√％縺ｮ watchdog 縺ｸ譁ｰ縺励＞ failure signature 繧定ｿｽ蜉�縺吶ｋ縲・|

---

## INC-012: Claudian Codex 繝｢繝・Ν驕ｸ謚櫁い縺悟ｰ代↑縺剰ｻｽ驥上Δ繝・Ν縺ｸ蛻・ｊ譖ｿ縺医↓縺上＞
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | 繝ｦ繝ｼ繧ｶ繝ｼ蝣ｱ蜻翫・laudian 縺ｮ Codex 繝｢繝・Ν繝峨Ο繝・・繝繧ｦ繝ｳ縺ｫ `GPT-5.4` 縺ｨ `qwen3:8b` 縺ｪ縺ｩ荳驛ｨ縺励°蜃ｺ縺壹√ｈ繧願ｻｽ縺・Δ繝・Ν縺ｸ蛻・ｊ譖ｿ縺医↓縺上°縺｣縺溘・|
| **蠖ｱ髻ｿ遽・峇** | `data/state/Obsidian Vault/.obsidian/plugins/claudian` 驟堺ｸ九・ Codex UI縲る∈謚櫁い荳崎ｶｳ縺ｫ繧医ｊ縲・溷ｺｦ驥崎ｦ悶・蛻・ｊ譖ｿ縺医ｄ霑ｽ蜉�繝｢繝・Ν縺ｮ髴ｲ蜃ｺ縺碁°逕ｨ萓晏ｭ倥↓縺ｪ縺｣縺ｦ縺・◆縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Codex 繝｢繝・Ν荳隕ｧ縺・`main.js` 蜀・・髱咏噪驟榊・縺ｫ縺ｻ縺ｼ蝗ｺ螳壹＆繧後※縺・◆縲・**Why2**: 譌｢蟄伜ｮ溯｣・・ `OPENAI_MODEL` 1莉ｶ縺�縺代ｒ迚ｹ蛻･謇ｱ縺・＠縲∬､・焚繝｢繝・Ν縺ｮ蛻玲嫌繧貞女縺大叙繧後↑縺九▲縺溘・**Why3**: 繝ｭ繝ｼ繧ｫ繝ｫ/霑ｽ蜉�繝｢繝・Ν繧貞・縺励◆縺・�ｴ蜷医〒繧ゅゞI 縺ｫ貂｡縺帙ｋ迺ｰ蠅・､画焚縺悟腰荳繝｢繝・Ν蜑肴署縺�縺｣縺溘・**Why4**: 縺昴・縺溘ａ霆ｽ驥上Δ繝・Ν繧・ｰ・擂霑ｽ蜉�繝｢繝・Ν繧貞・縺吶◆縺ｳ縺ｫ繧ｳ繝ｼ繝牙､画峩縺悟ｿ・ｦ√□縺｣縺溘・**Why5**: 縲梧里螳壹Δ繝・Ν縲阪→縲檎腸蠅・罰譚･縺ｮ霑ｽ蜉�繝｢繝・Ν縲阪ｒ繝槭・繧ｸ縺吶ｋ蜈ｱ騾壼・逅・′ Codex 蛛ｴ縺ｫ譛ｪ螳溯｣・□縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `main.js` 縺ｮ Codex 繝｢繝・Ν螳夂ｾｩ縺ｫ `gpt-5.3-codex` 縺ｨ `gpt-5.2` 繧定ｿｽ蜉�縺励√＆繧峨↓ `OPENAI_AVAILABLE_MODELS` / `CODEX_AVAILABLE_MODELS` 縺九ｉ隍・焚繝｢繝・Ν繧定ｪｭ縺ｿ霎ｼ繧薙〒繝峨Ο繝・・繝繧ｦ繝ｳ縺ｸ邨ｱ蜷医☆繧九ｈ縺・ｿｮ豁｣縺励◆縲ゅ≠繧上○縺ｦ `.claudian/claudian-settings.json` 縺ｨ plugin `data.json` 縺ｫ `OPENAI_AVAILABLE_MODELS` 繧定ｿｽ蜉�縺励∬ｻｽ驥丞ｯ・ｊ縺ｮ蛟呵｣懊ｒ蜊ｳ譎る∈謚槫庄閭ｽ縺ｫ縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/data.json`, `data/state/Obsidian Vault/.claudian/claudian-settings.json`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `node --check "data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js"` 縺ｧ讒区枚繧ｨ繝ｩ繝ｼ縺ｪ縺励ｒ遒ｺ隱阪ＡOPENAI_AVAILABLE_MODELS` 縺ｫ蛻玲嫌縺励◆繝｢繝・Ν縺瑚ｨｭ螳壹ヵ繧｡繧､繝ｫ荳翫〒菫晄戟縺輔ｌ縲∵里螳壹Δ繝・Ν縺ｨ驥崎､・勁蜴ｻ縺励▽縺､ UI 縺ｫ貂｡繧区ｧ区・縺ｫ縺ｪ縺｣縺溘・|
| **Lessons Learned** | 繝｢繝・Ν驕ｸ謚・UI 縺ｯ蝗ｺ螳壼・謖吶↓蟇・○縺吶℃繧九→驕狗畑騾溷ｺｦ縺瑚誠縺｡繧九りｿｽ蜉�鬆ｻ蠎ｦ縺碁ｫ倥＞蛟､縺ｯ縲∵里螳壼､繧呈戟縺｡縺､縺､迺ｰ蠅・､画焚縺九ｉ諡｡蠑ｵ縺ｧ縺阪ｋ蠖｢縺ｫ縺励※縺翫￥縺ｨ菫晏ｮ医＠繧・☆縺・・|
| **蜀咲匱髦ｲ豁｢遲・* | Claudian 縺ｮ Codex 繝｢繝・Ν霑ｽ蜉�譎ゅ・ `OPENAI_AVAILABLE_MODELS` 繧貞━蜈育噪縺ｫ譖ｴ譁ｰ縺励√さ繝ｼ繝牙､画峩縺ｯ譌｢螳壼呵｣懊ｄ繝槭・繧ｸ繝ｭ繧ｸ繝・け縺ｮ謾ｹ蝟・凾縺ｫ髯仙ｮ壹☆繧九ゆｻ雁ｾ梧眠繝｢繝・Ν繧定ｶｳ縺咎圀繧ょ腰荳 `OPENAI_MODEL` 縺�縺代↓萓晏ｭ倥＠縺ｪ縺・％縺ｨ繧偵Ξ繝薙Η繝ｼ鬆・岼縺ｫ蜉�縺医ｋ縲・|

---

## INC-011: Claudian 蛻晏屓蠢懃ｭ斐・菴捺─驕・ｻｶ
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | 繝ｦ繝ｼ繧ｶ繝ｼ縺・`Hello` 蠕後・霑皮ｭ泌ｾ・■縺碁聞縺吶℃繧九→蝣ｱ蜻翫Ｃridge log 縺ｧ縺ｯ 2026-04-11 13:10:40 JST 縺ｮ騾∽ｿ｡縺九ｉ 13:13:37 JST 縺ｮ霑皮ｭ泌ｮ御ｺ・∪縺ｧ邏・77遘偵°縺九▲縺ｦ縺・◆縲・|
| **蠖ｱ髻ｿ遽・峇** | Claudian 縺ｮ霆ｽ縺・ｼ夊ｩｱ縺ｧ繧ゅ檎┌蜿榊ｿ懊阪↓隕九∴繧・☆縺上∝茜逕ｨ邯咏ｶ壽ｧ繧剃ｸ九￡縺ｦ縺・◆縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: `Hello` 縺ｮ繧医≧縺ｪ霆ｽ縺・・蜉帙〒繧ゅΟ繝ｼ繧ｫ繝ｫ `qwen3:8b` 縺ｮ蠢懃ｭ泌ｮ御ｺ・∪縺ｧ蠕・▲縺ｦ縺九ｉ UI 縺ｫ蜈ｨ譁・ｒ霑斐＠縺ｦ縺・◆縲・**Why2**: bridge 縺ｯ `stream:false` 縺ｧ completion 螳御ｺ・ｾ後↓ 1 蝗槭□縺・`delta` 繧帝√▲縺ｦ縺・◆縲・**Why3**: 蛻晏屓繝｡繝・そ繝ｼ繧ｸ騾∽ｿ｡譎ゅ↓縺ｯ蛻･繧ｹ繝ｬ繝・ラ縺ｧ莨夊ｩｱ繧ｿ繧､繝医Ν逕滓・繧ょ酔譎ゅ↓襍ｰ縺｣縺ｦ縺・◆縲・**Why4**: 繧ｿ繧､繝医Ν逕滓・繧よ悽菴薙→蜷後§繝ｭ繝ｼ繧ｫ繝ｫ繝｢繝・Ν繧剃ｽｿ縺・◆繧√；PU/CPU 雉・ｺ舌→蠕・■譎る俣繧剃ｽ呵ｨ医↓豸郁ｲｻ縺励※縺・◆縲・**Why5**: 菴捺─騾溷ｺｦ謾ｹ蝟・・縺溘ａ縺ｮ縲悟・縺ｫ譁・ｭ励ｒ蜃ｺ縺吶阪瑚｣懷勧蜃ｦ逅・ｒ繝ｭ繝ｼ繧ｫ繝ｫ蜊ｳ譎ょ喧縺吶ｋ縲阪→縺・≧譛驕ｩ蛹悶′ bridge 縺ｫ譛ｪ螳溯｣・□縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `codex_bridge.js` 繧呈峩譁ｰ縺励・1) 騾壼ｸｸ蠢懃ｭ斐・ Ollama OpenAI 莠呈鋤 API 繧・`stream:true` 縺ｧ蜻ｼ縺ｳ蜃ｺ縺励※ `item/agentMessage/delta` 繧帝先ｬ｡騾√ｋ縲・2) `max_tokens: 160` 縺ｨ `temperature: 0.2` 縺ｧ遏ｭ繧√・螳牙ｮ壼ｯ・ｊ縺ｫ縺吶ｋ縲・3) 繧ｿ繧､繝医Ν逕滓・繝ｪ繧ｯ繧ｨ繧ｹ繝医・繝｢繝・Ν繧貞他縺ｰ縺・bridge 蜀・〒蜊ｳ譎ら函謌舌☆繧九√ｈ縺・↓縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `node --check` 縺ｧ讒区枚遒ｺ隱肴ｸ医∩縲ゅΟ繝ｼ繧ｫ繝ｫ蜀咲樟縺ｧ繧ｿ繧､繝医Ν逕滓・繝ｪ繧ｯ繧ｨ繧ｹ繝医・蜊ｳ蠎ｧ縺ｫ `Greet the assistant` 繧定ｿ斐☆縺薙→繧堤｢ｺ隱阪る壼ｸｸ莨夊ｩｱ縺ｯ `item/agentMessage/start` 縺悟叉譎ゅ↓蜃ｺ繧九％縺ｨ繧堤｢ｺ隱阪＠縺溘・|
| **Lessons Learned** | 繝ｭ繝ｼ繧ｫ繝ｫ繝｢繝・Ν縺ｧ縺ｯ縲梧怙邨ょｮ御ｺ・凾髢薙阪□縺代〒縺ｪ縺上梧怙蛻昴・蜿ｯ隕匁枚蟄励∪縺ｧ縺ｮ譎る俣縲阪ｒ譛驕ｩ蛹悶＠縺ｪ縺・→縲√Θ繝ｼ繧ｶ繝ｼ菴捺─縺ｯ螟ｧ縺阪￥謔ｪ蛹悶☆繧九り｣懷勧繧ｿ繧ｹ繧ｯ縺・deterministic 縺ｫ蜃ｦ逅・〒縺阪ｋ縺ｪ繧峨Δ繝・Ν縺ｫ謚輔￡縺ｪ縺・婿縺悟ｮ牙ｮ壹☆繧九・|
| **蜀咲匱髦ｲ豁｢遲・* | Claudian 縺ｮ latency 謾ｹ蝟・〒縺ｯ縲√Δ繝・Ν螟画峩蜑阪↓ `streaming`縲～token cap`縲～title-generation bypass` 縺ｮ繧医≧縺ｪ transport 蛛ｴ蟇ｾ遲悶ｒ蜈医↓讀懆ｨ弱☆繧九Ｘatchdog 縺ｮ latency 繝√ぉ繝・け繧堤ｶ咏ｶ壹＠縲∝・蠎ｦ 2 蛻・ｶ・・螻･豁ｴ縺悟｢励∴繧句�ｴ蜷医・霆ｽ驥上Δ繝・Ν霑ｽ蜉�繧呈､懆ｨ弱☆繧九・|

---

## INC-007: Claudian `spawn EINVAL` 蜀阪・匱・・onfigured `cliPath` 縺・PATH 閾ｪ蜍戊ｧ｣豎ｺ縺ｫ雋�縺代ｋ・・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | 繝ｦ繝ｼ繧ｶ繝ｼ蝣ｱ蜻・`Error: spawn EINVAL`縲ＡC:\\Users\\yasu\\.claude\\debug\\claudian-spawn.log` 繧堤｢ｺ隱阪☆繧九→縲～data.json` 縺ｧ縺ｯ plugin 蜷梧｢ｱ `codex.cmd` 繧呈欠螳壹＠縺ｦ縺・ｋ縺ｮ縺ｫ縲∝ｮ溯｡梧凾縺ｯ `C:\\Users\\yasu\\AppData\\Roaming\\npm\\codex.cmd` 縺碁∈縺ｰ繧後※縺・◆縲・|
| **蠖ｱ髻ｿ遽・峇** | `data/state/Obsidian Vault/.obsidian/plugins/claudian` 驟堺ｸ九・ Codex 騾｣謳ｺ縲８indows 迺ｰ蠅・〒 Codex provider 蛻晄悄蛹悶′螟ｱ謨励＠縲＾bsidian 縺九ｉ Codex 繧ｻ繝・す繝ｧ繝ｳ繧帝幕蟋九〒縺阪↑縺・・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Claudian 縺・global npm 驟堺ｸ九・ `codex.cmd` 繧堤峩謗･ spawn 縺励～spawn EINVAL` 縺ｫ縺ｪ縺｣縺溘・**Why2**: `codex_bridge.js` 縺ｸ蛻・ｊ譖ｿ縺医ｋ蜑肴ｮｵ縺ｮ CLI 隗｣豎ｺ縺ｧ縲∬ｨｭ螳壽ｸ医∩ `cliPath` 繧医ｊ PATH 閾ｪ蜍墓爾邏｢邨先棡縺悟━蜈医＆繧後※縺・◆縲・**Why3**: `data.json` 縺ｫ縺ｯ plugin 蜷梧｢ｱ `codex.cmd` 縺御ｿ晏ｭ倥＆繧後※縺・◆縺後～resolveCodexCliPath` 縺・Windows 縺ｧ `findCodexBinaryPath(customEnv.PATH)` 繧貞・縺ｫ霑斐＠縺ｦ縺・◆縲・**Why4**: 縺昴・邨先棡縲《ibling bridge 謗｢邏｢繧・global npm 驟堺ｸ九ｒ蝓ｺ貅悶↓縺励∝ｭ伜惠縺励↑縺・`codex_bridge.js` 繧定ｦ九◆蠕後↓蜊ｱ髯ｺ縺ｪ `.cmd` 逶ｴ spawn 縺ｸ谿狗蕗縺励◆縲・**Why5**: 縲後Θ繝ｼ繧ｶ繝ｼ縺梧・遉ｺ險ｭ螳壹＠縺・CLI path 繧呈怙蜆ｪ蜈医☆繧九阪→縺・≧蝓ｺ譛ｬ繝ｫ繝ｼ繝ｫ縺・resolver 縺ｫ蜿肴丐縺輔ｌ縺ｦ縺・↑縺九▲縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `resolveCodexCliPath` 縺ｮ蜆ｪ蜈磯�・ｽ阪ｒ菫ｮ豁｣縺励～cliPathsByHost` / `cliPath` 縺ｮ螳溷惠繝輔ぃ繧､繝ｫ繧・PATH 閾ｪ蜍戊ｧ｣豎ｺ繧医ｊ蜈医↓謗｡逕ｨ縺吶ｋ繧医≧螟画峩縲りｨｭ螳・path 繧剃ｽｿ縺｣縺溷�ｴ蜷医ｂ spawn 繝ｭ繧ｰ縺ｸ谿九☆繧医≧縺ｫ縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `data.json` 縺ｮ `cliPath` 縺・plugin 蜷梧｢ｱ `codex.cmd` 繧呈欠縺励※縺・ｋ縺薙→繧堤｢ｺ隱阪ゆｿｮ豁｣蠕後た繝ｼ繧ｹ縺ｧ縺ｯ configured path 繧貞・縺ｫ霑斐☆縺薙→繧堤｢ｺ隱阪Ａnode --check "data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js"` 繧貞ｮ溯｡後＠縲∵ｧ区枚繧ｨ繝ｩ繝ｼ縺ｪ縺励ｒ遒ｺ隱阪・|
| **Lessons Learned** | Windows 縺ｮ wrapper 蝗樣∩縺�縺代〒縺ｪ縺上√後←縺ｮ wrapper 繧帝∈縺ｶ縺九阪・蜆ｪ蜈磯�・ｽ阪ｂ蜷後§縺上ｉ縺・㍾隕√り・蜍墓爾邏｢縺ｯ萓ｿ蛻ｩ縺ｧ繧ゅ∵・遉ｺ險ｭ螳壹ｒ荳頑嶌縺阪☆繧九→蜀咲匱隕∝屏縺ｫ縺ｪ繧翫ｄ縺吶＞縲ゅΟ繧ｰ縺ｫ縺ｯ縲御ｽ輔ｒ隕九▽縺代◆縺九阪□縺代〒縺ｪ縺上御ｽ輔ｒ謗｡逕ｨ縺励◆縺九阪ｒ谿九☆譁ｹ縺瑚ｿｽ霍｡縺励ｄ縺吶＞縲・|
| **蜀咲匱髦ｲ豁｢遲・* | Windows resolver 縺ｮ蝗槫ｸｰ遒ｺ隱阪〒縺ｯ縲～configured path exists` / `PATH has different codex.cmd` 縺ｮ遶ｶ蜷医こ繝ｼ繧ｹ繧貞ｿ・★蜷ｫ繧√ｋ縲Ｔpawn 繝ｭ繧ｰ縺ｯ謗｡逕ｨ CLI path 繧呈ｮ九＠縲～.cmd` 逶ｴ spawn 縺瑚ｵｷ縺阪◆繧牙叉蠎ｧ縺ｫ逡ｰ蟶ｸ蛻､螳壹〒縺阪ｋ繧医≧縺ｫ縺吶ｋ縲・|

---

## INC-008: Claudian `Cannot read properties of undefined (reading 'id')`
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | `spawn EINVAL` 隗｣豸亥ｾ後，laudian 蛛ｴ縺ｧ `Cannot read properties of undefined (reading 'id')` 縺檎匱逕溘Ｃridge log 縺ｧ縺ｯ `thread/start` 縺悟ｱ翫＞縺ｦ縺・◆縺後∝ｯｾ蠢懊☆繧区ｧ矩�蛹門ｿ懃ｭ斐′荳崎ｶｳ縺励※縺・◆縲・|
| **蠖ｱ髻ｿ遽・峇** | Obsidian Vault 縺ｮ Claudian 繝励Λ繧ｰ繧､繝ｳ縲・odex provider 蛻晄悄蛹門ｾ後↓ thread 菴懈・繧・turn 髢句ｧ九〒 UI 縺檎ｶ咏ｶ壻ｸ崎・縺ｫ縺ｪ繧九・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Claudian 縺・`result.thread.id` 縺ｾ縺溘・ `result.turn.id` 繧定ｪｭ縺ｿ蜿悶ｍ縺・→縺励※ `undefined.id` 縺ｫ縺ｪ縺｣縺溘・**Why2**: `codex_bridge.js` 縺ｯ `initialize` 莉･螟悶・螟ｧ蜊翫・繝｡繧ｽ繝・ラ縺ｫ蟇ｾ縺励※ `{}` 繧定ｿ斐☆縺�縺代〒縲，odex app-server 莠呈鋤縺ｮ蠢懃ｭ泌ｽ｢繧定ｿ斐＠縺ｦ縺・↑縺九▲縺溘・**Why3**: `thread/start` 縺ｮ謌ｻ繧雁､縺ｫ `thread.id` / `thread.path` 縺後↑縺上～turn/start` 縺ｫ繧・`turn.id` 縺後↑縺九▲縺溘・**Why4**: 騾夂衍邉ｻ繧よ悴螳溯｣・〒縲》urn 螳御ｺ・ｒ蠕・▽蛛ｴ縺梧悄蠕・☆繧・`turn/completed` 繧・agent message 繧､繝吶Φ繝医′譚･縺ｪ縺九▲縺溘・**Why5**: 襍ｷ蜍慕｢ｺ隱阪ｒ `initialize` 謌仙粥縺ｾ縺ｧ縺ｧ豁｢繧√※縺翫ｊ縲∝ｮ滄圀縺ｮ turn 髢句ｧ九ヵ繝ｭ繝ｼ縺ｾ縺ｧ縺ｮ莠呈鋤諤ｧ讀懆ｨｼ縺御ｸ崎ｶｳ縺励※縺・◆縲・|
| **菫ｮ豁｣蜀・ｮｹ** | `codex_bridge.js` 繧呈怙蟆城剞縺ｮ Codex app-server 莠呈鋤 bridge 縺ｫ諡｡蠑ｵ縲Ａthread/start` / `thread/resume` / `turn/start` / `turn/interrupt` / `thread/compact/start` 縺ｮ蠢懃ｭ斐ｒ霑ｽ蜉�縺励～thread.id` / `thread.path` / `turn.id` 繧定ｿ斐☆繧医≧菫ｮ豁｣縲ゅ＆繧峨↓ `item/agentMessage/*` 縺ｨ `turn/completed` 騾夂衍繧帝√ｋ繧医≧縺ｫ縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `node --check` 縺ｧ bridge 縺ｮ讒区枚遒ｺ隱阪ｒ螳滓命縲ゅΟ繝ｼ繧ｫ繝ｫ蜀咲樟縺ｧ縺ｯ `initialize` 蠕後・ `thread/start` 縺・`thread.id` 縺ｨ `path` 繧定ｿ斐＠縲～turn/start` 縺・`turn.id` 縺ｨ `turn/completed` 騾夂衍繧定ｿ斐☆縺薙→繧堤｢ｺ隱阪・|
| **Lessons Learned** | transport 謗･邯壽・蜉溘→ app-server 莠呈鋤縺ｯ蛻･蝠城｡後・CP/JSON-RPC 縺ｮ縲後▽縺ｪ縺後ｋ縲阪□縺代〒縺ｯ荳榊香蛻・〒縲ゞI 縺瑚ｪｭ繧蜈ｷ菴鍋噪縺ｪ繝ｬ繧ｹ繝昴Φ繧ｹ shape 縺ｾ縺ｧ蜷医ｏ縺帙ｋ蠢・ｦ√′縺ゅｋ縲・|
| **蜀咲匱髦ｲ豁｢遲・* | Claudian bridge 縺ｮ蝗槫ｸｰ遒ｺ隱阪↓ `initialize -> thread/start -> turn/start` 縺ｮ荳騾｣縺ｮ繧ｹ繝｢繝ｼ繧ｯ繝・せ繝医ｒ霑ｽ蜉�縺励～thread.id` / `turn.id` / `turn/completed` 縺ｮ蟄伜惠繧貞ｿ・�医メ繧ｧ繝・け縺ｫ縺吶ｋ縲・|

---

## INC-009: Claudian 騾∽ｿ｡辟｡蜿榊ｿ懶ｼ・iteLLM alias 荳肴紛蜷医→ Ollama 逶ｴ邨仙喧・・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | 繝ｦ繝ｼ繧ｶ繝ｼ縺・`Hello` 繧帝∽ｿ｡縺励※繧・UI 縺檎┌蜿榊ｿ懊Ａclaudian-bridge.log` 縺ｧ縺ｯ `turn/start` 縺ｾ縺ｧ騾ｲ繧薙〒縺・◆縺後∬ｿ皮ｭ疲悽譁・′遨ｺ縺�縺｣縺溘・|
| **蠖ｱ髻ｿ遽・峇** | Obsidian Vault 縺ｮ Claudian 繝励Λ繧ｰ繧､繝ｳ縲る∽ｿ｡閾ｪ菴薙・騾壹ｋ縺後∬ｿ皮ｭ斐′陦ｨ遉ｺ縺輔ｌ縺壻ｼ夊ｩｱ蛻ｩ逕ｨ縺悟ｮ溯ｳｪ荳崎・縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Claudian 縺ｧ縺ｯ `turn/start` 縺悟ｮ御ｺ・＠縺ｦ縺・◆縺ｮ縺ｫ蠢懃ｭ疲悽譁・′霑斐ｉ縺ｪ縺九▲縺溘・**Why2**: bridge 縺・LiteLLM 縺ｮ 404 繧ｨ繝ｩ繝ｼ繧堤ｩｺ霑皮ｭ斐→縺励※謇ｱ縺｣縺ｦ縺・◆縲・**Why3**: LiteLLM proxy 縺ｮ alias `claude` / `codex` 縺ｯ蜀・Κ縺ｧ `openai/qwen3:8b` 繧貞盾辣ｧ縺礼ｶ壹￠縲＾llama 蛛ｴ縺ｧ `model not found` 縺ｫ縺ｪ縺｣縺ｦ縺・◆縲・**Why4**: config 菫ｮ豁｣縺�縺代〒縺ｯ proxy 蜀・Κ縺ｮ provider 隗｣驥亥ｷｮ繧貞ｮ悟・縺ｫ貎ｰ縺帙★縲，laudian 縺ｮ蟇ｾ隧ｱ邨瑚ｷｯ縺御ｸ榊ｮ牙ｮ壹↑縺ｾ縺ｾ縺�縺｣縺溘・**Why5**: Claudian 縺梧悽蠖薙↓蠢・ｦ√→縺励※縺・◆縺ｮ縺ｯ LiteLLM 蝗ｺ譛画ｩ溯・縺ｧ縺ｯ縺ｪ縺上√Ο繝ｼ繧ｫ繝ｫ Ollama 縺ｸ縺ｮ螳牙ｮ壹＠縺・chat completion 邨瑚ｷｯ縺�縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `codex_bridge.js` 繧堤腸蠅・､画焚繝吶・繧ｹ縺ｫ縺励～OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENAI_API_KEY` 縺九ｉ逶ｴ謗･謗･邯壼・繧定ｧ｣豎ｺ縺吶ｋ繧医≧螟画峩縲・laudiian 險ｭ螳壹ｒ `http://127.0.0.1:11434/v1` + `qwen3:8b` 縺ｫ譖ｴ譁ｰ縺励´iteLLM 繧堤ｵ檎罰縺帙★ Ollama 縺ｸ逶ｴ邨舌☆繧狗ｵ瑚ｷｯ縺ｸ蛻・ｊ譖ｿ縺医◆縲ゆｽｵ縺帙※ `data/state/litellm_config.yaml` 縺ｮ繝ｭ繝ｼ繧ｫ繝ｫ繝｢繝・Ν螳夂ｾｩ繧・LiteLLM 莠呈鋤蠖｢蠑上∈譏ｯ豁｣縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js`, `data/state/Obsidian Vault/.claudian/claudian-settings.json`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/data.json`, `data/state/litellm_config.yaml`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | bridge 蜊倅ｽ灘・迴ｾ縺ｧ `initialize -> thread/start -> turn/start` 繧貞ｮ溯｡後＠縲～Hello! How can I assist you today?` 縺・`item/agentMessage/delta` 縺ｨ `completed` 縺ｧ霑斐ｋ縺薙→繧堤｢ｺ隱阪・|
| **Lessons Learned** | proxy 繧帝俣縺ｫ謖溘・險ｭ險医・譟碑ｻ溘□縺後∝次蝗�蛻・ｊ蛻・￠荳ｭ縺ｯ萓晏ｭ倡せ縺悟｢励∴繧九ゅΟ繝ｼ繧ｫ繝ｫ蜊倅ｸ霍ｯ邱壹〒蜊∝・縺ｪ讖溯・縺ｯ縲√∪縺壽怙遏ｭ邨瑚ｷｯ縺ｧ螳牙ｮ夂ｨｼ蜒阪＆縺帙※縺九ｉ謚ｽ雎｡蛹悶ｒ雜ｳ縺呎婿縺悟ｮ牙・縲・|
| **蜀咲匱髦ｲ豁｢遲・* | Claudian 縺ｮ逍朱夂｢ｺ隱阪〒縺ｯ縲ゞI 陦ｨ遉ｺ縺�縺代〒縺ｪ縺・bridge 蜊倅ｽ薙・ `Hello` 繧ｹ繝｢繝ｼ繧ｯ繝・せ繝医ｒ邯ｭ謖√☆繧九・iteLLM alias 繧剃ｽｿ縺・�ｴ蜷医ｂ縲√Ο繝ｼ繧ｫ繝ｫ Ollama 逶ｴ邨舌・莉｣譖ｿ邨瑚ｷｯ繧呈ｮ九＠縺ｦ縺翫￥縲・|

---

## INC-006: Claudian `spawn EINVAL` 蜀咲匱・・lobal `codex.cmd` 縺ｨ bundled bridge 縺ｮ蛻・屬・・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | Claudian 襍ｷ蜍墓凾縺ｫ `spawn EINVAL`縲ＡC:\\Users\\yasu\\.claude\\debug\\claudian-spawn.log` 繧堤｢ｺ隱阪☆繧九→縲～C:\\Users\\yasu\\AppData\\Roaming\\npm\\codex.cmd` 繧堤峩謗･ spawn 縺励※螟ｱ謨励＠縺ｦ縺・◆縲・|
| **蠖ｱ髻ｿ遽・峇** | Obsidian Vault 縺ｮ Claudian 繝励Λ繧ｰ繧､繝ｳ縺九ｉ Codex app-server 繧定ｵｷ蜍輔〒縺阪★縲∝・譛溷喧縺ｫ螟ｱ謨励・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Windows 縺ｧ `codex.cmd` 繧・`spawn(..., { shell: false })` 縺励～spawn EINVAL` 縺悟・逋ｺ縺励◆縲・**Why2**: `.cmd` 繧堤峩謗･襍ｷ蜍輔＠縺ｪ縺・◆繧√・蝗樣∩縺ｯ蜈･縺｣縺ｦ縺・◆縺後～codex_bridge.js` 縺ｮ謗｢邏｢縺・global npm 驟堺ｸ九・ sibling 繧貞燕謠舌↓縺励※縺・◆縲・**Why3**: 螳滄圀縺ｮ迺ｰ蠅・〒縺ｯ `codex.cmd` 縺ｯ `C:\\Users\\yasu\\AppData\\Roaming\\npm` 縺ｫ縺ゅｊ縲～codex_bridge.js` 縺ｯ `data/state/Obsidian Vault/.obsidian/plugins/claudian/` 縺ｫ蜷梧｢ｱ縺輔ｌ縺ｦ縺・※蜷後§蝣ｴ謇縺ｫ辟｡縺九▲縺溘・**Why4**: bridge 縺瑚ｦ九▽縺九ｉ縺ｪ縺・◆繧・`node + codex_bridge.js` 縺ｮ逶ｴ襍ｷ蜍輔∈蛻・ｊ譖ｿ繧上ｉ縺壹∵里蟄倥・蜊ｱ髯ｺ縺ｪ `.cmd` spawn 邨瑚ｷｯ縺ｫ谿狗蕗縺励◆縲・**Why5**: global CLI 縺ｨ plugin bundled asset 縺悟・髮｢縺輔ｌ縺滄・鄂ｮ繧呈Φ螳壹＠縺滓怙蠕後・繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ縺梧悴螳溯｣・□縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | Windows wrapper 讀懷・譎ゅ・ bridge 隗｣豎ｺ鬆・ｒ `preferred PATH bridge` -> `codex.cmd sibling bridge` -> `plugin bundled codex_bridge.js` 縺ｫ螟画峩縲Ｔpawn 螟ｱ謨玲凾縺ｮ retry 邨瑚ｷｯ繧ょ酔縺倬�・ｺ上↓邨ｱ荳縺励“lobal npm 驟堺ｸ九↓ bridge 縺檎┌縺上※繧・bundled bridge 繧・`node.exe` 縺ｧ襍ｷ蜍輔〒縺阪ｋ繧医≧縺ｫ縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:60983`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:61007` |
| **讀懆ｨｼ邨先棡** | 繧ｽ繝ｼ繧ｹ遒ｺ隱阪〒 bridge 隗｣豎ｺ鬆・↓ bundled fallback 縺瑚ｿｽ蜉�縺輔ｌ縺溘％縺ｨ繧堤｢ｺ隱阪Ａmain.js` 縺ｯ `node` 縺ｧ讒区枚繝√ぉ繝・け貂医∩縲Ａcodex_bridge.js` 蛛ｴ縺ｮ initialize 蠢懃ｭ斐・ `platformOs=windows`, `platformFamily=windows` 繧定ｿ斐☆縺薙→繧貞・遒ｺ隱阪ゅΟ繧ｰ荳翫・螟ｱ謨礼ｵ瑚ｷｯ (`codex.cmd` 逶ｴ spawn) 縺ｯ莉雁屓縺ｮ蛻・ｲ舌〒蝗樣∩縺輔ｌ繧九・|
| **Lessons Learned** | Windows 縺ｮ `.cmd` 蝗樣∩縺ｯ縲恵ridge 縺瑚ｦ九▽縺九ｋ蜑肴署縲阪□縺代〒縺ｯ荳榊香蛻・・LI 縺ｨ bridge 縺悟挨驟咲ｽｮ縺ｫ縺ｪ繧・npm/plugin 豺ｷ蝨ｨ迺ｰ蠅・ｒ蜑肴署縺ｫ縲∵怙蠕後↓ bundled asset 縺ｸ謌ｻ繧後ｋ險ｭ險医′蠢・ｦ√・|
| **蜀咲匱髦ｲ豁｢遲・* | Windows 襍ｷ蜍輔さ繝ｼ繝峨〒縺ｯ wrapper 螳滉ｽ薙→ bridge 螳滉ｽ薙・驟咲ｽｮ蛻・屬繧貞ｸｸ縺ｫ諠ｳ螳壹☆繧九Ｃridge 隗｣豎ｺ鬆・ｒ繝ｭ繧ｰ縺ｸ谿九＠縲～.cmd` 繧堤峩謗･ spawn 縺吶ｋ邨瑚ｷｯ繧貞屓蟶ｰ遒ｺ隱榊ｯｾ雎｡縺ｫ縺吶ｋ縲・|
1. Windows 縺ｧ縺ｯ縲訓ATH 縺ｫ縺ゅｋ縲阪□縺代〒縺ｯ荳榊香蛻・〒縲～spawn` 縺ｮ螳溯｡悟ｽ｢蠑丞ｷｮ縺ｾ縺ｧ隕九ｋ蠢・ｦ√′縺ゅｋ縲・2. `initialize` 縺ｯ繧ｿ繧､繝�繧｢繧ｦ繝医□縺代〒縺ｪ縺上∝ｿ懃ｭ斐せ繧ｭ繝ｼ繝樔ｸ榊ｙ縺ｧ繧ゆｺ梧ｮｵ逶ｮ縺ｮ髫懷ｮｳ繧定ｵｷ縺薙☆縺溘ａ縲∬ｵｷ蜍輔→蠢懃ｭ斐・荳｡譁ｹ繧貞酔譎ゅ↓讀懆ｨｼ縺吶ｋ縲・3. 譌｢蟄倥Λ繝・ヱ繝ｼ (`codex.cmd`) 繧呈ｴｻ縺九☆諡｡蠑ｵ縺ｮ譁ｹ縺後∝挨邉ｻ邨ｱ縺ｮ襍ｷ蜍慕ｵ瑚ｷｯ繧貞｢励ｄ縺吶ｈ繧雁ｮ牙・縺ｫ蟆主・縺ｧ縺阪ｋ縲・## INC-020: Gmail priority backfill container path was unstable on the mini PC
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | A manual priority backfill run for `2026-01-01` onward failed first with `returncode 137` even after reducing the month scope, while host-side Gmail incremental sync for the same query completed successfully. |
| **Impact** | Historical Gmail ingestion was not progressing beyond recent incremental sync, so older mail from January 2026 onward was not being backfilled continuously. |
| **Root Cause (5 Why)** | **Why1**: `run_priority_gmail_backfill.py` executed Gmail indexing inside the gateway container via `docker exec`. **Why2**: On this mini PC, that container backfill path was unstable and the process was killed with exit `137` before completing a month-sized chunk. **Why3**: The daemon had been restarted with `--skip-full-backfill`, so the unstable full-backfill path stayed bypassed and historical ingestion never resumed. **Why4**: The original backfill implementation used a heavier execution path than the already-stable host-side temp-DB promotion flow used by `host_gmail_incremental_sync.py`. **Why5**: The system lacked a bounded, host-side historical backfill path that reused the proven safe SQLite promotion pattern. |
| **Fix** | Switched `data/workspace/run_priority_gmail_backfill.py` from container execution to the host-side temp-DB promotion pattern, added bounded CLI args (`--start-date`, `--end-date`, `--max-messages-per-chunk`), reduced the default monthly backfill chunk to `500`, and removed `--skip-full-backfill` from `data/workspace/email_continuous_watchdog.py` so restarted daemons can resume historical backfill. |
| **Files** | `data/workspace/run_priority_gmail_backfill.py`, `data/workspace/email_continuous_watchdog.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python data/workspace/run_priority_gmail_backfill.py --start-date 2026-01-01 --end-date 2026-01-31 --max-messages-per-chunk 500` completed with `returncode 0`; January chunk result was `candidates=500`, `indexed=160`, `skipped=340`, `errors=0`. Direct host sync for the same query also succeeded earlier with `indexed=411`, `skipped=89`, `errors=0`. |
| **Lessons Learned** | For long-running Gmail backfills on this mini PC, reuse the host-side temp SQLite promotion path that already proved stable. Prefer bounded month or date windows before re-enabling unattended historical catch-up. |
| **Prevention** | Keep full backfill chunk sizes bounded, preserve lock-based serialization with `EmailDbLock`, and validate backfill changes with a single-month run before allowing unattended daemon recovery to trigger them. |
## INC-021: Blacklisted Gmail messages were still stored in `emails`
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | Review of the Gmail ingest flow showed that blacklist and newsletter filters only affected task extraction and did not prevent blacklisted messages from being written into `emails` and SQLite FTS. |
| **Impact** | Newsletter and blocked notification mail still consumed SQLite rows, FTS space, and downstream processing time even when they were excluded from `tasks`. |
| **Root Cause (5 Why)** | **Why1**: `index_gmail()` fetched and parsed Gmail messages, then always called `upsert_record()`. **Why2**: The sender filter file was only consulted inside `looks_like_task()`. **Why3**: `looks_like_task()` runs after the email row is already inserted, during task extraction. **Why4**: The system optimized task quality but not storage hygiene. **Why5**: There was no pre-storage Gmail filter step that reused the existing blacklist, newsletter, and whitelist logic. |
| **Fix** | Added a Gmail pre-storage filter in `data/workspace/email_search_index.py` so blacklisted and newsletter messages are skipped before insertion into `emails`, and exposed `skipped_by_filter` in the Gmail ingest summary. Added `email ingest watchdog restart` to `data/workspace/email_rag_sender_filters.json` so watchdog restart notifications are dropped before DB insertion. |
| **Files** | `data/workspace/email_search_index.py`, `data/workspace/email_rag_sender_filters.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | Static validation via `python -m py_compile data/workspace/email_search_index.py`. Runtime Gmail summaries now include `skipped_by_filter`, enabling direct observation of pre-storage blacklist filtering in future sync cycles. |
| **Lessons Learned** | On this mini PC, blacklist and newsletter rules should be applied as early as possible to reduce DB growth and FTS churn, not only at task extraction time. |
| **Prevention** | Keep sender and content filters shared between task classification and pre-storage gating, and include skip counters in operational status so filter effectiveness is visible without inspecting the DB manually. |
## INC-022: Continuous patrol missed local API outages and user-intent drift
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | User reported that local APIs such as `email_blacklist_hub` often fell unnoticed, and earlier Gmail ingest drift had shown that patrols were checking heartbeat files without fully validating whether user-requested behavior was still being achieved. |
| **Impact** | Local tools could be down while dashboards still looked broadly healthy, and user-requested behaviors such as January 2026 onward Gmail backfill or blacklist effectiveness observability could drift without prompt correction. |
| **Root Cause (5 Why)** | **Why1**: `continuous_system_improvement.py` focused on watchdog freshness and status JSONs, but not on direct local API reachability. **Why2**: `email_blacklist_hub` had a start script, yet neither `continuous_system_improvement.py` nor `auto_repair_allowed.py` monitored or restarted it. **Why3**: Patrol logic did not audit contract-level expectations such as 窶廨mail daemon must not run with `--skip-full-backfill`窶・or 窶彷ilter telemetry must remain visible.窶・**Why4**: `data/workspace` resolves through the `E:` workspace path on this machine, so repo-root discovery based only on `__file__.resolve()` could point start actions at non-existent `E:\scripts\...` paths. **Why5**: The patrol layer had grown around component heartbeat checks, but not around user-intent contracts and mixed-drive path reality on this mini PC. |
| **Fix** | Extended `data/workspace/continuous_system_improvement.py` to probe `email_blacklist_hub` API endpoints directly, verify Gmail backfill drift and filter telemetry, and expose those checks in summary/status output. Extended `data/workspace/auto_repair_allowed.py` to restart `email_blacklist_hub` when stale or missing. Added repo-root fallback resolution in both scripts so start actions use the actual repo `scripts/` directory even when `data/workspace` resolves through `E:`. Restarted `email_blacklist_hub` and re-ran the patrol until summary showed the API reachable and `skipped_by_filter` visible. |
| **Files** | `data/workspace/continuous_system_improvement.py`, `data/workspace/auto_repair_allowed.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/continuous_system_improvement.py data/workspace/auto_repair_allowed.py` passed. `http://127.0.0.1:8791/api/email-blacklist/config` returned live JSON again. `python data/workspace/host_gmail_incremental_sync.py --gmail-max-messages 5 --gmail-fallback-days 1` completed with `skipped_by_filter=2`. `data/workspace/continuous_system_improvement_status.json` at `2026-04-12 07:12:58 JST` showed `Email blacklist hub API is reachable`, `Historical Gmail backfill still targets January 2026 onward`, and `Gmail filter telemetry is visible in ingest summaries`. |
| **Lessons Learned** | Heartbeat files are necessary but not sufficient. On this environment, patrols must verify API endpoints and a small set of explicit user-intent contracts, not just whether a process exists. |
| **Prevention** | Keep critical local APIs in the patrol catalog, keep at least one observable metric for each user-facing optimization (such as `skipped_by_filter`), and resolve repo-root paths defensively whenever workspace files may be mirrored onto another drive. |
## INC-023: Email Search API was not supervised and degraded the portal experience
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | User reported that `http://localhost:8088/apps/email_search/` looked down during a broader mini PC slowdown check. Investigation showed the portal page itself was reachable, but its backend API on `127.0.0.1:8792` was not running. |
| **Impact** | The Email Search UI loaded from the portal but could not return stats or search results, so it appeared broken. The system also lacked automatic restart for that API, making the failure recur silently after process loss. |
| **Root Cause (5 Why)** | **Why1**: `apps/email_search/index.html` depends on `email_search_api.py` at `127.0.0.1:8792`. **Why2**: The API had no dedicated Windows start script or watchdog integration. **Why3**: `continuous_system_improvement.py` and `auto_repair_allowed.py` originally monitored other local APIs but not Email Search. **Why4**: The mini PC slowdown symptoms prompted a check of background activity, revealing that watchdog cadence was moderate while the heavier pressure came from `Memory Compression`, `vmmemWSL`, Docker/WSL workloads, and VS Code processes. **Why5**: Service supervision coverage had focused on Gmail, Docker UI, and Blacklist Hub first, leaving Email Search outside the local API patrol catalog. |
| **Fix** | Added `scripts/start_email_search_api.ps1` to start and health-check `data/workspace/email_search_api.py`. Extended `data/workspace/continuous_system_improvement.py` to probe `http://127.0.0.1:8792/api/stats` and surface Email Search health in patrol summaries. Extended `data/workspace/auto_repair_allowed.py` to restart Email Search API when the process is missing or the API probe fails. Started the API and confirmed the portal backend was serving again. |
| **Files** | `scripts/start_email_search_api.ps1`, `data/workspace/continuous_system_improvement.py`, `data/workspace/auto_repair_allowed.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/continuous_system_improvement.py data/workspace/auto_repair_allowed.py data/workspace/email_search_api.py` passed. `http://127.0.0.1:8792/api/stats` returned JSON with `total_emails=23212` and `total_tasks=9172`. `data/workspace/continuous_system_improvement_status.json` showed `Email search API is reachable`. |
| **Lessons Learned** | For portal apps backed by local host APIs, supervising only the static UI path is not enough. The host API must be in the patrol catalog with a concrete health probe. |
| **Prevention** | Keep each portal app窶冱 host API paired with a start script and patrol probe, and treat UI reachability and backend reachability as separate checks. |

## INC-024: `minipc_optimizer` 縺・mini PC 縺ｮ螳溽腸蠅・〒 Lite 蛛懈ｭ｢縺ｫ螟ｱ謨励＠縺ｦ縺・◆

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 07:32 JST |
| **Detection** | User approved stopping safe background services to lighten the mini PC. `python data/workspace/minipc_optimizer.py apply-lite` first failed with `open E:\\clawstack_v2\\docker-compose.yml` and then `no such service: infinity`, even though candidate containers were visibly running. |
| **Impact** | The lightweight-mode harness could report heavy candidates but could not actually stop them on this machine, so memory-heavy optional services stayed online and the user-facing slowdown would persist longer than necessary. |
| **Root Cause (5 Why)** | **Why1**: `minipc_optimizer.py` derived `ROOT` from `Path(__file__).resolve()`, which can resolve through the `E:` workspace mirror on this mini PC. **Why2**: That made the compose path point to a non-existent `E:\\clawstack_v2\\docker-compose.yml` instead of the real repo on `D:`. **Why3**: After fixing the root, the harness still used `docker compose stop <service>`, assuming guessed service names exactly matched compose service ids. **Why4**: At least one running container (`clawstack-unified-infinity-1`) did not map cleanly enough for compose-stop by guessed service name, causing `no such service`. **Why5**: The optimizer had been designed around compose topology, but this mini PC now has mixed-drive path reality and practical container-name truth that are more reliable for emergency lightweight actions. |
| **Fix** | Updated `data/workspace/minipc_optimizer.py` to resolve the repo root by searching for the actual repo containing `clawstack_v2/docker-compose.yml` and `data/workspace`, falling back only if needed. Reworked Lite stopping to target currently running container names via `docker stop` instead of `docker compose stop`, so optional services can be stopped even when compose service ids drift from guessed names. |
| **Files** | `data/workspace/minipc_optimizer.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/minipc_optimizer.py` passed. `python data/workspace/minipc_optimizer.py apply-lite` returned `changed=true` and stopped 21 optional containers including `infinity`, `clickhouse`, `paperless`, `docling`, `metabase`, `stirling_pdf`, `portainer`, and `uptime-kuma`. A follow-up `python data/workspace/minipc_optimizer.py status` reported `heavyRunningCandidates=[]`, and `docker ps` no longer listed those optional services as running. |
| **Lessons Learned** | On this machine, host-side harnesses should prefer runtime-truth checks over inferred compose metadata when doing safe operational reductions. Mixed-drive path resolution and partial compose drift are normal enough that emergency controls should degrade gracefully. |
| **Prevention** | Reuse repo-root fallback logic in every host harness that launches or stops services, and prefer container-name based safe-stop flows for Lite mode unless a strong reason exists to require compose service ids. |

## INC-025: Gateway memory bloat was caused by duplicate `ingest_watchdog.py` processes and the harness lacked a full live inventory

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 21:12 JST |
| **Detection** | During mini PC slowdown analysis, `docker stats` showed `clawstack-unified-clawdbot-gateway-1` consuming about `4.8 GiB` RSS. Inspecting processes inside the container revealed hundreds of duplicate `python3 /home/node/clawd/ingest_watchdog.py` instances. At the same time, the AI Engineering Harness page did not yet expose a complete host API and major Docker service inventory, which made the drift harder to see quickly. |
| **Impact** | The gateway container consumed several GiB of memory, increasing overall pressure on `vmmemWSL` and host memory compression, and the existing dashboard did not clearly show which APIs or services were up, down, or intentionally stopped. |
| **Root Cause (5 Why)** | **Why1**: `paperless_rag_watchdog.py` only treated 窶從o ingest process窶・as unhealthy and did not detect duplicate `ingest_watchdog.py` processes. **Why2**: Its restart flow mainly relied on a single pidfile-oriented path, so stale or multiplied watchdog processes could survive while new ones were launched. **Why3**: Repeated repair attempts over time allowed duplicate `ingest_watchdog.py` processes to accumulate inside the gateway container. **Why4**: `continuous_system_improvement.py` summarized many patrol signals but did not yet collect a single inventory of host APIs, key Docker services, and gateway ingest watchdog counts. **Why5**: Operational observability had evolved around individual status files rather than a compact live inventory tied to the user-facing Harness card. |
| **Fix** | Updated `data/workspace/paperless_rag_watchdog.py` to count running `ingest_watchdog.py` processes, mark duplicate counts as unhealthy, and restart by killing all matching ingest watchdog processes before relaunching a single one. Updated `data/workspace/continuous_system_improvement.py` to collect `hostApiInventory`, `serviceInventory`, and `gatewayIngestWatchdogCount`, and to schedule `run_paperless_rag_watchdog` when duplicate gateway ingest processes are detected. Expanded `data/workspace/apps/ai_engineering_harness_status/index.html` to show the gateway ingest watchdog count, a full Host APIs panel, and a Major Docker Services panel. Restarted both the Windows `paperless_rag_watchdog.py` and `continuous_system_improvement.py` background patrols so the new logic is active. Manually collapsed duplicate gateway ingest watchdog processes back to a single running process. |
| **Files** | `data/workspace/paperless_rag_watchdog.py`, `data/workspace/continuous_system_improvement.py`, `data/workspace/apps/ai_engineering_harness_status/index.html`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/paperless_rag_watchdog.py data/workspace/continuous_system_improvement.py` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc 'ps -ef | grep ingest_watchdog.py | grep -v grep | wc -l'` returned `1` after cleanup. `docker stats` dropped gateway memory from about `4.8 GiB` to about `580 MiB`. `python data/workspace/continuous_system_improvement.py --once` produced `continuous_system_improvement_status.json` with `context.hostApiInventory`, `context.serviceInventory`, and `context.gatewayIngestWatchdogCount`, and the status summary now reports `Gateway ingest watchdog process count is healthy` with `processes=1`. |
| **Lessons Learned** | For long-running gateway sidecars, 窶徘rocess exists窶・is not a sufficient health test. The harness must detect multiplicity, not just absence. Operational cards are much more useful when they display both health summaries and the current live inventory that explains those summaries. |
| **Prevention** | Keep duplicate-process counts as first-class patrol signals, restart Windows patrol daemons after harness code changes, and expose the up/down state of major APIs and services on the Harness page so silent drift is visible before memory bloat becomes user-visible. |

## INC-026: Paperless ingest stopped because Paperless was offline and the gateway used a stale direct token path

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 22:02 JST |
| **Detection** | User requested Paperless ingest recovery after investigation showed repeated `401 Unauthorized` in `/home/node/clawd/ingest_watchdog.log`, stale `paperless_rag_watchdog` warnings, and `clawstack-unified-paperless-1` stopped with `Exited (137)`. |
| **Impact** | Paperless document ingestion into `universal_knowledge` was no longer progressing, watchdogs kept trying to revive the ingest loop, and the mini PC carried extra background churn without actually indexing new Paperless documents. |
| **Root Cause (5 Why)** | **Why1**: The Paperless container itself was not running, so the ingest path was intermittently unreachable. **Why2**: Even when Paperless was available again, `data/workspace/ingest_watchdog.py` still used a hard-coded legacy API token and direct `http://paperless:8000` target. **Why3**: That legacy token was no longer valid for the current Paperless API, causing repeated `401 Unauthorized`. **Why4**: On this mini PC, the gateway could successfully authenticate through `http://host.docker.internal:8000`, while the direct container alias path returned `Invalid token`, so the old fixed endpoint was no longer the reliable route. **Why5**: Paperless ingest credentials and route selection had been embedded in scripts instead of being kept in one host-editable operational config. |
| **Fix** | Restarted `clawstack-unified-paperless-1`, verified the Paperless API on `127.0.0.1:8000`, generated a fresh API token via `/api/token/`, and moved Paperless ingest settings into `data/workspace/paperless_ingest_config.json`. Updated `data/workspace/ingest_watchdog.py`, `data/workspace/requeue_recent_paperless_docs.py`, and `data/workspace/audit_paperless_ingest_alignment.py` to consume that config instead of a hard-coded token. Switched the gateway ingest route to `http://host.docker.internal:8000`, updated `paperless_rag_watchdog.py` to count only real Python ingest processes, and reran the Paperless audit using host-side fallbacks. |
| **Files** | `data/workspace/paperless_ingest_config.json`, `data/workspace/ingest_watchdog.py`, `data/workspace/requeue_recent_paperless_docs.py`, `data/workspace/audit_paperless_ingest_alignment.py`, `data/workspace/paperless_rag_watchdog.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `docker start clawstack-unified-paperless-1` brought Paperless back to `Up ... (healthy)`. `POST http://127.0.0.1:8000/api/token/` with `admin/admin` returned a fresh token. From inside the gateway, `requests.get('http://host.docker.internal:8000/api/documents/?page_size=1', headers={'Authorization': 'Token ...'})` returned `200`, and importing `ingest_watchdog.py` inside the gateway showed `PAPERLESS_URL=http://host.docker.internal:8000`. `paperless_rag_watchdog_status.json` then reported `stage=healthy`, `ingestAlive=true`, `ingestProcessCount=1`. `python data/workspace/audit_paperless_ingest_alignment.py --recent-limit 10` completed with `status=healthy` and no missing recent documents. |
| **Lessons Learned** | For Paperless on this mini PC, the stable path is not just 窶彡ontainer-to-container by service name窶・ Authentication and reachability can diverge between the direct container alias and the host-exposed route, so the operational config needs an explicit chosen endpoint. |
| **Prevention** | Keep Paperless ingest token and base URL in a dedicated workspace config file, avoid hard-coded long-lived tokens in scripts, and validate both 窶廣PI auth works窶・and 窶彗udit sees recent docs窶・after any Paperless restart or Lite-mode service reduction. |

## INC-027: Patrols needed to treat `401/403` as outage-equivalent and semi-automate Paperless token renewal

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 22:14 JST |
| **Detection** | User requested that `401/403` responses be treated as patrol failures rather than mere 窶廣PI responded窶・signals, and asked for Paperless-style token reissue to be semi-automated. Existing API inventory cards could show up/down, but auth drift still required manual digging. |
| **Impact** | An API could be effectively unusable while still appearing reachable, and token-backed integrations like Paperless ingest could silently degrade until a human manually reissued credentials and updated config. |
| **Root Cause (5 Why)** | **Why1**: `continuous_system_improvement.py` treated successful TCP/HTTP response handling and authentication validity as the same concept. **Why2**: `401/403` were not being elevated into explicit auth-failure patrol weaknesses. **Why3**: Paperless ingest token refresh existed only as a manual recovery pattern from the previous incident, not as a reusable harness action. **Why4**: `auto_repair_allowed.py` did not have a direct rule for 窶彗uth is stale but service is otherwise reachable窶・ **Why5**: Operational hardening had focused first on process recovery and freshness, leaving auth-contract drift as a separate manual concern. |
| **Fix** | Extended `data/workspace/continuous_system_improvement.py` so HTTP probes classify `401/403` as `authFailure`, expose that on `hostApiInventory`, and raise explicit weaknesses such as `paperless_ingest_auth`. Added `refresh_paperless_ingest_token.py` to mint a fresh Paperless API token from the running Paperless container credentials and update `paperless_ingest_config.json`. Integrated that refresh action into both `continuous_system_improvement.py` and `auto_repair_allowed.py`. Updated `data/workspace/apps/ai_engineering_harness_status/index.html` so host API rows show `AUTH 401/403` instead of looking like generic connectivity failures. Also aligned gateway ingest-process counting in `continuous_system_improvement.py` with `pgrep` so the dashboard does not overcount wrapper shells. |
| **Files** | `data/workspace/continuous_system_improvement.py`, `data/workspace/auto_repair_allowed.py`, `data/workspace/refresh_paperless_ingest_token.py`, `data/workspace/apps/ai_engineering_harness_status/index.html`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/continuous_system_improvement.py data/workspace/auto_repair_allowed.py data/workspace/refresh_paperless_ingest_token.py` passed. `python data/workspace/refresh_paperless_ingest_token.py` completed and wrote `paperless_token_refresh_status.json`. A fresh `continuous_system_improvement.py --once` run showed `Paperless ingest API authentication is valid` and included `paperless_ingest_auth` in `hostApiInventory`. `auto_repair_allowed.py` completed with `paperless_token` rule evaluating `healthy`, confirming the new semi-automatic path is wired in. |
| **Lessons Learned** | For operations patrols, `reachable` is not enough. Authentication validity is part of availability when a user-facing workflow depends on it. |
| **Prevention** | Keep auth-backed probes separate from plain liveness checks, surface them on the portal card, and maintain one dedicated token-refresh harness per long-lived local integration that depends on renewable credentials. |

## INC-028: Auto-repair had stale target assumptions for scheduled reports and missed dead Paperless watchdogs

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 22:49 JST |
| **Detection** | A weakness review of the current mini PC patrol stack showed two avoidable blind spots: `auto_repair_allowed.py` still tried to run scheduled report sync through a non-existent `clawstack-unified-learning_engine-1` container, and it could mark `paperless_rag` healthy even when `paperless_rag_watchdog.py` itself was no longer running. |
| **Impact** | Scheduled-report repair attempts produced misleading `No such container` failures instead of the real underlying cause, and Paperless ingest supervision could silently degrade if the Windows watchdog died while the ingest heartbeat remained fresh for a while. |
| **Root Cause (5 Why)** | **Why1**: `auto_repair_allowed.py` had an old hard-coded `docker exec clawstack-unified-learning_engine-1 ...` command. **Why2**: The environment had moved to `wsl_native` and no longer guaranteed that container name or a container-based execution path for this task. **Why3**: The same script evaluated `paperless_rag` only from JSON freshness, not from the Windows watchdog process itself. **Why4**: That allowed a dead watchdog to be masked by still-fresh ingest heartbeat files. **Why5**: Repair logic had evolved around status files first, and some operational assumptions were not updated when the runtime topology changed. |
| **Fix** | Updated `data/workspace/auto_repair_allowed.py` so scheduled-report repair now executes the host-side `scheduled_report_search.py` directly instead of targeting the removed container name. Added an explicit process-presence check for `paperless_rag_watchdog.py` before declaring Paperless RAG healthy, so auto-repair can restart the watchdog when the Windows process is missing. |
| **Files** | `data/workspace/auto_repair_allowed.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/auto_repair_allowed.py` passed. A fresh `python data/workspace/auto_repair_allowed.py` run restarted `paperless_rag_watchdog.py` successfully and showed `scheduled_reports_sync` invoking the host-side script path instead of the removed container. The scheduled report sync still failed, but now with the true cause: upstream `n8n` API timeout, not a fake container-name mismatch. |
| **Lessons Learned** | Repair harnesses should point at the smallest stable execution surface available on the host, and liveness of a watchdog process must be checked separately from freshness of the child service it supervises. |
| **Prevention** | Prefer host-side script entry points over fragile container-name assumptions for maintenance jobs, and always combine `status freshness` with `process existence` when supervising watchdog-style services. |

## INC-029: Scheduled-report sync used the wrong n8n auth path and gateway ingest had multiple owners

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 23:25 JST |
| **Detection** | User requested root-cause investigation for `n8n timeout` and `gateway duplicate ingest`. The scheduled report repair path had stopped failing with a fake container-name error, but still timed out while probing `host.docker.internal:5679`. Separately, `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "ps -o pid,ppid,lstart,cmd -C python3 | grep ingest_watchdog.py"` showed a new `ingest_watchdog.py` process every ~5 minutes with `PPID 1`, confirming duplicate ownership. |
| **Impact** | Scheduled report sync could not read workflow executions reliably, so `scheduled_reports` stayed stale. Gateway memory and CPU were wasted by many duplicate `ingest_watchdog.py` processes, worsening mini PC responsiveness and risking repeated Paperless ingest churn. |
| **Root Cause (5 Why)** | **Why1**: `scheduled_report_search.py` only tried n8n public API-key routes and kept `host.docker.internal` in the host-side candidate set. **Why2**: On this machine, host access to `127.0.0.1:5679/rest/login` succeeds, but API-key access to `/api/v1` and `/rest` returns `401`, and `host.docker.internal:5679` can time out from the Windows host. **Why3**: The script had no login-cookie fallback even though other repo utilities already used `n8n-auth` cookies successfully. **Why4**: Gateway ingest was started by more than one control plane: container boot plus the active n8n workflow `Ingest Watchdog Supervisor`. **Why5**: Lifecycle ownership for `ingest_watchdog.py` was never reduced to one authoritative watchdog, so overlapping restart paths kept multiplying the process. |
| **Fix** | Updated `data/workspace/scheduled_report_search.py` to load `N8N_API_KEY` from env/`.env`, prefer localhost routes, and fall back to `POST /rest/login` with cached `n8n-auth` cookies when API-key auth returns `401/403`. Applied the same login fallback pattern to `data/workspace/create_scheduled_report_sync_workflow.py`. Updated `data/workspace/recreate_workflows.py` so the `Ingest Watchdog Supervisor` workflow is preserved but explicitly deactivated, with future re-runs keeping it inactive instead of re-enabling duplicate restarts. Clarified `data/state/entrypoint.sh` so host-side `paperless_rag_watchdog` is the intended restart owner. Then deactivated n8n workflow `VBQMPFGWSVtwy2Vy`, killed all real `ingest_watchdog.py` processes in the live gateway container, and relaunched a single instance. |
| **Files** | `data/workspace/scheduled_report_search.py`, `data/workspace/create_scheduled_report_sync_workflow.py`, `data/workspace/recreate_workflows.py`, `data/state/entrypoint.sh`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/scheduled_report_search.py data/workspace/create_scheduled_report_sync_workflow.py data/workspace/recreate_workflows.py` passed. Direct host login to `http://127.0.0.1:5679/rest/login` returned `200` and an `n8n-auth` cookie. `python data/workspace/scheduled_report_search.py sync --limit-executions 20` now completes successfully instead of timing out. `python data/workspace/recreate_workflows.py` reported `Ingest Watchdog Supervisor ... active=False`. After cleanup, `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "sleep 330; pgrep -fc '^python3 /home/node/clawd/ingest_watchdog.py$'"` returned `1`, proving the 5-minute duplicate loop stopped. |
| **Lessons Learned** | For n8n on this mini PC, host-maintenance scripts must prefer the same login-cookie path that already works for other local admin tools; API-key-only assumptions are brittle. For long-running sidecars, one process owner is a design rule, not just an implementation detail. |
| **Prevention** | Keep host-side n8n maintenance utilities on localhost-first login fallback, and keep only one authoritative restart path for gateway sidecars. When a workflow is retained only for historical reference, explicitly keep it deactivated in the workflow recreation script so future maintenance runs do not resurrect duplicate process loops. |

## INC-030: Outbound notifications relied on policy text more than code-level allowlist enforcement

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-13 06:12 JST |
| **Detection** | User requested a hard-force guard so no information could ever be sent outside their own Telegram and `y.suzuki.hk@gmail.com`. Review found that policy files already restricted outbound delivery, but multiple runtime send paths still relied on local constants or environment values instead of one fail-closed allowlist check. |
| **Impact** | A drifted environment variable, reused helper, or future sender script could have delivered notifications to an unintended Telegram chat or Gmail recipient even though the written policy prohibited it. |
| **Root Cause (5 Why)** | **Why1**: Outbound safety was documented in `data/workspace/AGENTS.md` and `email_ops_policy.json`, but not centralized in a shared runtime guard. **Why2**: Several scripts (`email_continuous_watchdog.py`, `run_email_rag_ingest_report.py`, `risk_notification.py`, `workflow_healer.py`, `inbox_watcher.py`, `scheduled_notify.py`, and Telegram bridge code) each constructed their own send calls. **Why3**: Most of those senders trusted embedded constants or env-derived values rather than validating the destination at send time. **Why4**: The AI Engineering Harness had no dedicated visibility card for outbound-delivery policy enforcement. **Why5**: Safety hardening had focused first on `draft_only` policy and specific Gmail helper scripts, but not on one shared fail-closed outbound guard across all active notification paths. |
| **Fix** | Added `data/workspace/outbound_delivery_guard.py` as a shared fail-closed allowlist module that only permits Gmail delivery to `y.suzuki.hk@gmail.com` and Telegram delivery to chat `8173025084`, while recording policy status in `outbound_delivery_guard_status.json`. Wired the guard into `data/workspace/email_continuous_watchdog.py`, `data/workspace/run_email_rag_ingest_report.py`, `data/workspace/risk_notification.py`, `data/workspace/workflow_healer.py`, `data/workspace/inbox_watcher.py`, and `data/workspace/scripts/scheduled_notify.py`. Hardened `scripts/telegram_fast_bridge.js` to block non-allowlisted Telegram chat IDs at send/edit time. Extended `data/workspace/continuous_system_improvement.py` and `data/workspace/apps/ai_engineering_harness_status/index.html` so the Harness now shows an `Outbound Guard` card and raises a weakness if the enforced Gmail or Telegram targets drift. |
| **Files** | `data/workspace/outbound_delivery_guard.py`, `data/workspace/email_continuous_watchdog.py`, `data/workspace/run_email_rag_ingest_report.py`, `data/workspace/risk_notification.py`, `data/workspace/workflow_healer.py`, `data/workspace/inbox_watcher.py`, `data/workspace/scripts/scheduled_notify.py`, `scripts/telegram_fast_bridge.js`, `data/workspace/continuous_system_improvement.py`, `data/workspace/apps/ai_engineering_harness_status/index.html`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile` passed for all changed Python files, and `node --check scripts/telegram_fast_bridge.js` passed. `outbound_delivery_guard_status.json` now shows `policyActive=true`, `allowedGmailRecipient=y.suzuki.hk@gmail.com`, and `allowedTelegramChatId=8173025084`. A fresh `continuous_system_improvement_status.json` run now includes the strength `Outbound delivery allowlist guard is enforced`, and the Harness page can render the new `Outbound Guard` card. |
| **Lessons Learned** | Written safety policy is not enough for outbound channels. Telegram and Gmail delivery must both be guarded by one runtime allowlist that fails closed. |
| **Prevention** | Require every future outbound sender to import the shared guard before network delivery, keep the Harness card visible so drift is obvious, and treat any non-allowlisted destination as a hard error instead of a warning. |

## INC-031: Telegram bridge stopped replying because runtime ownership drifted away from the supervised implementation

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-13 |
| **Detection** | User reported that Telegram messages no longer received replies after a mini PC freeze/slowdown period. Investigation found the last successful Telegram reply recorded at `2026-04-13 08:10:26 JST`, while runtime status later pointed to a live `powershell.exe -File scripts\\telegram_fast_bridge_v3.ps1` process instead of the monitored `node scripts\\telegram_fast_bridge.js` bridge. |
| **Impact** | Telegram could silently stop behaving as expected while the repo still contained a newer hardened bridge implementation. Recovery was unreliable because the watchdog, startup task, and active runtime were not aligned on one canonical process owner. |
| **Root Cause (5 Why)** | **Why1**: Multiple Telegram bridge implementations (`telegram_fast_bridge.js`, `telegram_fast_bridge.ps1`, `telegram_fast_bridge_v2.ps1`, `telegram_fast_bridge_v3.ps1`) coexisted. **Why2**: The active runtime had drifted to `telegram_fast_bridge_v3.ps1`, while the startup script and recent hardening targeted `telegram_fast_bridge.js`. **Why3**: The watchdog only checked pid/status freshness and did not verify that the running process actually matched the canonical implementation. **Why4**: The Windows Startup folder and scheduled-task setup did not enforce one authoritative owner end to end, so an older/manual PowerShell bridge could survive outside the intended recovery path. **Why5**: Operational supervision focused on liveness files first, but not on implementation drift between legacy and canonical Telegram bridge entrypoints. |
| **Fix** | Updated `scripts/start_telegram_fast_bridge.ps1` to stop all repo-local Telegram bridge variants before starting the canonical `node scripts/telegram_fast_bridge.js` process, and to log startup actions in `data/state/telegram_fast/startup.log`. Updated `scripts/watchdog_telegram_bridge.ps1` to detect legacy PowerShell bridge variants, duplicate bridge processes, and status-pid mismatch, then restart only the canonical JS bridge. Updated `scripts/check_telegram_fast_bridge.ps1` so diagnostics now show the actual bridge command line and implementation type. Updated `scripts/install_telegram_fast_bridge_startup.ps1` so watchdog installation and login-time startup are handled together, with Windows Startup-folder fallback if scheduled-task creation is denied. |
| **Files** | `scripts/start_telegram_fast_bridge.ps1`, `scripts/watchdog_telegram_bridge.ps1`, `scripts/check_telegram_fast_bridge.ps1`, `scripts/install_telegram_fast_bridge_startup.ps1`, `docs/INCIDENT_LOG.md` |
| **Verification** | `powershell -ExecutionPolicy Bypass -File scripts/install_telegram_fast_bridge_startup.ps1` ensured watchdog installation and login-start fallback. `powershell -ExecutionPolicy Bypass -File scripts/start_telegram_fast_bridge.ps1` stopped the drifted PowerShell bridge and launched the canonical Node bridge. `powershell -ExecutionPolicy Bypass -File scripts/check_telegram_fast_bridge.ps1` now reports the live `telegram_fast_bridge.js` command line. `node --check scripts/telegram_fast_bridge.js` passed, and `watchdog_telegram_bridge.ps1` now restarts when a legacy PowerShell implementation is detected. |
| **Lessons Learned** | For long-poll bots, "a process exists" is not enough. The harness must verify that the supervised implementation is the one actually consuming updates. |
| **Prevention** | Keep one canonical Telegram bridge owner, make watchdogs validate command-line identity in addition to pid freshness, and reinstall startup/watchdog tasks together whenever the Telegram runtime path changes. |

## INC-032: Workflow Healer crashed after n8n execution-list API shape drift and always returned a failure exit code

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:04 JST |
| **Detection** | User reported that `Workflow Healer` had crashed. Investigation of `/home/node/clawd/workflow_healer.log` showed repeated `FATAL: 0` every 15 minutes from `2026-04-13 21:15 JST` onward. A traced manual run inside `clawstack-unified-clawdbot-gateway-1` reproduced `KeyError: 0` at `latest_status = execs[0].get("status", "")`. |
| **Impact** | The `P017 Workflow Self-Healer` n8n job was running on schedule but failing before it could inspect or repair any workflow. Because the script also unconditionally ended with `sys.exit(1)`, even healthy runs would still be marked as failed by n8n. |
| **Root Cause (5 Why)** | **Why1**: `workflow_healer.py` assumed `/rest/executions` returned a plain list under `data`, and indexed `execs[0]`. **Why2**: The current n8n API shape returns execution rows under `data.results`, so `get_recent_executions()` handed back a dict instead of a list. **Why3**: The script had no response-normalization helper for API shape drift across n8n versions. **Why4**: Runtime logging only recorded `FATAL: 0`, because the raised `KeyError(0)` was stringified without a traceback. **Why5**: The CLI epilogue had also been left with an unconditional `sys.exit(1)`, so successful runs were not clearly distinguishable from real crashes in scheduler results. |
| **Fix** | Updated `data/workspace/workflow_healer.py` to normalize n8n list payloads via `extract_n8n_items()`, covering both legacy `data: [...]` and current `data.results: [...]` execution responses. Wired that normalization into `get_active_workflows()`, `get_recent_executions()`, and `get_execution_error()`. Also added traceback logging on fatal errors and corrected the CLI exit path so `--dry-run` and healthy runtime executions return exit code `0`, while true exceptions return `1`. |
| **Files** | `data/workspace/workflow_healer.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/workflow_healer.py` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc 'cd /home/node/clawd && python3 workflow_healer.py --dry-run'` reported `Active workflows: 5` with all monitored workflows healthy. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc 'cd /home/node/clawd && python3 workflow_healer.py; code=$?; echo EXIT=$code'` completed with `=== Workflow Healer done ===` and `EXIT=0`. The live log no longer ends in `FATAL: 0` after the fix. |
| **Lessons Learned** | n8n maintenance scripts need one local normalization layer for REST payloads instead of baking in a single response shape. Exit codes matter as much as business logic in scheduled jobs, because a scheduler can only distinguish healthy from broken through process termination status. |
| **Prevention** | Reuse response-normalization helpers for other n8n maintenance scripts, log tracebacks for unexpected exceptions instead of only exception strings, and treat `exit 0 on healthy / exit 1 on fault` as a required check whenever a script is run under n8n `Execute Command`. |

## INC-033: Telegram bridge treated DB-search requests as generic email chat instead of explicit local DB lookup

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:32 JST |
| **Detection** | User reported that a Telegram request to search the mini PC's DB did not work. Review of `data/state/telegram_fast/harness_status.json` showed the latest request had been routed as `email`, and the bridge replied with a generic Gmail capability explanation instead of returning local DB search results. |
| **Impact** | Telegram users could ask for a DB search and receive a misleading explanatory reply rather than actual results from the local indexed stores, making the mini PC appear unable to search its own data even though the underlying SQLite search backend was healthy. |
| **Root Cause (5 Why)** | **Why1**: `scripts/telegram_fast_bridge.js` had no dedicated `db` route. **Why2**: Messages containing words like `gmail` or `mail` were classified directly as `email`, even when the user's intent was "search the DB". **Why3**: The `email` path used a general prompt-building flow that can answer conversationally, not a fail-closed structured DB response. **Why4**: Telegram routing relied mainly on broad intent regexes rather than an explicit "local DB lookup" override. **Why5**: The bridge design had evolved around email/task/report assistants, but not around a user-facing "DB讀懃ｴ｢縺励※" command family. |
| **Fix** | Updated `scripts/telegram_fast_bridge.js` to recognize explicit DB-search wording via `isDatabaseIntent()`, prioritize a new `db` route in `classifyRoute()`, and answer through `generateDatabaseReply()` that queries local task, report, and email contexts directly and returns structured DB-hit summaries. Restarted the canonical Telegram bridge via `scripts/start_telegram_fast_bridge.ps1` so the new routing logic is live. |
| **Files** | `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `node --check scripts/telegram_fast_bridge.js` passed. `python3 /home/node/clawd/email_search_query.py --db /home/node/clawd/email_search.db context 'gmail 隱ｭ縺ｿ蜿悶ｋ 縺ｧ縺阪∪縺吶°' --limit 3` returned valid JSON results from the live SQLite DB inside `clawstack-unified-clawdbot-gateway-1`, confirming the backend was healthy. `powershell -ExecutionPolicy Bypass -File scripts/start_telegram_fast_bridge.ps1` restarted the canonical Node bridge at `2026-04-14 07:31:57 JST`. End-to-end Telegram confirmation still requires one fresh user message after this routing fix. |
| **Lessons Learned** | For chat-driven ops tools, "search-capable backend exists" is not enough. The conversational router needs an explicit intent for "search the local DB now" so capability explanations do not mask successful search backends. |
| **Prevention** | Keep explicit operational intents such as `DB讀懃ｴ｢`, `螻･豁ｴ讀懃ｴ｢`, and `繝｡繝ｼ繝ｫDB讀懃ｴ｢` ahead of softer conversational email intents, and prefer structured fail-closed summaries for search requests instead of letting them fall through to open-ended model prompting. |

## INC-034: Relative due-date parsing missed `譚･騾ｱ` / `譚･騾ｱ譛ｫ` and fell back to free-text task search

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:43 JST |
| **Detection** | User reported that asking Telegram for tasks due by next week returned obviously stale items from 2019-2020. Log review showed the Telegram bridge correctly routed `譚･騾ｱ譛ｫ縺ｾ縺ｧ縺檎ｴ肴悄縺ｮ讌ｭ蜍呎蕗縺医※縺上□縺輔＞` to `task`, but `email_search_query.py` returned `due_on=null`, `due_from=null`, and `due_to=null`, causing a plain text-match search instead of a due-date range filter. |
| **Impact** | Relative-date task queries such as `譚･騾ｱ縺ｾ縺ｧ`, `譚･騾ｱ譛ｫ縺ｾ縺ｧ`, and similar deadline requests could return unrelated historical tasks, making Telegram task-search answers unreliable for near-term planning. |
| **Root Cause (5 Why)** | **Why1**: `scripts/telegram_fast_bridge.js` successfully routed the user message to task search. **Why2**: `data/workspace/email_search_query.py` only recognized `莉頑律`, `譏取律`, `莉企ｱ`, and `莉頑怦` for due-date resolution. **Why3**: `譚･騾ｱ` and `譚･騾ｱ譛ｫ` were not mapped into a date window in `resolve_due_range()`. **Why4**: When no date window was found, task search fell back to term-based SQL matching. **Why5**: Relative-date coverage had grown incrementally around current-day and current-week use cases, but the next-week planning phrases used from Telegram had not been added to the parser. |
| **Fix** | Updated `data/workspace/email_search_query.py` so `RELATIVE_TERMS` includes `譚･騾ｱ`, `莉企ｱ譛ｫ`, and `譚･騾ｱ譛ｫ`, and `resolve_due_range()` now maps `莉企ｱ譛ｫ` to the current week window and `譚･騾ｱ` / `譚･騾ｱ譛ｫ` to the next week window. Synced the updated script into `clawstack-unified-clawdbot-gateway-1` at `/home/node/clawd/email_search_query.py`. |
| **Files** | `data/workspace/email_search_query.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/email_search_query.py` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "cd /home/node/clawd && python3 email_search_query.py --db /home/node/clawd/email_search.db tasks-context '譚･騾ｱ譛ｫ縺ｾ縺ｧ縺檎ｴ肴悄縺ｮ讌ｭ蜍呎蕗縺医※縺上□縺輔＞' --limit 5"` now returns `due_from=2026-04-20` and `due_to=2026-04-26`, with current 2026-dated items instead of 2019-2020 records. |
| **Lessons Learned** | Chat routing and DB health are only half the path. Relative-date parsers need explicit coverage for the phrases users actually use in operations, especially planning ranges like next week and next weekend. |
| **Prevention** | Extend relative-date parsing with a maintained set of operational Japanese phrases and add smoke checks for `莉頑律`, `莉企ｱ`, `莉企ｱ譛ｫ`, `譚･騾ｱ`, and `譚･騾ｱ譛ｫ` whenever task-search date logic changes. |

## INC-035: Telegram DB count requests fell through to generic RAG advice instead of returning a numeric count

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:49 JST |
| **Detection** | User reported another disappointing Telegram reply after sending `DB縺九ｉIATF髢｢騾｣縺ｮ雉・侭謨ｰ繧呈焚縺医※`. The latest bridge log showed `route=general`, `tier=rag`, and the reply was generic guidance about searching for `IATF`, rather than a counted result from the local DB. |
| **Impact** | Telegram could answer count-style DB requests with advice text instead of an actual number, making DB-backed operational questions feel unreliable even though the underlying SQLite store was healthy and queryable. |
| **Root Cause (5 Why)** | **Why1**: The bridge recognized some DB-search wording, but not the specific combination of `DB縺九ｉ ... 雉・侭謨ｰ繧呈焚縺医※`. **Why2**: That message therefore fell through to general classification, where `IATF` triggered the RAG path. **Why3**: The RAG path can summarize retrieved snippets, but it has no notion of total matching-document count. **Why4**: `email_search_query.py` had context and search commands, but no dedicated count command for Telegram to call. **Why5**: DB-search support had been expanded around retrieval and due-date queries first, while aggregate/count requests were still unimplemented. |
| **Fix** | Added `search-count` to `data/workspace/email_search_query.py`, backed by `count_search_rows()` using FTS count with LIKE fallback. Added `fetchEmailCount()` to `data/state/email_context_helper.js`. Updated `scripts/telegram_fast_bridge.js` so DB + IATF/material/count wording is forced onto the `db` route, and `generateDatabaseReply()` now returns a numeric count for count-style requests. Restarted the canonical Telegram bridge and synced the updated Python script into `clawstack-unified-clawdbot-gateway-1`. |
| **Files** | `data/workspace/email_search_query.py`, `data/state/email_context_helper.js`, `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/email_search_query.py` passed. `node --check scripts/telegram_fast_bridge.js` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "python3 /home/node/clawd/email_search_query.py --db /home/node/clawd/email_search.db search-count 'IATF 髢｢騾｣ 雉・侭'"` returned `result_count=1117`. `powershell -ExecutionPolicy Bypass -File scripts/start_telegram_fast_bridge.ps1` restarted the canonical bridge so the new route is live. |
| **Lessons Learned** | For chat ops, retrieval and aggregation are different capabilities. If users can ask "how many?", the bridge needs a dedicated count path instead of hoping a retrieval-oriented model route will infer aggregation correctly. |
| **Prevention** | Keep explicit patterns for `莉ｶ謨ｰ`, `菴穂ｻｶ`, `謨ｰ繧呈焚縺医※`, and similar aggregate queries ahead of generic RAG routing, and maintain one script-level count command so Telegram, CLI, and future dashboards can all reuse the same DB-count implementation. |

## INC-036: Telegram answered IATF document counts from model inference instead of DB truth and lost follow-up title context

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 08:12 JST |
| **Detection** | User reported that Telegram answered `IATF髢｢騾｣縺ｮ雉・侭縺ｯ菴穂ｻｶ縺ゅｊ縺ｾ縺吶°・歔 with `12莉ｶ`, and then answered `雉・侭蜷阪・菴輔〒縺吶°・歔 with only one fabricated-looking title. Log review showed the first message routed to `general` and `tier=rag`, not `db`, and the follow-up also routed to `general/simple`. |
| **Impact** | Telegram gave materially wrong inventory information for IATF-related materials, undercounting a large local corpus and failing to list representative titles from the real DB. This undermined trust in Telegram-based retrieval for local knowledge counts. |
| **Root Cause (5 Why)** | **Why1**: The bridge only forced `db` routing when the message explicitly contained DB-like wording. **Why2**: `IATF髢｢騾｣縺ｮ雉・侭縺ｯ菴穂ｻｶ縺ゅｊ縺ｾ縺吶°・歔 lacked `DB` but still semantically asked for a local count, so it fell through to general classification. **Why3**: General classification sent `IATF` questions into the RAG path, which is retrieval-oriented rather than count-oriented. **Why4**: The count response path did not persist the returned title list for the next follow-up turn. **Why5**: Telegram DB support had been implemented as one-shot answers first, without a lightweight local context memory for follow-up questions like `雉・侭蜷阪・・歔. |
| **Fix** | Updated `scripts/telegram_fast_bridge.js` so `IATF/ISO/QMS + 莉ｶ謨ｰ/雉・侭/謨ｰ` questions route directly to `db` even without the literal `DB` keyword. Extended `generateDatabaseReply()` to call the real `search-count` backend, include representative titles from `fetchEmailContext()`, and save those titles into `data/state/telegram_fast/last_db_context.json` for immediate follow-up questions such as `雉・侭蜷阪・菴輔〒縺吶°・歔. Restarted the canonical Telegram bridge after the change. |
| **Files** | `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `node --check scripts/telegram_fast_bridge.js` passed. The live DB backend reports `result_count=1118` for `IATF 髢｢騾｣ 雉・侭` via `python3 /home/node/clawd/email_search_query.py --db /home/node/clawd/email_search.db search-count 'IATF 髢｢騾｣ 雉・侭'`. Representative titles returned from the same DB search include `Re: 雉ｼ雋ｷ繝励Ο繧ｻ繧ｹ KPI縺ｫ縺､縺・※`, `繧ｰ繝ｫ繝ｼ繝励い繧ｫ繧ｦ繝ｳ繝・ IATF蜀・Κ逶｣譟ｻ蜩｡ "譖ｴ譁ｰ縺ｮ縺顔衍繧峨○`, and `Re: VDA縺ｫ縺､縺・※`, confirming that the local store contains far more than 12 items and multiple distinct titles. |
| **Lessons Learned** | For local-knowledge chat tools, "domain question" and "DB truth query" are not the same. Count and listing requests need to bypass generative shortcuts, and follow-up questions need lightweight state so users can ask naturally without repeating the full query every turn. |
| **Prevention** | Route `菴穂ｻｶ` / `莉ｶ謨ｰ` / `雉・侭蜷港 follow-ups to the DB layer by default when a recent DB context exists, and keep a short-lived local result cache for follow-up listing questions in Telegram. |

## INC-037: Telegram intent handling needed canonical normalization for varied Japanese expressions
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-14 |
| **逋ｺ隕区婿豕・* | User reported that Telegram replies still missed intent when the same request was phrased as `IATF髢｢騾｣縺ｮ雉・侭縺ｯ菴穂ｻｶ縺ゅｊ縺ｾ縺吶°・歔, `雉・侭蜷阪・菴輔〒縺吶°・歔, `譚･騾ｱ縺ｾ縺ｧ縺檎ｴ肴悄縺ｮ讌ｭ蜍呎蕗縺医※`, or `繝｡繝ｼ繝ｫDB縺ｧ蜿嶺ｿ｡縺励◆IATF縺ｮ雉・侭繧呈爾縺励※`. |
| **蠖ｱ髻ｿ遽・峇** | Telegram routing for local DB search, task search, and follow-up questions. Users could receive model-style replies or ambiguous fallbacks instead of the intended local search behavior. |
| **Root Cause (5 Why)** | **Why1**: Route selection depended on ad hoc regex branches added case by case. **Why2**: The same user intent could appear as count, list, follow-up, or search wording, but those variants were not normalized into a canonical intent bucket. **Why3**: Follow-up questions relied on a single cached title list, but the cache was only useful after some branches and not consistently preserved across all DB responses. **Why4**: The search layer was already capable, but the bridge did not enforce a stable `db_count` / `db_list` / `db_followup` / `task_due` style classification. **Why5**: The system had been optimized for individual fixes first, rather than a reusable intent normalization layer. |
| **Fix** | Reworked `scripts/telegram_fast_bridge.js` so user text is normalized with NFKC and compacted before routing. Added canonical intent helpers for DB count/list/follow-up, task due-date phrasing, report, email, and complaint intents. Updated `generateDatabaseReply()` to store and reuse recent titles for follow-up questions, and to keep DB count replies grounded in the local search backend. |
| **Files** | `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `node --check scripts/telegram_fast_bridge.js` passed after the change. The updated bridge now classifies the representative inputs above into the intended intent buckets in code review, and the previous `12莉ｶ` style inference path is no longer the DB count path for IATF material questions. |
| **Lessons Learned** | User phrasing must be treated as noisy input, not as a specification. The bridge needs a small number of canonical intents and short-lived context, rather than one-off regexes for each new wording. |
| **Prevention** | Keep expanding canonical intent buckets and shared normalization instead of adding isolated phrasing rules. When a new wording appears more than once, map it to an existing intent bucket first and only add a new bucket when the behavior is genuinely new. |

## INC-038: 2025 process monitoring measurement refresh failed because PDF directory check blocked Excel-only regeneration

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 10:34 JST |
| **Detection** | User reported that `http://localhost:3004/products/process_monitoring_measurement?year=2025` showed too many blank cells and did not reflect the Excel content. Investigation found `year_2025` in `db/process_monitoring_measurement.json` was still an array with only five monthly PDF items, even though `db/documents/繝励Ο繧ｻ繧ｹ縺ｮ逶｣隕悶・貂ｬ螳夊ｨ倬鹸_2025蟷ｴ.xls` already existed. |
| **Impact** | The 2025 process-monitoring page displayed incomplete or mostly empty content, so users could not rely on it as a faithful view of the registered Excel source. |
| **Root Cause (5 Why)** | **Why1**: `ProcessMonitoringMeasurementRefreshService.call` returned `PDF source directory was not found.` before doing any work if `/paperless_consume` was absent. **Why2**: That guard lived at the top of `call`, even though `refresh_year` could already rebuild 2025 from the local Excel file alone. **Why3**: As a result, Excel-only regeneration was impossible unless a PDF source directory happened to exist. **Why4**: The current JSON had never been switched from the older `year_2025` array format into the Excel-backed grid format. **Why5**: The refresh flow had been optimized around PDF fallback first, and the Excel-primary case was not allowed to complete without an unrelated PDF directory. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so the top-level `call` no longer fails early when the PDF source directory is missing. The PDF directory check now happens only inside the PDF fallback branch of `refresh_year`, after Excel has been checked first. Then regenerated 2025 from `db/documents/繝励Ο繧ｻ繧ｹ縺ｮ逶｣隕悶・貂ｬ螳夊ｨ倬鹸_2025蟷ｴ.xls`, which rewrote `db/process_monitoring_measurement.json` with the full grid data. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/db/process_monitoring_measurement.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` now returns `success=>true` and `updated_years=>[2025]`. The refreshed JSON now stores `year_2025` as a hash with `rows=96`, `nonblank_cells=1365`, and `source_file=繝励Ο繧ｻ繧ｹ縺ｮ逶｣隕悶・貂ｬ螳夊ｨ倬鹸_2025蟷ｴ.xls`. `http://localhost:3004/products/process_monitoring_measurement?year=2025` returns `200` after the refresh. |
| **Lessons Learned** | A fallback path should not block the primary path. If a year can be rebuilt from local Excel, the refresh flow must not require an unrelated PDF source directory first. |
| **Prevention** | Keep Excel regeneration independent from PDF availability, and prefer source-specific checks inside each branch instead of at the top of the whole refresh flow. Add a smoke check for 2025 refresh whenever this service changes. |

## INC-039: 2025 process monitoring measurement header layout broke because the refresh path lacked template widths and header rows

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 10:57 JST |
| **Detection** | User reported that `http://localhost:3004/products/process_monitoring_measurement?year=2025` still had a broken header after the 2025 data regeneration. A visual browser check with Playwright confirmed that the page was rendering, but the 2025 table header was compressed and misaligned compared with 2024. |
| **Impact** | The 2025 process-monitoring page was readable in the body but the top header region looked malformed, which made the page feel unreliable even though the data rows were present. |
| **Root Cause (5 Why)** | **Why1**: The 2025 refresh path wrote Excel-derived rows into `db/process_monitoring_measurement.json` without `column_widths`. **Why2**: The view uses `active_year[:column_widths]` to size the table, so a missing array falls back to browser auto-sizing. **Why3**: The Excel-only regeneration path also preserved the workbook's raw top rows, which did not visually match the stable 2024 template header. **Why4**: The earlier fix focused on getting the 2025 data and counts back, but not on preserving the 2024 visual baseline. **Why5**: The refresh service did not have a template-normalization step for the header region, so structurally valid data could still render with a broken-looking table top. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so Excel-backed refreshes now copy `column_widths` from the 2024 template and replace the first eight rows with the 2024 header rows before saving the 2025 payload. Re-ran `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` and verified the rendered page with Playwright screenshot after the fix. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/db/process_monitoring_measurement.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` returned `success=>true` and rewrote the JSON with the normalized 2025 payload. Playwright screenshot review of the authenticated `2025` page showed the header aligned to the 2024 visual baseline and the table no longer compressed at the top. `http://localhost:3004/products/process_monitoring_measurement?year=2025` continued to return `200`. |
| **Lessons Learned** | A structurally correct table can still look broken if the visual template is not preserved. Header rows and column widths are part of the contract, not just the data cells. |
| **Prevention** | Keep a template-normalization step for year-specific refreshes, and compare the rendered 2025 page against the 2024 visual baseline whenever the refresh pipeline changes. |

## INC-040: 2025 process monitoring measurement body rows were over-wrapped by long decimal values

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 11:05 JST |
| **Detection** | After visually comparing authenticated `2024` and `2025` screenshots, the 2025 body still looked denser than 2024 even though the header was aligned. The first metric block and some score cells were wrapping long floating-point strings such as `0.8571428571428571`, making the body feel compressed. |
| **Impact** | The 2025 page was technically correct but harder to read than 2024 because long numeric strings expanded several rows and reduced the visual similarity between the two years. |
| **Root Cause (5 Why)** | **Why1**: Excel-derived floats were serialized with full precision via `Float#to_s`. **Why2**: Some cells contained formula results with many decimal places. **Why3**: Those long strings wrapped inside fixed-width table cells. **Why4**: The 2025 rendering path did not apply the same compact numeric presentation as the 2024 template. **Why5**: The refresh pipeline focused on data completeness first and visual normalization second, so the body row density drifted from the 2024 baseline. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so float values are formatted with `%.4f` and trimmed before being written to `db/process_monitoring_measurement.json`. Re-ran the 2025 refresh and rechecked both `2024` and `2025` screenshots in Playwright. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/db/process_monitoring_measurement.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | The refreshed `year_2025` payload now renders compact values such as `0.8571` instead of long full-precision decimals, and the authenticated 2025 screenshot no longer shows the same degree of body-row over-wrapping. Both `2024` and `2025` pages still return `200`. |
| **Lessons Learned** | Visual parity is not just about structure; numeric formatting materially affects row height and readability. |
| **Prevention** | Keep a compact formatting rule for all Excel-derived floats in this report, and compare rendered screenshots after refreshes that introduce or regenerate formula-driven numbers. |
## INC-041: 2025 process monitoring measurement body rows misrendered because refresh stored a raw grid instead of template-backed year items

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 11:19 JST |
| **Detection** | User pointed out that the `2025` page still had a misaligned `累積 / 実績 / 計画` region even after the header was fixed. Visual comparison showed the page was rendering a different structure than `2024`, especially in the effectiveness section. |
| **Impact** | The 2025 process-monitoring table looked structurally different from 2024, making the cumulative rows appear shifted and reducing trust in the report. |
| **Root Cause (5 Why)** | **Why1**: The refresh service was saving 2025 as an Excel-derived grid hash. **Why2**: The view expected 2025 data to be replayed through the 2024 template so row spans and block structure would remain stable. **Why3**: Excel layout and template layout diverged in the effectiveness section, especially around cumulative/actual/plan rows. **Why4**: A raw grid preserves workbook layout details instead of the canonical contract used by the page. **Why5**: The refresh flow had drifted from the `template + year items` design that the renderer already supports. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so Excel refreshes now save 2025 as month-based year items instead of a raw grid. Added `extract_excel_year_entries` to read the workbook into `{process, metric, target, actual}` items, and updated `ProcessMonitoringMeasurementService#split_actual_values` to accept `当月 / 累計` as well as the legacy labels. The view now rebuilds 2025 through the 2024 template path again. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/app/services/process_monitoring_measurement_service.rb`, `docs/INCIDENT_LOG.md` |
| **Verification** | `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` returned `success=>true`. `bundle exec ruby -c` passed for both modified service files. Playwright screenshots of authenticated `2024` and `2025` pages showed the 2025 table returning to the 2024 template shape, with the cumulative region no longer visibly shifted. |
| **Lessons Learned** | The page contract is the template, not the source workbook. Even when raw Excel looks valid, saving it as a final render format can break the visual invariants users rely on. |
| **Prevention** | Keep 2025 and later stored as normalized year items, not workbook-shaped grids. Compare the rendered result against the 2024 template whenever the refresh path changes. |
## INC-042: Mini PC slowdown required a split between always-on core services and on-demand heavy services
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 23:17 JST |
| **Detection** | User reported that the PC still felt slow while wanting `clawstack-unified` to remain basically always on, and specifically asked for a setup where Telegram stays usable without bringing the whole heavy stack up all the time. |
| **Impact** | The previous all-or-nothing mental model encouraged keeping many heavy services resident together, which made the mini PC feel sluggish even when only Telegram and the core gateway path were needed. |
| **Root Cause (5 Why)** | **Why1**: The unified Docker stack had been treated as one monolith. **Why2**: Heavy services such as Open WebUI, n8n, monitoring, and media tools tended to ride along with the always-on path. **Why3**: Telegram only needs the gateway and a small local model/runtime surface, not the full optional stack. **Why4**: There was no explicit host-side `core` startup entrypoint to separate “always-on but light” from “start only when needed.” **Why5**: Operational convenience had been prioritized over load separation, so the slow mini PC had no first-class lightweight startup mode. |
| **Fix** | Added `scripts/start_clawstack_core.ps1` to start a lightweight always-on set of Docker services (`clawdbot-gateway`, `postgres`, `redis`, `ollama`, `qdrant`, `litellm`, `searxng`, `minio`, `portal_server`) and then launch the canonical Telegram bridge via `scripts/start_telegram_fast_bridge.ps1`. This keeps Telegram usable while leaving the heavy stack on demand through `scripts/start_docker_addons.ps1`. |
| **Files** | `scripts/start_clawstack_core.ps1`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/minipc_optimizer.py` passed. The new core-start script was added without touching `docker-compose.yml`, and the operational plan now separates the always-on Telegram/core path from the heavy addon path. |
| **Lessons Learned** | “Always on” should mean “always on at the lightest viable layer,” not “all services at once.” A small host-side launcher is enough to make the split explicit and safe. |
| **Prevention** | Use the new core launcher for normal work, reserve `start_docker_addons.ps1` for heavy workloads, and keep Telegram bridge startup tied to the lightweight core path so user messages remain responsive. |
## INC-043: Mini PC load needed a staged startup plan instead of simultaneous service activation
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-15 |
| **Detection** | User requested a plan that keeps all apps available but reduces slowdown as much as possible. Current runtime showed a mix of always-on Docker services, email watchdogs, learning memory, and portal tooling, which can create a startup spike if launched together. |
| **Impact** | Simultaneous startup of Docker services and host-side watchdogs increases CPU, memory, and disk pressure during boot or recovery, especially on the mini PC. That makes the system feel slower even if each app is useful on its own. |
| **Root Cause (5 Why)** | **Why1**: Startup paths were spread across several scripts without a single coordinated sequence. **Why2**: Some services were safe individually but still expensive when launched at the same time. **Why3**: Dependency-aware waiting was only partially present in a few scripts. **Why4**: There was no host-side balanced launcher to serialize startup and gate the next step on readiness. **Why5**: The runtime had evolved toward feature coverage first, while load-shedding and startup pacing had not been formalized. |
| **Fix** | Added `scripts/start_minipc_balanced_stack.ps1` as a host-side launcher that starts services in a controlled sequence with per-step health probes and cooldowns. It writes status to `data/state/minipc_balanced_stack/startup_status.json` and supports `-DryRun` plus `-Mode balanced|full`. Also added readiness waits to `scripts/start_email_blacklist_hub_api.ps1` and `scripts/start_email_continuous_watchdog.ps1` so dependent services do not pile up immediately. |
| **Files** | `scripts/start_minipc_balanced_stack.ps1`, `scripts/start_email_blacklist_hub_api.ps1`, `scripts/start_email_continuous_watchdog.ps1`, `data/state/minipc_balanced_stack/startup_status.json`, `data/state/minipc_balanced_stack/startup.log`, `docs/INCIDENT_LOG.md` |
| **Verification** | PowerShell syntax check passed for all edited scripts. `scripts/start_minipc_balanced_stack.ps1 -DryRun` completed successfully and wrote the planned balanced startup sequence: postgres, redis, qdrant, ollama, gateway, portal_server, litellm, n8n, learning_engine, email_search_api, email_blacklist_hub, email_continuous_watchdog, telegram_fast_bridge. |
| **Lessons Learned** | Keeping all apps available does not require starting all of them at once. A staged launcher with health gates gives most of the responsiveness benefit without turning off useful services. |
| **Prevention** | Use the balanced launcher for normal boot and recovery scenarios. Keep heavy extras in `full` mode only, and continue adding readiness checks instead of adding more simultaneous startup paths. |

## INC-044: Postgres WAL corruption caused crash loop and system freeze
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-17 14:35 JST |
| **Detection** | User reported system freeze. docker ps showed postgres in a Restarting state. Container logs confirmed PANIC: could not locate a valid checkpoint record. |
| **Impact** | Entire stack (n8n, Gateway, Paperless, etc.) unable to connect to DB, leading to resource-intensive reconnection loops and system sluggishness/freeze. |
| **Root Cause (5 Why)** | **Why1**: Postgres failed to start. **Why2**: WAL files were corrupted. **Why3**: Likely an improper shutdown or system freeze during heavy I/O. **Why4**: The system was under heavy load due to many simultaneous services (INC-043). **Why5**: Hard reset was performed during a freeze, leading to disk state inconsistency. |
| **Fix** | Stopped postgres container. Ran pg_resetwal -f via a temporary container to reset the Write Ahead Logs. Fixed lightrag health check which was contributing to noise. |
| **Files** | docs/INCIDENT_LOG.md, docker-compose.lightrag.yml |
| **Verification** | postgres status returned to Up and logs showed ready to accept connections. System responsiveness restored. |
| **Lessons Learned** | Database corruption is a high risk during system freezes. Priority should be given to DB health in recovery playbooks. |
| **Prevention** | Ensure staged startup and load balancing (INC-043) are enforced to prevent freezes that lead to hard restarts. |

## INC-045: Rails app access failure (502 Bad Gateway) due to port mismatch
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-18 15:40 JST |
| **Detection** | User reported "Rails繧｢繝励Μ縺ｮ襍ｷ蜍輔↓螟ｱ謨励＠縺ｦ縺�∪縺�". Browser check confirmed 502 Bad Gateway at port 80 (Nginx). |
| **Impact** | Application inaccessible via Nginx reverse proxy (Port 80), though backend container was Up on Port 3004. |
| **Root Cause** | Port mismatch in Nginx configuration. iatf_system/nginx/conf.d/default.conf was pointing to web:3003 while the Rails production server was configured to listen on port **3004** in both docker-compose.production.yml and .env.production. |
| **Fix** | Updated iatf_system/nginx/conf.d/default.conf to use port **3004** for the upstream 
ails_app and restarted the Nginx container. |
| **Files** | [default.conf](file:///d:/Clawdbot_Docker_20260125/iatf_system/nginx/conf.d/default.conf), docs/INCIDENT_LOG.md |
| **Verification** | Browser subagent confirmed http://localhost (Port 80) successfully rendering the Rails login page. |
| **Lessons Learned** | When moving Rails ports or updating environment variables, reverse proxy configurations (Nginx) must be synchronized. |
| **Prevention** | Ensure port consistency across .env.production, docker-compose.production.yml, and 
ginx configurations. Consider using shared environment variables for ports where possible. |

## INC-046: Rails products index (500 Internal Server Error) due to view syntax error
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-18 15:55 JST |
| **Detection** | User reported "We're sorry, but something went wrong" at http://localhost:3004/products. Rails logs confirmed syntax error, unexpected rescue modifier, expecting ')' in pp/views/products/index.html.erb. |
| **Impact** | The main products index page was completely inaccessible, preventing users from viewing item progress. |
| **Root Cause (5 Why)** | **Why1**: ERB compilation failed. **Why2**: Syntax error at line 256. **Why3**: A 
escue modifier was placed inside method call parentheses without proper grouping (I18n.l(val, format: :long rescue val)). **Why4**: This is invalid Ruby syntax for keyword arguments. **Why5**: The template had been modified previously to add localization, and the syntax check was not exhaustive. |
| **Fix** | Corrected the syntax in pp/views/products/index.html.erb by properly grouping the localized call: <%= (I18n.l(@publish_dates[idx], format: :long) rescue @publish_dates[idx]) %>. |
| **Files** | [index.html.erb](file:///d:/Clawdbot_Docker_20260125/iatf_system/app/views/products/index.html.erb), docs/INCIDENT_LOG.md |
| **Verification** | Browser subagent confirmed /products successfully redirects to /users/sign_in and renders the login page without the "something went wrong" error. |
| **Lessons Learned** | ERB views should be checked for syntax correctness, especially when using inline 
escue modifiers. |
| **Prevention** | Ensure any changes to localization or view logic are tested by rendering the actual page. Consider a CI step that runs erblint or similar. |

## INC-047: Rails home page (500 Error) due to missing 'index_tasseido' route/action
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-18 16:20 JST |
| **Detection** | After fixing INC-046, the home page still returned a 500 error. Logs confirmed undefined local variable or method 'index_tasseido_path' at pp/views/products/index.html.erb:48. |
| **Impact** | The Products index page could not be rendered for logged-in users, as the "Attainment Level" (驕疲�蠎ｦ) feature was missing its backend infrastructure. |
| **Root Cause (5 Why)** | **Why1**: The home page failed to render. **Why2**: An undefined path helper index_tasseido_path was called. **Why3**: A new UI component for "Attainment Level" had been added to the template without implementing the route or controller. **Why4**: Changes were made in production mode, and one error (syntax) was masking another (missing route). **Why5**: Development and production environments lacked synchronization on new features. |
| **Fix** | (1) Added index_tasseido route to config/routes.rb. (2) Implemented index_tasseido action in ProductsController. (3) Created pp/views/products/index_tasseido.html.erb to render the existing chart partial. (4) Restarted Docker containers to clear the Rails production route/code cache. |
| **Files** | [routes.rb](file:///d:/Clawdbot_Docker_20260125/iatf_system/config/routes.rb), [products_controller.rb](file:///d:/Clawdbot_Docker_20260125/iatf_system/app/controllers/products_controller.rb), [index_tasseido.html.erb](file:///d:/Clawdbot_Docker_20260125/iatf_system/app/views/products/index_tasseido.html.erb), docs/INCIDENT_LOG.md |
| **Verification** | Browser subagent confirmed the home page loads correctly and clicking '驕疲�蠎ｦ (蝗ｳ逡ｪ蛻･)' renders a valid bar chart for specific part numbers. |
| **Lessons Learned** | Adding UI components requires updating the full stack (Route -> Controller -> View). In production, a container restart is mandatory to apply these changes. |
| **Prevention** | Use automated smoke tests to ensure that all navigation items and form targets on the main dashboard are reachable. |

## INC-048: TOP page layout "destruction" after incomplete UI modernization
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-18 16:40 JST |
| **Detection** | User reported that the TOP page format was "completely destroyed" after the recent fixes. |
| **Impact** | The Products index page had a broken sidebar layout, missing tab styles, and incorrect summary logic (showing flat list instead of grouped summary). |
| **Root Cause (5 Why)** | **Why1**: The layout appeared broken. **Why2**: Essential CSS for the dashboard tabs was missing from the template. **Why3**: An experimental Tailwind sidebar layout had been introduced during a "repair" phase that was incompatible with the existing view structure. **Why4**: The summary partial (_form) differed from the expected dashboard partial (_form3). **Why5**: Changes in production were not immediately visible due to Puma's template caching, masking errors until a restart. |
| **Fix** | (1) Reconstructed index.html.erb using the classic centered 1200px layout from index3. (2) Restored the radio-button tab system with its original CSS. (3) Switched Phase dashboard to use orm3 (grouped summary). (4) Integrated the new 'Tasseido' feature as a functional 8th tab. (5) Restarted the Docker container to apply view changes. |
| **Files** | [index.html.erb](file:///d:/Clawdbot_Docker_20260125/iatf_system/app/views/products/index.html.erb), [products_controller.rb](file:///d:/Clawdbot_Docker_20260125/iatf_system/app/controllers/products_controller.rb) |
| **Verification** | Browser subagent verified the restoration of the classic look, the removal of the sidebar, and the functionality of all 8 tabs. |
| **Lessons Learned** | When "repairing" templates, strictly adhere to existing project design patterns (like radio-button tabs) unless a full redesign is requested. Always restart the production server when updating view templates to clear memory caches. |

### INC-049: Layout Mismatch during IATF Restoration
- **発生日**: 2026-04-18
- **発見方法**: ユーザーからの「デザイン変更」および「崩壊」の指摘
- **影響範囲**: /products ページのUI不一致
- **根本原因**: 「GitHubから入手」という指示に対し、リポジトリの履歴にある旧サイドバー形式を復元したが、その際のCSS/HTMLの整合性不足およびユーザーの期待する『最新のGitHub状態』への理解不足。
- **修正内容**: origin/main から厳密にサイドバー＋青テーブル形式をロールバックし、文字化けのみを技術的に修正。
- **検証結果**: ブラウザ検証によりサイドバー・青テーブル・正確な日本語表示を確認済み。
- **教訓**: 『オリジナル』の定義が文脈により異なるため（Git上のコードか、直近の稼働状態か）、大規模な差し戻し前には必ず構造のプレビューを行うこと。

## INC-050: Email continuous ingest daemon restarted due to stale heartbeat
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-20 05:39 JST |
| **Detection** | Email continuous ingest watchdog restarted the daemon, logging "Reason: daemon heartbeat stale" with "Known stage: full_backfill". |
| **Impact** | The email ingestion process was interrupted during long-running tasks, causing uncompleted syncs and unnecessary service churn. |
| **Root Cause (5 Why)** | **Why1**: Heartbeat (updatedAt) became stale during the full_backfill phase. **Why2**: The full backfill took longer than the watchdog threshold. **Why3**: The script continuous_email_ingest_daemon.py calls 
un_command which blocks completely until the subprocess (
un_priority_gmail_backfill.py) finishes. **Why4**: 
un_command has no mechanism to update the heartbeat file (email_continuous_ingest_status.json) while waiting. **Why5**: Heartbeats were only updated between tasks, failing to account for tasks like ull_backfill (max 5400s) and sync_learning (max 1800s) that run for a long time. |
| **Fix** | Replaced 
un_command in 
un_full_backfill and 
un_learning_sync with a new 
un_command_with_heartbeat wrapper that utilizes subprocess.Popen to update the heartbeat every 30 seconds while waiting. |
| **Files** | data/workspace/continuous_email_ingest_daemon.py |
| **Verification** | Verified code explicitly emits updatedAt and currentTaskHeartbeatAt during long subprocess operations without changing underlying business logic. |
| **Lessons Learned** | Long-running subprocesses required by a constantly monitored daemon must include an internal heartbeat loop. |
| **Prevention** | Ensure any new task invoking a subprocess with a timeout greater than the watchdog's threshold (e.g., > 60 seconds) wraps it with periodic heartbeat updates. |

## INC-051: Learning Engine & Watchdog Failure (Process Conflict)
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-23 02:30 JST |
| **Detection** | Risk notification flagged Learning Engine as offline. Auto-repair failed with exit code 4294770688. |
| **Impact** | Temporary unavailability of learning features and email search/blacklist APIs. |
| **Root Cause (5 Why)** | **Why1**: Learning Engine and Email APIs were reporting as offline or unstable. **Why2**: Duplicate background processes for email_search_api.py and email_blacklist_hub_api.py were running (one via Microsoft Store Python, one via Venv), causing port contention and resource waste. **Why3**: The auto-repair script failed to restart them because it resolved the repo ROOT to C:\Windows\System32. **Why4**: resolve_repo_root() fell back to Path.cwd() when running as a system task, and its traversal logic was insufficient for the host environment. **Why5**: mcp-bridge was also looping because it was configured with a stdio-only MCP server command in a container. |
| **Fix** | (1) Terminated all duplicate host processes. (2) Restored services cleanly using Venv-based launchers. (3) Patched auto_repair_allowed.py with resilient path resolution (traversing up from __file__ and adding explicit fallbacks). (4) Reconfigured mcp-bridge to use clawstack_mcp_server.py (Python/FastMCP) listening on 0.0.0.0:3333. |
| **Files** | [auto_repair_allowed.py](file:///d:/Clawdbot_Docker_20260125/data/workspace/auto_repair_allowed.py), [docker-compose.yml](file:///d:/Clawdbot_Docker_20260125/docker-compose.yml), [clawstack_mcp_server.py](file:///d:/Clawdbot_Docker_20260125/data/workspace/clawstack_mcp_server.py), docs/INCIDENT_LOG.md |
| **Verification** | Verified all endpoints (8110, 8791, 8792, 3333) are reachable from the host. Auto-repair script confirmed correct ROOT resolution (D:\Clawdbot_Docker_20260125). |
| **Lessons Learned** | Background processes must be managed via a single canonical launcher to avoid duplicates. Auto-repair scripts must be path-agnostic or have robust discovery for the host repository root. |
| **Prevention** | Audit the startup sequence in start_minipc_balanced_stack.ps1 to ensure no duplicate spawns occur. Add a check in individual API scripts to exit if another instance is already bound to the port. |

## INC-052: AI Strategy Scout watchdog stopped due to omission from balanced startup
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-25 06:21 JST |
| **Detection** | User reported that AI tool info was not being updated. `ai_strategy_scout_watchdog_status.json` showed updatedAt from 12 days ago. |
| **Impact** | Automated technology research and architectural recommendations were stale. |
| **Root Cause (5 Why)** | **Why1**: Watchdog process was not running. **Why2**: System was recovered multiple times recently (INC-051, etc.). **Why3**: Recoveries used `start_minipc_balanced_stack.ps1`. **Why4**: The balanced startup script did not include the scout watchdog step. **Why5**: The scout was initially treated as a non-core "extra" but is actually part of daily governance. |
| **Fix** | (1) Triggered manual scout to refresh data. (2) Modified `scripts/start_minipc_balanced_stack.ps1` to include `ai_strategy_scout_watchdog` in the default balanced sequence. (3) Restarted the watchdog process. |
| **Files** | `scripts/start_minipc_balanced_stack.ps1`, `docs/INCIDENT_LOG.md`, `ACT.md` |
| **Verification** | Verified `ai_strategy_scout_local_digest.md` contains current date (2026-04-25). Watchdog process confirmed active. |
| **Lessons Learned** | Governance and research tasks (Scout) are as critical as connectivity tasks (Telegram Bridge) for long-term agent autonomy. |
| **Prevention** | Audit the balanced startup script whenever a new critical governance or watchdog service is introduced. |
## INC-053: Telegram OpenClaw conversation and scheduled notification degradation
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-29 21:40 JST |
| **Detection** | User reported abnormal Telegram conversation and asked whether Gmail due-date notifications, AI Strategy Scout, and self-growth were still alive. Local checks showed Telegram replies in mojibake, repeated model timeouts, current n8n API listing only 4 workflows, missing AI Scout/P016 workflows from the active API surface, and duplicate AI Scout watchdog processes. |
| **Impact** | Telegram conversation quality was degraded; Gmail due-date information was not reliably sent to Telegram; AI Scout n8n workflow was absent from the active n8n API; self-growth hygiene was running but had not written a fresh status until manually checked. |
| **Root Cause (5 Why)** | **Why1**: Telegram replies were abnormal. **Why2**: The bridge routed simple messages into a slow local model path and retained stale mojibake status from prior replies. **Why3**: The default bridge model path could exceed the interaction timeout under current host load. **Why4**: Scheduled notification workflows were assumed present from old SQLite/backups, but the active n8n API surface had lost them after prior restore/import churn. **Why5**: Startup/watchdog ownership was split between n8n workflows and host watchdogs, allowing duplicate host processes and missing active n8n workflows to coexist without a single health assertion. |
| **Fix** | (1) Changed `scripts/start_telegram_fast_bridge.ps1` default Telegram model to `qwen3-nothink:latest` and shortened timeout to 20s. (2) Added deterministic fast replies for greetings and weather-unavailable cases in `scripts/telegram_fast_bridge.js`, and added a safe Japanese timeout fallback. (3) Confirmed `data/state/email_context_helper.js` routes Gmail/due-date/report intents with readable Japanese patterns. (4) Added Telegram sending to `data/workspace/ai_strategy_scout_watchdog.py` after successful local scout refresh. (5) Added and ran `data/workspace/repair_telegram_n8n_schedules_20260429.py` to restore P016 and AI Scout workflows from backups, patch P016 to send Gmail due-date summaries to Telegram, and set schedules. (6) Activated restored n8n workflows and restarted canonical Telegram, AI Scout, and self-growth watchdog processes. |
| **Files** | `scripts/start_telegram_fast_bridge.ps1`, `scripts/telegram_fast_bridge.js`, `data/state/email_context_helper.js`, `data/workspace/ai_strategy_scout_watchdog.py`, `data/workspace/repair_telegram_n8n_schedules_20260429.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `node --check scripts/telegram_fast_bridge.js` passed. `python -m py_compile` passed for the modified Python scripts. `email_search_query.py tasks-context "納期 今週 未回答"` returned 1 open Gmail due-date item for 2026-04-29. Active n8n workflows verified: P016 restored as `OpnCRJquLkBjXOyw` active=true; AI Scout restored as `Mc3U5YAJrQxydJ96` active=true. Self-growth hygiene status is healthy with 4 points and estimated 0.023 MB. One canonical process each is running for Telegram bridge, AI Scout watchdog, and self-growth hygiene. |
| **Lessons Learned** | n8n database snapshots/backups are not proof that workflows are active in the current API surface. Telegram chat bridges need deterministic fast paths for common interactions when the local model stack is busy. |
| **Prevention** | Keep a single canonical launcher for each host watchdog, verify active n8n workflows through the REST API after restore, and treat Telegram response timeout/error rate as a health signal rather than only process liveness. |

## INC-054: ByteRover curate failures and local memory fallback
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-29 22:20 JST |
| **Detection** | User reported frequent ByteRover failures and asked whether prior experience had been lost. `brv query` worked from `.brv/context-tree`, but `brv curate` returned HTTP 401 with the built-in ByteRover provider. |
| **Impact** | Existing project memories remained readable, but new experiences could fail to persist through normal `brv curate`, creating a risk that repair knowledge would be lost between sessions. |
| **Root Cause (5 Why)** | **Why1**: ByteRover saves failed. **Why2**: `brv curate` returned HTTP 401 while `brv query` still worked. **Why3**: The built-in ByteRover provider path treated curate as unauthorized even though the provider was connected. **Why4**: The installed CLI was old (`2.1.3`) and local provider fallback with Ollama avoided 401 but was too slow for curate. **Why5**: There was no project-local timeout/fallback wrapper to preserve memory when the official curator path failed. |
| **Fix** | Upgraded global `byterover-cli` from `2.1.3` to `3.10.0`, verified query still works, tested built-in and local provider curate paths, and added `scripts/brv_safe_curate.ps1` as an external harness that writes a local Markdown fallback when `brv curate` fails or times out. |
| **Files** | `scripts/brv_safe_curate.ps1`, `docs/INCIDENT_LOG.md` |
| **Verification** | `brv --version` reports `byterover-cli/3.10.0`. `brv query` completes successfully. Built-in `curate` still returns HTTP 401, confirming the residual upstream/auth issue. Local Ollama provider `query` works, while curate timed out after 180s. `scripts/brv_safe_curate.ps1` was verified with a forced 1s timeout and wrote `.brv/context-tree/infrastructure/byterover_repair/safe_curate_fallback.md`. |
| **Lessons Learned** | ByteRover read health and write health are separate. A working `query` does not prove `curate` can persist new operational lessons. |
| **Prevention** | Use `scripts/brv_safe_curate.ps1` for important post-fix memories until official `brv curate` is healthy. Include `brv status`, provider, CLI version, query, and curate checks in future memory-health triage. |

## INC-055: Missing critical n8n workflows restored from backups
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-29 22:30 JST |
| **Detection** | User asked whether all n8n workflows had been restored. n8n REST API showed only six workflows, and critical scheduled workflows for Daily Promises, Daily System Health Check, Email RAG Ingest, and Daily Trend Opportunity Report were missing from the active API surface while backups existed under `backups/n8n/`. |
| **Impact** | Several scheduled governance and reporting tasks would not run at their expected times, even though older backup files made the workflows appear recoverable. |
| **Root Cause (5 Why)** | **Why1**: Scheduled n8n tasks were missing. **Why2**: The active n8n API surface had fewer workflows than the historical critical set. **Why3**: Prior recovery focused on P016 and AI Scout, leaving other critical workflows in backups only. **Why4**: The integrity manifest was not present on the host, so missing critical workflows were not automatically asserted after n8n restore/import churn. **Why5**: Workflow existence had been inferred from backup files instead of verified through the current REST API. |
| **Fix** | Added and ran `data/workspace/restore_missing_critical_n8n_workflows_20260429.py`. The script backed up the current n8n API list, selected the latest active backup per critical workflow, imported each workflow inactive, validated expected cron expressions, then activated only workflows with no validation problems. |
| **Files** | `data/workspace/restore_missing_critical_n8n_workflows_20260429.py`, `data/workspace/restore_missing_critical_n8n_workflows_20260429_status.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | Restored workflows: `Daily Promises Report` as `4X9B3RqBOtcMvpZh` cron `0 23 * * *`, `Daily System Health Check` as `E1ATfn6J7i7aZrMr` cron `0 9 * * *`, `Email RAG Ingest` as `SKarchfEc4Oy9lMr` cron `0 2 * * *`, and `Daily Trend Opportunity Report` as `nGPAoWhJXVxCF899` cron `30 20 * * *`. Re-checked six critical workflows including P016 and AI Scout; all were `active=true` with expected cron expressions. |
| **Lessons Learned** | Backups prove recoverability, not active service. After any n8n repair, the active REST API surface must be compared against the critical workflow set. |
| **Prevention** | Keep `restore_missing_critical_n8n_workflows_20260429_status.json` as the current restoration evidence and recreate a host-visible critical workflow manifest/check if n8n import churn happens again. |

## INC-056: OpenCode GO LiteLLM config contained direct API key
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-29 22:38 JST |
| **Detection** | User asked whether OpenCode GO was rule-based and running under the optimal environment. Inspection of `data/state/litellm_config.yaml` showed OpenCode GO aliases were registered, but the OpenCode GO API credential was directly embedded in alias definitions instead of using environment-variable references. |
| **Impact** | The OpenCode GO routing policy existed and aliases were visible through LiteLLM, but the config did not fully comply with the external AI confidentiality policy and increased credential exposure risk. |
| **Root Cause (5 Why)** | **Why1**: A credential appeared in a runtime config. **Why2**: OpenCode GO model aliases had been added directly to `data/state/litellm_config.yaml`. **Why3**: The template/notes required environment-variable based configuration, but the merged runtime config used literal values. **Why4**: Registration was checked by model-list visibility rather than by policy compliance. **Why5**: There was no post-merge lint/check for secret literals in LiteLLM routing files. |
| **Fix** | Replaced OpenCode GO `api_base` and `api_key` literals in `data/state/litellm_config.yaml` with `${OPENCODE_GO_API_BASE}` and `${OPENCODE_GO_API_KEY}` for `opencode-go-research`, `opencode-go/kimi-k2.6`, `opencode-go/glm-5.1`, `opencode-go/deepseek-v4-flash`, and `opencode-go/deepseek-v4-pro`. |
| **Files** | `data/state/litellm_config.yaml`, `docs/INCIDENT_LOG.md` |
| **Verification** | LiteLLM `/v1/models` still lists the OpenCode GO aliases. `Select-String` confirms OpenCode GO aliases now use environment-variable references rather than direct literals. No external OpenCode GO inference call was executed because that would send data to a cloud API and may incur cost. |
| **Lessons Learned** | Model alias visibility is not the same as policy-compliant operation. External-provider routes must be checked for both runtime availability and secret-handling hygiene. |
| **Prevention** | Add secret-literal checks for `data/state/litellm_config*.yaml` before future external model merges, and require explicit consent before cloud inference smoke tests. |

## INC-057: IATF教材生成がOpenCode GOからGeminiへ早期フォールバック
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-29 22:50 JST |
| **Detection** | User noted that IATF教材生成 should be using OpenCode GO models. `data/iatf_videos/generation.log` showed recent successful scripts as `google/gemini-2.5-flash` or `direct/gemini-2.5-flash` even though `SCRIPT_MODELS` listed `opencode-go/kimi-k2.6` first. Minimal public smoke tests through LiteLLM confirmed OpenCode GO aliases were reachable. |
| **Impact** | IATF script generation could use the more expensive Gemini fallback even when OpenCode GO was available under the intended routing policy. Failures were also hard to diagnose because empty model responses and timeout details were only printed, not written to a durable status file. |
| **Root Cause (5 Why)** | **Why1**: Gemini was used for recent IATF scripts. **Why2**: The script generator tried only `opencode-go/kimi-k2.6` before Gemini in the LiteLLM route. **Why3**: Kimi/OpenCode calls can take longer than the previous 30s client timeout or occasionally return empty content, causing immediate fallback. **Why4**: Other OpenCode GO aliases (`deepseek-v4-flash` and `deepseek-v4-pro`) were registered but not included in the script-generation priority list. **Why5**: There was no preflight harness to prove OpenCode GO returned non-empty content before a long IATF generation run. |
| **Fix** | Updated `clawstack_v2/apps/iatf_video_factory/pipeline/script_generator.py` to load root `.env` when used standalone, add `opencode-go/deepseek-v4-flash` and `opencode-go/deepseek-v4-pro` before Gemini, extend OpenCode GO LiteLLM client timeout to 180s, treat empty content as an explicit route failure, and write the latest route status to `data/workspace/iatf_opencode_go_routing_status.json`. Added `data/workspace/iatf_opencode_go_preflight.py` as a host-side read-only preflight that tests OpenCode GO aliases with a public non-sensitive prompt and writes `data/workspace/iatf_opencode_go_preflight_status.json`. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/pipeline/script_generator.py`, `data/workspace/iatf_opencode_go_preflight.py`, `data/workspace/iatf_opencode_go_preflight_status.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile clawstack_v2/apps/iatf_video_factory/pipeline/script_generator.py data/workspace/iatf_opencode_go_preflight.py` passed. `python data/workspace/iatf_opencode_go_preflight.py --timeout 60` succeeded for `opencode-go/kimi-k2.6` in 28.30s, `opencode-go/deepseek-v4-flash` in 24.33s, and `opencode-go/deepseek-v4-pro` in 26.83s, all returning non-empty JSON content through LiteLLM. |
| **Lessons Learned** | A model being first in a priority list is not enough; the client timeout and empty-response handling must match the provider's real latency and response behavior. |
| **Prevention** | Run `data/workspace/iatf_opencode_go_preflight.py` before long IATF generation batches and inspect the generated status JSON. Keep multiple OpenCode GO aliases before paid fallbacks so one OpenCode model failure does not immediately route to Gemini. |

## INC-058: OpenRadioss run35 estimated multi-week runtime
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 06:50 JST |
| **Detection** | User asked to make OpenRadioss finish in about 10 hours. Inspection of `/work/engine_run35.log` showed the engine was still around `T=0.00124 s` after about `50,200 s` elapsed, while the deck end time was `0.08 s` with `DT=5.0e-8 s`, giving a multi-week remaining estimate. |
| **Impact** | The OpenRadioss job was consuming CPU but was not practical as an engineering feedback run. It also competed with other local generation work for host resources. |
| **Root Cause (5 Why)** | **Why1**: The calculation was projected to take far longer than expected. **Why2**: The engine deck requested `0.08 s` of simulation time at a very small timestep. **Why3**: That implies roughly `1,600,000` cycles before contact/cost effects. **Why4**: The job was being used as a feedback/screening calculation rather than a final high-fidelity validation, but the run controls were closer to a long validation deck. **Why5**: There was no host-side tuning harness that preserved the original deck, records the intended runtime budget, and restarts a shortened screening run with traceable settings. |
| **Fix** | Added `data/workspace/openradioss_10h_tune_run35.py` to back up current `/work` inputs/logs, patch the engine deck, stop only the active OpenRadioss engine process, and restart as `run37`. Tuned settings: end time `0.0014 s`, minimum nodal timestep `8.0e-8 s`, animation interval `0.00035 s`, and reduced animation output to EPSP/VONM/DISP. Added `data/workspace/openradioss_10h_tuning_report.md` with the analysis and remaining engineering notes. |
| **Files** | `data/workspace/openradioss_10h_tune_run35.py`, `data/workspace/openradioss_10h_tuning_report.md`, `data/workspace/openradioss_10h_tuning_status.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/openradioss_10h_tune_run35.py` passed. `run37` started in `clawstack-unified-openradioss-1` with PID recorded in `/work/engine.pid`. Initial line showed `DT=8.0000E-08` and `DM/M=1.9495E+01`. After about 90 seconds, `/work/engine_run37.log` reported `NC=100`, `T=8.0000E-06`, `DM/M=1.9526E+01`, and `REMAINING TIME=13122.24 s`, which is within the requested 10-hour class. |
| **Lessons Learned** | Runtime budget must be encoded directly into the engine deck for screening runs. Leaving a validation-style end time in place can make a job appear healthy while being operationally unusable. |
| **Prevention** | Keep a separate screening profile for OpenRadioss jobs, preserve original validation decks before tuning, and check estimated cycles plus early `REMAINING TIME` before leaving a long CAE run unattended. |

## INC-059: Rails app unavailable through nginx and LAN address
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 08:20 JST |
| **Detection** | User reported that `http://192.168.5.172/` did not display the Rails app. Host-side `curl` showed `http://127.0.0.1/` initially returned 502 through nginx, while the Rails container itself returned a login redirect on port 3004. |
| **Impact** | The Rails app was not reachable through the intended nginx entrypoint, and LAN access through the host IP remained unavailable even after the application proxy was repaired. |
| **Root Cause (5 Why)** | **Why1**: nginx returned 502. **Why2**: nginx tried to proxy to `web:3003`. **Why3**: the Rails/Puma container was listening on `0.0.0.0:3004`, so upstream port 3003 refused the connection. **Why4**: the nginx config had drifted from the active Rails container port. **Why5**: there was no startup health check that validated nginx upstream reachability and LAN binding together. Residual LAN timeout is separate: Docker reported `0.0.0.0:80->80`, but Windows did not show a host listener on physical port 80 and adding a `netsh portproxy` entry requires administrator rights. |
| **Fix** | Changed `iatf_system/nginx/conf.d/default.conf` upstream from `web:3003` to `web:3004`, validated the config with `nginx -t`, reloaded nginx, and restarted `iatf_system-nginx-1` to refresh the port binding. After user approved the Docker binding fix, tested direct Docker LAN binding, then moved the active production compose nginx mapping to `127.0.0.1:18090:80` after direct `192.168.5.172:80:80` still failed before reaching nginx. This leaves host port 80 free for an administrator-level Windows `0.0.0.0:80 -> 127.0.0.1:18090` portproxy. Recreated only `iatf_system-nginx-1`. No protected Rails view/layout/route/application files were changed. |
| **Files** | `iatf_system/nginx/conf.d/default.conf`, `iatf_system/docker-compose.production.yml`, `docs/INCIDENT_LOG.md` |
| **Verification** | `docker exec iatf_system-nginx-1 nginx -t` passed. `curl.exe -I --max-time 8 http://127.0.0.1/` returned `HTTP/1.1 302 Found` with `Location: http://127.0.0.1/users/sign_in`, proving nginx-to-Rails proxying is repaired. Direct Docker LAN binding showed `127.0.0.1:80->80/tcp, 192.168.5.172:80->80/tcp` but `http://192.168.5.172/` still timed out and nginx logs showed the request never reached nginx. Final tested Docker mapping is `127.0.0.1:18090->80/tcp`; Windows `portproxy` is `0.0.0.0:80 -> 127.0.0.1:18090`. `curl.exe -I --max-time 8 http://127.0.0.1:18090/` and `curl.exe -I --max-time 8 http://192.168.5.172/` both return `HTTP/1.1 302 Found`; the LAN response redirects to `http://192.168.5.172/users/sign_in`. nginx access logs show both requests reaching `iatf_system-nginx-1`. |
| **Lessons Learned** | Local container health, nginx upstream health, and LAN reachability are separate checks. A Docker port mapping line is not sufficient evidence that Windows is listening on the physical LAN address. |
| **Prevention** | Add a lightweight host-side health check that asserts all three paths: Rails container port 3004, nginx via `127.0.0.1:80`, and LAN address `192.168.5.172:80`. Keep nginx upstream port synchronized with the Rails/Puma runtime port in future compose/config changes. |

## INC-060: Rails production Tailwind/assets missing after LAN recovery
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 09:10 JST |
| **Detection** | User reported that the Rails design/layout decoration disappeared and Tailwind CSS appeared dead after LAN access was restored. `curl` against the sign-in page showed stylesheet links to `/assets/tailwind-...css`, `/assets/inter-font-...css`, and JS assets, but direct requests for those asset URLs returned 404. |
| **Impact** | Rails pages loaded, but production styling, layout decoration, images, and JavaScript assets were missing or degraded. The app looked unstyled even though the route itself was reachable. |
| **Root Cause (5 Why)** | **Why1**: The browser loaded the HTML but not the CSS. **Why2**: `/assets/...` URLs returned 404. **Why3**: `public/assets` inside `iatf_system-web-1` was empty after the production container/volume state changed. **Why4**: The production startup command only ran `npm run build:css`, which creates the non-digested Tailwind build but does not populate Rails' digested `public/assets` manifest. **Why5**: There was no post-restart health check that requested the actual digest CSS/JS URLs referenced by the rendered HTML. |
| **Fix** | Ran `RAILS_ENV=production bundle exec rails assets:precompile` inside `iatf_system-web-1`, then restarted the web container so Rails reloaded the new asset manifest. Updated `iatf_system/docker-compose.production.yml` so the production web command runs `bundle exec rails assets:precompile` before starting Puma, preventing empty `public/assets` after future container recreation. |
| **Files** | `iatf_system/docker-compose.production.yml`, `iatf_system/app/assets/stylesheets/tailwind.css`, `docs/INCIDENT_LOG.md` |
| **Verification** | After precompile and web recreation, `curl -L http://192.168.5.172/users/sign_in` references `/assets/tailwind-e9c087ad77e1b3d918d43a7664907da844ab9e7b.css`, `/assets/inter-font-1b0c468edea01b74041b0c74f0ae84d34c09f89f.css`, and `/assets/application-e249ed276a5680c3eca8b1b2c3b5d81ea26353d9.js`. Direct `curl -I` checks for those three URLs through `http://192.168.5.172/` all returned `HTTP/1.1 200 OK`. `public/assets` contains 74 files after precompile. |
| **Lessons Learned** | A successful Rails route check is not enough after production container changes. Asset health must be verified by fetching the exact digest URLs emitted in the rendered HTML. |
| **Prevention** | Keep production startup responsible for `rails assets:precompile` before Puma starts, and add digest CSS/JS URL checks to future Rails availability triage. |

## INC-061: Amada press IoT charts did not receive numeric data
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 09:27 JST |
| **Detection** | User reported that graphs from the Amada press machine were not reflected on `http://192.168.5.172/products/iot?commit=IOTデータ`. Local checks found today's Amada CSV files under `/myapp/db/record/iot`, but `IotDataService.call` returned series like `["0", nil]` because the parser expected two CSV columns. |
| **Impact** | The IoT page loaded, but Amada80t3 line charts had empty/nil values for most series, so current press data was not visualized even though Node-RED/Raspberry Pi CSV files were present. |
| **Root Cause (5 Why)** | **Why1**: Amada charts did not show current values. **Why2**: Chartkick received nil values for the y-axis. **Why3**: `IotDataService` used `CSV.foreach(..., headers: true)` and emitted `[row[0], row[1]]`. **Why4**: Current Amada CSV files are one-value-per-line time series without headers, so the first value was treated as a header and there was no second column. **Why5**: The page also used historical snake_case instance variable names for several Amada/Dobby charts while the service generated mixed-case names, so some series could remain nil even after CSV loading. |
| **Fix** | Updated `IotDataService#load_csv` to parse headerless CSV, support both one-column and two-column formats, synthesize the x-axis from row index for one-column files, and cast numeric values. Updated `ProductsController#iot` to provide backward-compatible instance variable aliases used by the existing IoT view. Restarted `iatf_system-web-1` to load the production code. |
| **Files** | `iatf_system/app/services/iot_data_service.rb`, `iatf_system/app/controllers/products_controller.rb`, `docs/INCIDENT_LOG.md` |
| **Verification** | `ruby -c` passed for `iot_data_service.rb` and `products_controller.rb`. `RAILS_ENV=production rails runner` confirmed Amada series contain numeric values: `StampingJYOTAIAmada80t3` 54 points ending `["53", 1]`, `StampingchokoteiAmada80t3` 54 points ending `["53", 25]`, `SPMAmada80t3` 54 points ending `["53", 130]`, and `ShotAmada80t3` 54 points ending `["53", 13130]`. After restart, Puma listened on `0.0.0.0:3004` and `http://192.168.5.172/` returned `HTTP/1.1 302 Found`. |
| **Lessons Learned** | Field CSV contracts can change independently from Rails assumptions. IoT graph health must validate non-nil y-values, not just file existence. |
| **Prevention** | Keep `IotDataService` tolerant of one-column and two-column CSVs, and add future health checks that report row count plus first/last non-nil values for each machine series. |

## INC-062: Node-RED IoT CSV lacked timestamp column for chart x-axis
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 09:39 JST |
| **Detection** | User clarified that the IoT chart x-axis should be date/time and that Node-RED should write the sensor acquisition time into column A when generating CSV files. Inspection showed the active `Shiftr Receiver` flow in `iatf_system-nodered-1` wrote raw MQTT payload values directly to CSV, producing one-value-per-line files. |
| **Impact** | Rails could graph current values after INC-061, but the x-axis used fallback row indexes for one-column legacy rows rather than actual acquisition timestamps. This reduced traceability of Amada press data. |
| **Root Cause (5 Why)** | **Why1**: The chart x-axis was not date/time. **Why2**: CSV rows did not contain acquisition timestamps. **Why3**: Docker-side Node-RED receiver functions set only `msg.filename` and passed raw `msg.payload` to the file node. **Why4**: The Shiftr receiver was introduced as a transport bridge and did not preserve the timestamp behavior used in some Raspberry Pi local CSV flows. **Why5**: The data contract between Node-RED CSV output and Rails Chartkick input was not documented or verified with a two-column sample. |
| **Fix** | Updated `Node_Red_JSON_20260429/docker/docker_nodered_shiftr_receiver.json` so all ten `Prep *` function nodes write `YYYY/MM/DD HH:mm:ss,value` to `msg.payload` before the file node appends the row. Backed up active Node-RED flows to `backups/nodered/iot_timestamp_20260430/iatf_system_nodered_flows_before_timestamp_patch.json` and patched the live `iatf_system-nodered-1` `Shiftr Receiver` flow through the Node-RED `/flows` API. After discovering the Node-RED container clock is UTC, changed the timestamp generation to explicitly output JST by adding 9 hours and formatting UTC fields from the adjusted timestamp. Backed up live IoT CSVs to `backups/iot_csv_timezone_20260430_095031/iot` and corrected already-written `2026/04/30 00:xx` timestamp rows to `2026/04/30 09:xx`; legacy one-column rows were left unchanged because they do not contain recoverable acquisition timestamps. |
| **Files** | `Node_Red_JSON_20260429/docker/docker_nodered_shiftr_receiver.json`, `backups/nodered/iot_timestamp_20260430/iatf_system_nodered_flows_before_timestamp_patch.json`, `backups/iot_csv_timezone_20260430_095031/iot`, `docs/INCIDENT_LOG.md` |
| **Verification** | JSON validation passed for `docker_nodered_shiftr_receiver.json`; all 10 `Prep *` nodes contain `msg.payload = timestamp + ',' + csvValue(msg.payload)`. The active Node-RED `/flows` API also shows the same timestamp payload logic in the `docker_receiver_tab`, including the JST correction `Date.now() + 9 * 60 * 60 * 1000`. Rails parsing was verified with a two-column sample: `[["2026/04/30 09:31:00", 123], ["2026/04/30 09:32:00", 124.5]]`. Host time and Rails `Time.current` both showed `2026/04/30 09:45-09:46 +09:00` during verification. After CSV correction, `2026_04_30*Amada80t3.csv` contained `utc00=0` and `jst09=111`; each Amada CSV tail ended at `2026/04/30 09:51:36,...` during verification. |
| **Lessons Learned** | Transport bridge flows must preserve the data contract, not only move MQTT topics. Chart traceability requires timestamped CSV rows at the data acquisition/write boundary. |
| **Prevention** | Treat IoT CSV as `timestamp,value`. Keep Rails tolerant of legacy one-column files, but require new Node-RED receiver flows to emit timestamped two-column rows and validate this before import. |

## INC-063: IoT monthly press utilization summary was missing
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 12:05 JST |
| **Detection** | User requested a monthly page that lists each monitored press machine's operating time, operating rate, shot count, SPM, and chokotei count, with browser-adjustable planned working hours such as 7.0 or 7.5 hours per day. |
| **Impact** | The real-time IoT graph showed current series, but users could not quickly review monthly equipment performance or compare multiple machines as the monitored press count grows. |
| **Root Cause (5 Why)** | **Why1**: Monthly utilization was not visible. **Why2**: Existing Rails IoT logic only loaded today's CSV series for charts. **Why3**: There was no service that scanned monthly IoT CSV files and grouped data by machine and metric. **Why4**: The original implementation assumed fixed known series instead of using the filename contract to discover machines. **Why5**: Operating rate rules had not yet been encoded as a reusable calculation with user-adjustable working-hour assumptions. |
| **Fix** | Added `IotMonthlySummaryService` to scan `/myapp/db/record/iot/YYYY_MM_*.csv`, detect equipment from `Shot*`, `SPM*`, `Stampingchokotei*`, and `StampingJYOTAI*` filenames, and calculate monthly active days, operating hours, operating rate, shot delta, average non-zero SPM, chokotei delta, and latest timestamp. Added `ProductsController#iot_monthly`, the `/products/iot_monthly` route, and a simple self-contained monthly summary view with month and planned-hours controls. Added a link from the real-time IoT page to the monthly summary. |
| **Files** | `iatf_system/app/services/iot_monthly_summary_service.rb` lines 7, 127, 145, 168; `iatf_system/app/controllers/products_controller.rb` lines 199-203; `iatf_system/config/routes.rb` line 72; `iatf_system/app/views/products/iot_monthly.html.erb` lines 262, 271, 313, 352; `iatf_system/app/views/products/iot.html.erb`; `docs/INCIDENT_LOG.md` |
| **Verification** | `ruby -c app/services/iot_monthly_summary_service.rb` and `ruby -c app/controllers/products_controller.rb` passed in `iatf_system-web-1`. `RAILS_ENV=production rails runner` for `month=2026-04` and `work_hours_per_day=8` detected `Amada80t3` with `active_days=2`, `available_hours=16.0`, `operating_hours=3.78`, `operating_rate=23.6`, `shot_count=28259`, `average_spm=125.7`, `chokotei_count=51`, and a latest timestamp in JST. Renderer verification for the monthly template returned HTML containing `iotm-title`, `Amada80t3`, and the adjustable `7.5` value. After restarting only `iatf_system-web-1`, `curl -I http://127.0.0.1:18090/products/iot_monthly?month=2026-04&work_hours_per_day=7.5` reached `ProductsController#iot_monthly` and returned the expected login redirect for an unauthenticated request. |
| **Lessons Learned** | IoT dashboards need both current graph views and period summaries. Filename-based machine discovery is safer for expansion than hard-coding every future press machine in the controller. |
| **Prevention** | Keep the monthly summary service tied to the `timestamp,value` CSV contract and add future equipment by following the metric filename prefixes instead of changing Rails code for each new machine. |

## INC-064: IoT daily equipment matrix was missing
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 12:31 JST |
| **Detection** | User requested another IoT page where the user selects year and month, the horizontal axis is day, the vertical axis is equipment, and tabs switch between chokotei count, shot count, and SPM statistics including MAX, AVE, MIN, and AVE±3σ. |
| **Impact** | Users could see current graphs and monthly totals, but could not compare daily machine performance across the whole month in a scan-friendly matrix. This would become harder as the number of monitored presses increases. |
| **Root Cause (5 Why)** | **Why1**: Daily cross-machine comparison was unavailable. **Why2**: Existing Rails IoT pages were chart/current-series and monthly-total oriented. **Why3**: There was no daily matrix service that grouped CSV files by date, equipment, and metric. **Why4**: SPM statistics had not been encoded as daily max/average/min/control-band values. **Why5**: The expansion path for more equipment required a filename-driven discovery service rather than another hard-coded controller/view list. |
| **Fix** | Added `IotDailyMatrixService` to scan `/myapp/db/record/iot/YYYY_MM_DD*.csv`, detect equipment from `Shot*`, `SPM*`, and `Stampingchokotei*` filenames, build all dates in the selected month, and calculate daily chokotei delta, daily shot delta, and SPM max/average/min/average±3 sigma from non-zero SPM samples. Added `ProductsController#iot_daily_matrix`, `/products/iot_daily_matrix`, a self-contained daily matrix view with year/month selectors and CSS-only tabs, a reusable numeric matrix partial, and navigation links from the real-time and monthly IoT pages. |
| **Files** | `iatf_system/app/services/iot_daily_matrix_service.rb` lines 7, 10, 26, 117, 124; `iatf_system/app/controllers/products_controller.rb` lines 206-210; `iatf_system/config/routes.rb` line 73; `iatf_system/app/views/products/iot_daily_matrix.html.erb` lines 254, 264, 280, 298, 321, 340; `iatf_system/app/views/products/_iot_daily_matrix_number_table.html.erb`; `iatf_system/app/views/products/iot.html.erb`; `iatf_system/app/views/products/iot_monthly.html.erb`; `docs/INCIDENT_LOG.md` |
| **Verification** | `ruby -c app/services/iot_daily_matrix_service.rb` and `ruby -c app/controllers/products_controller.rb` passed in `iatf_system-web-1`. `RAILS_ENV=production rails runner` for `year=2026, month=4` detected `["Amada80t3"]`, 30 date columns, 2026-04-30 shot count `19426`, chokotei count `30`, and SPM stats `{max: 248.0, average: 125.6, min: 63.0, plus_3sigma: 160.2, minus_3sigma: 91.1}`. Renderer verification confirmed the page includes `iotd-title`, tab IDs, `Amada80t3`, and `MAX`. After restarting only `iatf_system-web-1`, `curl -I http://127.0.0.1:18090/products/iot_daily_matrix?year=2026&month=4` reached `ProductsController#iot_daily_matrix` and returned the expected login redirect for an unauthenticated request. |
| **Lessons Learned** | Period dashboards should support both aggregate totals and daily matrix views. Statistical SPM summaries are more useful when presented in the same equipment/date matrix as counts. |
| **Prevention** | Keep daily IoT analysis filename-driven, preserve the `timestamp,value` CSV contract, and add future metrics as new service-level metric patterns before changing controller/view code. |

## INC-065: IoT real-time graph page needed business-friendly visual modernization
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 12:59 JST |
| **Detection** | User requested `http://192.168.5.172/products/iot` to be made more modern while staying simple, understated, and business-oriented, with rollback available. |
| **Impact** | The existing IoT page showed the graphs but used very wide fixed layouts, old tab styling, mojibake labels, and sparse navigation. It was harder to scan in daily business use even though the data path was functioning. |
| **Root Cause (5 Why)** | **Why1**: The page looked dated and difficult to read. **Why2**: It used a fixed `2200px` tab layout and minimal visual hierarchy. **Why3**: It had grown from an early graph test page rather than a maintained production dashboard. **Why4**: Later monthly and daily summary pages were added with clearer navigation, but the real-time graph page had not been brought up to the same standard. **Why5**: The page relied on old inline structure instead of a self-contained, rollback-friendly view refresh. |
| **Fix** | Backed up the current state to `backup/pre-iot-page-modernize-20260430`, `backups/git_worktree/pre_iot_page_modernize_20260430.diff`, and `backups/git_worktree/iot_html_erb_pre_modernize_20260430.bak`. Replaced only `iatf_system/app/views/products/iot.html.erb` with a self-contained business-style layout: restrained slate/white palette, compact header, navigation buttons to monthly and daily pages, summary tiles, CSS-only equipment tabs, and chart sections using `width: 100%`. Existing controller, services, routes, CSV logic, layout, shared partials, assets, and Docker settings were not changed for this UI refresh. |
| **Files** | `iatf_system/app/views/products/iot.html.erb` lines 213, 217-218, 251, 261-361; `docs/INCIDENT_LOG.md`; rollback backups under `backups/git_worktree/` |
| **Verification** | `RAILS_ENV=production rails runner` rendered `products/iot` with Chartkick output and produced a 64,819 character HTML fragment. File checks confirmed the new title, monthly/daily links, Amada tab, and all `line_chart` calls are present. Restarted only `iatf_system-web-1`; after startup asset processing completed, `curl -I http://127.0.0.1:18090/products/iot` reached `ProductsController#iot` and returned the expected login redirect for an unauthenticated request. |
| **Lessons Learned** | Operational dashboards need periodic UI maintenance even when data pipelines are healthy. Keeping the refresh self-contained in the view made rollback straightforward and avoided Tailwind build fragility. |
| **Prevention** | For future IoT UI changes, keep the chart data path separate from visual refreshes, preserve a per-view backup before replacing dashboards, and verify both renderer output and route reachability after restart. |

## INC-066: IATF video rendered invalid close-up frames without visual QA
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 15:50 JST |
| **Detection** | User reported that the generated IATF video showed the same grayscale close-up frame from start to finish and was unusable as training material. A sampled contact sheet confirmed six sampled frames were visually identical close-ups. |
| **Impact** | The produced MP4 was falsely treated as a completed training video although the visual content was invalid. This damaged trust and could waste review time if delivered as a finished IATF teaching asset. |
| **Root Cause (5 Why)** | **Why1**: The final video showed the same unusable image throughout. **Why2**: The Blender renderer imported GLB character assets and rendered frames even when the camera/scale produced an extreme close-up. **Why3**: The pipeline only checked that enough PNG frames existed and then composed MP4; it did not visually inspect sample frames. **Why4**: Existing-frame resume logic skipped rerendering when frame count was sufficient, so bad frames could be reused repeatedly. **Why5**: There was no mandatory AI/human visual gate between render and final MP4 composition. |
| **Fix** | Added `clawstack_v2/apps/iatf_video_factory/pipeline/visual_qa.py`, which samples rendered frames, writes a contact sheet, checks frame dimension consistency, visual detail, contrast, and near-identical sampled frames, and fails closed before MP4 composition. Updated `run_host.py` to call Visual QA after Blender render or existing-frame skip and before FFmpeg compose, and initialized `model = "unknown"` so final status updates do not fail on resume/error edge cases. Stopped an orphaned old `blender.exe` process. Built a replacement slide-based MP4 from the existing valid Japanese timeline/audio using `data/workspace/rebuild_iatf_video_as_slides_20260430.py` so the current deliverable is at least readable business training content instead of the invalid character close-up render. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/pipeline/visual_qa.py`; `clawstack_v2/apps/iatf_video_factory/run_host.py`; `data/workspace/rebuild_iatf_video_as_slides_20260430.py`; `data/workspace/iatf_video_visual_qa/contact_sheet_current_bad_video.jpg`; `data/iatf_videos/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ_slide_rebuild.mp4`; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile` passed for `visual_qa.py`, `run_host.py`, and `rebuild_iatf_video_as_slides_20260430.py`. Running Visual QA on the bad existing frames returned `ok=False` with `inconsistent_frame_dimensions`, `low_visual_detail`, and `sample_frames_are_nearly_identical`, proving the new gate catches this failure before MP4 composition. The slide rebuild generated 56 slides and `IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ_slide_rebuild.mp4`; `ffprobe` reported 1280x720, duration `833.2s`, and size about `9.6MB`. Preview frames at 5s, 6m, and 12m were extracted and visually inspected; the 12m frame was regenerated after fixing Japanese text wrapping so long text stays inside the card. |
| **Lessons Learned** | File existence and render completion are not quality checks. Long-running media generation must include visual inspection gates before finalization, especially when 3D camera/model assets are involved. |
| **Prevention** | Treat `visual_qa_report.json` and `contact_sheet.jpg` as mandatory artifacts for every IATF video render. Do not mark a video done unless Visual QA passes; when it fails, preserve the contact sheet and stop before FFmpeg composition. Prefer business slide rendering for IATF teaching assets unless character animation has passed a short preview QA first. |

## INC-067: IATF video generation lacked slide-first AI review gate
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 16:20 JST |
| **Detection** | After the invalid close-up video incident, user required that slides be generated first, visually checked by a capable AI model against the script, and only then allowed to proceed to video generation. |
| **Impact** | The previous pipeline could generate audio, render frames, and compose video without proving the instructional slides/storyboard were readable or script-aligned. This allowed expensive downstream work to start before the most reviewable artifact existed. |
| **Root Cause (5 Why)** | **Why1**: Video generation started before a reviewable slide/storyboard gate. **Why2**: The pipeline treated script/timeline JSON as enough structure to proceed to rendering. **Why3**: The first visual artifact was the Blender frame set, which is expensive and can fail in camera/model placement. **Why4**: There was no pre-video AI review contract requiring approval of a contact sheet and manifest. **Why5**: Cloud AI cost/data safety concerns had prevented ad hoc visual-model calls, but no fail-closed local review handoff existed. |
| **Fix** | Added `clawstack_v2/apps/iatf_video_factory/pipeline/slide_preflight.py`, which renders a slide deck from the timeline, writes `slide_preflight/contact_sheet.jpg`, `slide_manifest.json`, and `ai_review_request.json`, verifies slide count, file existence, 1280x720 size, nonblank script text, and text SHA-256 alignment with the timeline. Updated `run_host.py` to call `slide_preflight_gate` immediately after script/timeline creation or resume and before lip sync, Blender rendering, Visual QA, or FFmpeg composition. The default mode is fail-closed: if `IATF_VIDEO_AI_REVIEW_CMD` is not configured, video generation stops before rendering. A `local_only` mode exists only for deterministic local verification and does not represent AI visual approval. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/pipeline/slide_preflight.py` lines 28, 194, 215, 244; `clawstack_v2/apps/iatf_video_factory/run_host.py` lines 160, 287-288; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile clawstack_v2/apps/iatf_video_factory/pipeline/slide_preflight.py clawstack_v2/apps/iatf_video_factory/pipeline/visual_qa.py clawstack_v2/apps/iatf_video_factory/run_host.py` passed. With `IATF_VIDEO_SLIDE_REVIEW_MODE=local_only`, the module generated 56 slide previews, `slide_manifest.json`, `ai_review_request.json`, and `contact_sheet.jpg`; the contact sheet was visually inspected and showed readable Japanese business slides across the sequence. With default settings and no AI reviewer command, the module failed closed with `ai_review_required_but_IATF_VIDEO_AI_REVIEW_CMD_not_set`, proving video generation will not proceed without explicit AI review approval. |
| **Lessons Learned** | The cheapest useful visual artifact should be reviewed first. A slide contact sheet is easier to inspect than a finished MP4 and catches storyboard, readability, and content-order problems before rendering. |
| **Prevention** | Keep slide preflight mandatory before every IATF video run. Do not configure cloud visual-review commands without user consent on model, data sent, and cost. Preserve `slide_preflight_result.json` as the audit evidence for each generated training video. |

## INC-068: IATF video rebuild continued with approved slide-video path
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 16:21 JST |
| **Detection** | User reported that Claude had stopped at usage limit after being instructed to rebuild the IATF training video by generating slides first, checking them with a capable AI model, and only then starting video generation with periodic content checks. |
| **Impact** | The rebuild could have remained half-finished, and the unsafe Blender-first path could still be used in future runs after slide approval. |
| **Root Cause (5 Why)** | **Why1**: The rebuild stopped before completion. **Why2**: The previous continuation depended on an interactive agent session reaching the end. **Why3**: The video factory had a slide preflight gate but no dedicated approved-slide video composer with periodic MP4 spot checks. **Why4**: `run_host.py` still defaulted to the Blender render path after slide approval. **Why5**: There was no resumable host-side build harness that records AI slide approval, composes a slide video, and verifies sampled MP4 frames against expected slides. |
| **Fix** | Added `clawstack_v2/apps/iatf_video_factory/pipeline/slide_video_builder.py`. The builder consumes `slide_preflight/slide_manifest.json`, `timeline.json`, and `master_audio.wav`, records `ai_review_approval.json`, composes an H.264 1280x720 slide video at 30fps, and extracts 12 checkpoint frames across the finished MP4 to compare each against the expected slide hash. Updated `run_host.py` so the default render mode is now `IATF_VIDEO_RENDER_MODE=slides`; Blender only runs when explicitly requested with `IATF_VIDEO_RENDER_MODE=blender`. Fixed a Windows console logging crash by replacing an unsupported dash character in the psutil fallback log. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/pipeline/slide_video_builder.py`; `clawstack_v2/apps/iatf_video_factory/run_host.py`; `data/iatf_videos/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ_slide_reviewed.mp4`; `data/iatf_videos/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ/slide_preflight/video_build/slide_video_build_result.json`; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile` passed for `slide_video_builder.py`, `slide_preflight.py`, `visual_qa.py`, and `run_host.py`. The reviewed slide video was generated successfully at `1280x720`, duration `849.652s`, size `16,031,789 bytes`, with video stream duration `849.633s` and `25,489` frames. The periodic MP4 spot check sampled slides 1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51, and 56; all 12 had hash distance `0` from the expected slide. The spot-check contact sheet was visually inspected and showed readable Japanese slides through the beginning, middle, and end. A full `run_host.py --pdf ...` integration run with `IATF_VIDEO_SLIDE_REVIEW_MODE=local_only` and `IATF_VIDEO_RENDER_MODE=slides` completed without Blender and logged `Slide video OK` plus `Spot check OK`. |
| **Lessons Learned** | A reliable training-video pipeline should review the storyboard artifact first, then verify the final MP4 at multiple timestamps. For static teaching material, slide-video composition is safer and cheaper than 3D character rendering until the 3D path has its own short-preview approval loop. |
| **Prevention** | Keep `IATF_VIDEO_RENDER_MODE=slides` as the default. Require explicit opt-in for Blender. Preserve `ai_review_approval.json`, `slide_video_build_result.json`, and `video_spot_check_contact_sheet.jpg` with every rebuilt IATF video. |

## INC-069: IATF video factory did not pick up normal Japanese training PDFs
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-01 11:00 JST |
| **Detection** | User clarified that slide videos are not useful for this training flow and pointed to `iatf_system/db/documents` plus `iatf_system/db/record/attachedfile.csv` as the canonical source for PDFs whose filenames start with `IATF 16949 内部監査資料`. A `run_host.py --limit 0` check had previously reported zero pending PDFs despite many matching files in `documents`. |
| **Impact** | The IATF video factory could not resume batch generation from the intended PDF source. It also defaulted toward the slide-video path added during the previous recovery, contrary to the desired non-slide training-video flow. |
| **Root Cause (5 Why)** | **Why1**: The pending queue was empty. **Why2**: `list_pending` searched for a mojibake filename prefix instead of the normal Japanese prefix. **Why3**: The pipeline did not use `attachedfile.csv`, even though it is the seed/list source for files in `documents`. **Why4**: The previous incident response optimized for a slide fallback after bad Blender frames. **Why5**: There was no smoke check comparing pending detection against `attachedfile.csv` and the host `documents` directory after the recovery change. |
| **Fix** | Updated `clawstack_v2/apps/iatf_video_factory/run_host.py` to read `attachedfile.csv` as UTF-8, select PDF rows whose normalized filename starts with `IATF 16949 内部監査資料`, resolve them against `iatf_system/db/documents`, and fall back to a normalized directory scan if the CSV is unavailable. Changed the default render mode back to `blender`, so slide preflight/video composition only runs when explicitly requested with `IATF_VIDEO_RENDER_MODE=slides`. Added quarantine-and-rerender behavior when existing rendered frames fail Visual QA, preventing bad close-up frames from being reused. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/run_host.py` lines 16, 99, 185, 335, 384; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile clawstack_v2/apps/iatf_video_factory/run_host.py clawstack_v2/apps/iatf_video_factory/pipeline/visual_qa.py` passed. Import-level smoke check reported `pending_count 43` from `attachedfile.csv`/`documents`, with the first items including `IATF 16949 内部監査資料_箇条8.5.4_箇条8.5.4.1梱包工程.pdf` and `IATF 16949 内部監査資料_箇条10.2.4_ポカヨケ.pdf`. `python clawstack_v2/apps/iatf_video_factory/run_host.py --limit 0` returned `未処理PDF: 0本`, confirming limit-zero remains a non-processing safety check. |
| **Lessons Learned** | Recovery defaults must be revisited when the user rejects the fallback path. Queue detection should follow the project’s seed source (`attachedfile.csv`) rather than hard-coded filename fragments. |
| **Prevention** | Keep a lightweight pending-detection smoke check for the IATF video factory that compares `attachedfile.csv` against `iatf_system/db/documents` before long-running video generation. Use `IATF_VIDEO_RENDER_MODE=slides` only as an explicit opt-in. |
