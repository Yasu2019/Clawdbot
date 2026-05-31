# NEC LAVIE -- K10 Integration Runbook

> **全体整理:** [`K3_LAVIE_IATF_INTEGRATION_SUMMARY.md`](K3_LAVIE_IATF_INTEGRATION_SUMMARY.md)

NEC LAVIE is **always powered on**. Satellite under K10: n8n + `exec_bridge`.  
**IATF on K3** (`docs/K3_IATF_MIGRATION.md`). **CAE: K10 primary, LAVIE light offload** via `cae_workload_router.yaml`.

**Trial today:** see **`docs/LAVIE_TRIAL_DAY_CHECKLIST.md`**

## Network (fill in after first boot)

| Host | IP | Port | Notes |
|------|-----|------|-------|
| K10 | `192.168.3.87` | 5679 | `k10_exec_bridge` |
| K3 | `192.168.3.151` | 5679 | existing satellite |
| **LAVIE** | `192.168.3.???` | 5679 | assign fixed DHCP or static |

Record LAVIE IP in `C:\clawstack_satellite\node_status.json` after setup.

## What LAVIE runs vs K10 (hybrid CAE)

| Workload | Host | Reason |
|----------|------|--------|
| **Heavy CAE** (drawing, resin_flow, ...) | **K10** | i9-13900HK, 48GB, faster |
| **Light CAE** (blanking, crushing, ...) | **LAVIE** when K10 RAM high | Offload via router |
| Ollama / heavy LLM | **K10 only** | compose up to 32GB |
| **IATF always-on** | **K3** (`192.168.3.151:3004`) | `K3_IATF_MIGRATION.md` |
| n8n schedules | K3 | triggers K10/LAVIE bridges |
| Remote shell | LAVIE + K3 `exec_bridge` | K10 orchestration |

Router: `scripts/cae_workload_router.py` + `data/workspace/cae_workload_router.yaml`

**One-shot runbook (SJP-2, failures documented):** [`docs/SATELLITE_CAE_ONE_SHOT_RUNBOOK.md`](SATELLITE_CAE_ONE_SHOT_RUNBOOK.md)

### Phase 1 trial (today)

- LAVIE: n8n + exec_bridge only
- K10: register IP with `k10_register_lavie_ip.ps1`

### Phase 2 (after trial)

- Sync `cae_te_workspace` to LAVIE
- OpenRadioss image on LAVIE for light trials

## One-shot setup on LAVIE (today)

### Prerequisites

1. Docker Desktop installed and running
2. Python 3 on PATH (for bridge workflow deploy)
3. Repo on USB or copy: `D:\Clawdbot_Docker_20260125`
4. K10 already has `k10_exec_bridge` and firewall TCP 5679 (done for K3)

### Run (Admin PowerShell recommended)

```bat
cd D:\Clawdbot_Docker_20260125
scripts\lavie_setup.bat
```

Or with explicit IP:

```powershell
.\scripts\lavie_node_setup.ps1 -LanIp 192.168.3.152
```

### What the batch file does

| # | Step |
|---|------|
| 1 | Detect LAN IP |
| 2 | Copy `deploy/satellite_node/` -> `C:\clawstack_satellite\` |
| 3 | Write `.env` (WEBHOOK_URL, K10 bridge URL, n8n password from repo `.env`) |
| 4 | Windows Firewall: allow inbound TCP 5679 (Private) |
| 5 | `docker compose build` + `up -d` (cache used) |
| 6 | Wait for `/healthz` |
| 7 | Deploy **Remote Execution Bridge** workflow |
| 8 | Self-test `exec_bridge` |
| 9 | Write `node_status.json` |

### If n8n owner account is not created yet

First boot may require UI setup:

1. Open `http://<LAVIE_IP>:5679`
2. Create owner: `y.suzuki.hk@gmail.com` / password = repo `.env` `n8n_PW`
3. Re-run bridge only:

```powershell
cd D:\Clawdbot_Docker_20260125
python scripts\satellite_deploy_exec_bridge.py --base-url http://<LAVIE_IP>:5679
```

Or:

```powershell
.\scripts\lavie_node_setup.ps1 -SkipBridge
# ... complete UI ...
.\scripts\lavie_node_setup.ps1 -LanIp <IP>
```

## Verify from K10

```powershell
cd D:\Clawdbot_Docker_20260125
python scripts\k10_verify_satellite_node.py --node-id lavie --ip <LAVIE_IP>
```

Checks:

- LAVIE `/healthz`
- LAVIE `exec_bridge` echo + `docker ps`
- LAVIE -> K10 `k10_exec_bridge` round-trip

Status file: `data/workspace/lavie_node_verify_status.json`

## K10 configuration after LAVIE is live

| Item | Change |
|------|--------|
| Gateway `BROWSER_IATF_URL` | `http://192.168.3.151:3004` (K3) |
| LAVIE router | `k10_register_lavie_ip.ps1` after setup |
| Control scripts | `http://<LAVIE_IP>:5679/webhook/exec_bridge` |

Example probe from K10 Python:

```python
import httpx
LAVIE = "http://192.168.3.????:5679/webhook/exec_bridge"
r = httpx.post(LAVIE, json={"cmd": "docker ps --format table"}, timeout=60)
print(r.json().get("stdout"))
```

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| K10 cannot reach LAVIE :5679 | LAVIE firewall / wrong IP | Re-run setup; check `node_status.json` |
| exec_bridge 404 | Workflow not active | `satellite_deploy_exec_bridge.py` |
| n8n login fail in script | Owner not created | Complete UI setup once |
| docker ps fails in bridge | Docker Desktop stopped | Start Docker on LAVIE |
| LAVIE -> K10 fail | K10 firewall | `open_k10_n8n_firewall.ps1` on K10 |
| ping fail | ICMP blocked | Use TCP tests only |

## Files created for this integration

```
deploy/satellite_node/          # USB-portable package
scripts/lavie_setup.bat         # double-click entry
scripts/lavie_node_setup.ps1    # main installer
scripts/satellite_deploy_exec_bridge.py
scripts/k10_verify_satellite_node.py
docs/K3_NODE_SETUP_PLAYBOOK.md  # K3 lessons + generic pattern
docs/LAVIE_K10_INTEGRATION.md   # this file
```

## Rollback

On LAVIE:

```powershell
cd C:\clawstack_satellite
docker compose down
# remove C:\clawstack_satellite if needed
```

K10 keeps working; K3 schedules unaffected.
