# Satellite CAE One-Shot Runbook (SJP v2)

> **Purpose:** K10 orchestrator + LAVIE (and future satellites) CAE trial delegation with **one-pass success**, based on failures observed 2026-05-31.  
> **Canonical policy:** `data/workspace/cae_workload_router.yaml` + `data/workspace/lavie_node_registry.json`  
> **Beads:** track follow-ups with `bd create` / link `discovered-from:Clawdbot_Docker_20260125-3yz`

---

## 0. Architecture (current)

| Host | Tailscale IP | Role |
|------|--------------|------|
| **K10** | `100.119.18.40` | Orchestrator, heavy OpenRadioss, DXF/FreeCAD, growth DB |
| **LAVIE** | `100.87.244.46` | Satellite: job worker `:5680`, OpenFOAM offload, light OpenRadioss |
| **K3** | (company LAN) | n8n schedules, IATF (not CAE satellite yet) |

**Adding a 3rd PC:** copy pattern in Section 8.

---

## 1. Known failures and fixes (do not repeat)

| # | Symptom | Root cause | Fix |
|---|---------|------------|-----|
| F1 | `unsupported type: cae_trial` | Old `lavie_job_worker.py` still running | Copy scripts + **restart worker** (Ctrl+C then start) |
| F2 | `unsupported type: cae_trial` | Only CAE `.py` copied, not worker | Sync **full** `C:\lavie_usb_pack\scripts\` |
| F3 | `ModuleNotFoundError: scipy` | LAVIE Python minimal | Use lazy-import `cae_te_engine.py` OR `pip install numpy scipy psutil` on LAVIE |
| F4 | `PREGATE_FAIL` missing case dir | `experiments/` not on LAVIE `E:` | Run `k10_sync_cae_experiments_to_lavie.py` from K10 |
| F5 | docker compose BOM error | UTF-8 BOM in `.env` | `utf-8-sig` reads + `lavie_repair_env.ps1` |
| F6 | K10 dispatch FAIL but worker OK | `SATELLITE_JOB_TOKEN` mismatch | Same token in K10 `.env` and `C:\clawstack_satellite\.env` |
| F7 | Restart kills HTTP job | Worker killed mid-request | Use `lavie_restart_remote.ps1` (detached, 5s delay) |
| F8 | Router sends resin_flow to K10 only | Old `heavy_categories` | Use `lavie_openfoam_categories` in router yaml |
| F9 | Portal shows old maturity only | SJP not in Portal | Read `satellite_cae_live_status.json` on Portal |
| F10 | OpenFOAM real run FAIL on LAVIE | `opencfd/openfoam-dev` image not pulled | On LAVIE: `docker pull opencfd/openfoam-dev:latest` (dry-run OK without) |
| F11 | parallel FAIL WinError 5 | K10 OR + LAVIE OF write `cae_te_log.json` same time | Fixed: merge retry in `k10_satellite_cae_dispatch.py` |
| F12 | DXF2STEP gap WARN api offline | Host API not running on `:8002` | `powershell -File scripts\start_dxf2step_api.ps1` |

---

## 2. One-shot success procedure (K10)

Run **in order**. Stop on first FAIL.

### Phase A -- K10 prep (2 min)

```powershell
cd D:\Clawdbot_Docker_20260125

# A1 Token present
Select-String -Path .env -Pattern "^SATELLITE_JOB_TOKEN="

# A2 Router + registry
python scripts\cae_workload_router.py --probe-lavie-jobs --json
python scripts\cae_workload_router.py --category resin_flow --json
# expect: host=lavie for OpenFOAM offload

# A3 Live status file refresh
python scripts\update_satellite_cae_live_status.py --json
```

### Phase B -- Push scripts + workspace to LAVIE (5 min)

```powershell
# B1 Scripts (Tailscale HTTP zip)
python scripts\k10_sync_lavie_scripts_to_lavie.py --build-pack

# B2 CAE experiments (13 files, ~16KB)
python scripts\k10_sync_cae_experiments_to_lavie.py

# B3 Boost + detached restart (optional after config change)
python scripts\k10_lavie_boost_and_restart.py --skip-sync
# wait ~45s, expect: LAVIE worker online
```

### Phase C -- Verification gates (3 min)

```powershell
python scripts\k10_verify_satellite_node.py --node-id lavie --ip 100.87.244.46
python scripts\k10_satellite_dispatch.py --probe --node lavie
python scripts\k10_satellite_cae_dispatch.py --category press_blanking --dry-run --host lavie
python scripts\k10_satellite_cae_dispatch.py --category resin_flow --dry-run --host lavie
# expect: verdict=DRY_RUN, RESULT: PASS

python scripts\k10_parallel_cae_orchestrator.py --dry-run --or-max-trials 1 --of-max-trials 1
# expect: RESULT: PASS
```

### Phase D -- Portal + logs (1 min)

```powershell
python scripts\update_satellite_cae_live_status.py
start http://localhost:8088/portal.html
# Check "Satellite CAE Live" panel (green = OK)

# Logs
Get-Content data\workspace\parallel_cae_log.jsonl -Tail 1
Get-Content data\cae_te_workspace\results\cae_te_log.json -TotalCount 40
```

### Phase E -- Production parallel CAE (when ready)

```powershell
# LAVIE: docker pull opencfd/openfoam-dev:latest  (once)

python scripts\k10_parallel_cae_orchestrator.py `
  --or-category press_blanking `
  --of-category resin_flow `
  --or-max-trials 3 `
  --of-max-trials 3
```

---

## 3. LAVIE manual checklist (only if remote sync fails)

1. Docker Desktop running  
2. Worker: `powershell -ExecutionPolicy Bypass -File C:\lavie_usb_pack\scripts\lavie_start_job_worker.ps1`  
3. Confirm: `Select-String C:\lavie_usb_pack\scripts\lavie_job_worker.py -Pattern cae_trial`  
4. Docker Desktop Resources: CPUs 6+, Memory 24GB+  
5. Jobs on **E:** `E:\clawstack_satellite\data\work\jobs` (not C:)

---

## 4. File map

| Path | Purpose |
|------|---------|
| `scripts/lavie_job_worker.py` | SJP worker (`shell`, `docker`, `cae_trial`) |
| `scripts/k10_satellite_cae_dispatch.py` | Single trial K10 or LAVIE |
| `scripts/k10_parallel_cae_orchestrator.py` | OR@K10 + OF@LAVIE parallel |
| `scripts/k10_sync_cae_experiments_to_lavie.py` | experiments/ sync |
| `scripts/k10_sync_lavie_scripts_to_lavie.py` | scripts/ sync |
| `scripts/k10_lavie_boost_and_restart.py` | Boost + restart |
| `scripts/update_satellite_cae_live_status.py` | Portal JSON |
| `data/workspace/satellite_cae_live_status.json` | Portal live panel |
| `data/workspace/cae_workload_router.yaml` | Routing rules |
| `data/workspace/lavie_node_registry.json` | LAVIE endpoints |

---

## 5. Routing rules (efficient parallel)

- **OpenRadioss heavy:** K10 (`press_drawing`, `progressive_strip_layout`)  
- **OpenFOAM:** LAVIE when `lavie_openfoam_categories` + worker online  
- **Light OpenRadioss:** LAVIE when K10 RAM high (optional)  
- **DXF / Cetol proxy:** K10 gap jobs (not LAVIE docker stack)

---

## 6. Security

- Never commit or paste `SATELLITE_JOB_TOKEN` in chat/docs  
- USB pack includes `.env` -- treat as secret media  
- Tailscale only; no public port forward for `:5680`

---

## 7. Troubleshooting quick table

| Error | Command |
|-------|---------|
| worker offline | `python scripts\k10_satellite_dispatch.py --probe --node lavie` |
| cae_trial unsupported | Re-sync scripts + restart worker on LAVIE |
| PREGATE_FAIL case dir | `python scripts\k10_sync_cae_experiments_to_lavie.py` |
| unauthorized 401 | Fix token match K10/LAVIE `.env` |
| OpenFOAM docker fail on LAVIE | `docker pull opencfd/openfoam-dev:latest` on LAVIE |

---

## 8. Adding a new satellite PC (e.g. PC-3)

1. Copy `dist/lavie_usb_pack` to `C:\clawstack_satellite` on new PC  
2. Run `lavie_setup.bat` + start job worker  
3. Note Tailscale IP  
4. Create `data/workspace/<node_id>_node_registry.json` (copy lavie template)  
5. Add block under `cae_workload_router.yaml`:

```yaml
satellites:
  pc3:
    enabled: true
    ip: "100.x.x.x"
    job_worker_port: 5680
```

6. Extend `pick_host()` categories for pc3 (future script change)  
7. Run Phase C probes with `--node pc3`  
8. Sync experiments to new PC work dir via adapted sync script  

---

## 10. SJP-3 (gap jobs on K10)

While OpenRadioss@K10 + OpenFOAM@LAVIE run, K10 can execute **short gap jobs** in parallel:

| Job | Domain | Script |
|-----|--------|--------|
| Cetol 6σ proxy | `TOLERANCE_ANALYSIS` | `k10_gap_job_runner.py --jobs tolerance` |
| DXF→3D readiness | `DXF2STEP` | `k10_gap_job_runner.py --jobs dxf2step` |

```powershell
# Gap jobs only
python scripts\k10_gap_job_runner.py --jobs tolerance,dxf2step

# Full SJP-3 parallel (OR + OF + gap)
python scripts\k10_parallel_cae_orchestrator.py --dry-run --sjp3 --or-max-trials 1 --of-max-trials 1
```

Log: `data/workspace/sjp3_gap_log.jsonl`

**DXF2STEP API (K10 host, port 8002):**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_dxf2step_api.ps1
curl http://127.0.0.1:8002/api/dxf2step/health
```

Note: Docker `dxf3d_app` on `:8003` is Streamlit UI, not this REST API.

---

## 11. LAVIE n8n recovery (:5679 exec_bridge)

If A3 fails but job worker `:5680` is OK:

```powershell
# Sync lavie_n8n_restart.ps1 to LAVIE first
python scripts\k10_sync_lavie_scripts_to_lavie.py

# Restart n8n docker + redeploy exec_bridge from K10
python scripts\k10_lavie_n8n_recover.py

# Or full verify (auto-recover on A3 fail)
powershell -ExecutionPolicy Bypass -File scripts\k10_satellite_verify_all.ps1
```

**K10 Tailscale firewall (LAVIE -> K10 `k10_exec_bridge`, run once as Admin on K10):**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\open_k10_n8n_tailscale_firewall.ps1
python scripts\k10_verify_satellite_node.py --node-id lavie --ip 100.87.244.46
```

---

## 9. Related docs

- [LAVIE_K10_INTEGRATION.md](LAVIE_K10_INTEGRATION.md)  
- [K3_LAVIE_IATF_INTEGRATION_SUMMARY.md](K3_LAVIE_IATF_INTEGRATION_SUMMARY.md)  
- [LAVIE_TRIAL_DAY_CHECKLIST.md](LAVIE_TRIAL_DAY_CHECKLIST.md) (Phase 1 historical)

---

*Last updated: 2026-05-31 (SJP-2/3 + n8n recover + Portal live status)*
