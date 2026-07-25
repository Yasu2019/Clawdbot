# CAE North Star & Meaning Gate Protocol (T019)

**Status:** CANONICAL -- applies to **all** agent activity, not only moldflow.  
**Priority:** P0 -- same tier as IATF gate enforcement (T018).  
**Beads:** `Clawdbot_Docker_20260125-3z1` / memory key `cae-north-star-t019`

---

## 1. North Star (final goal -- never lose sight)

Deliver **progressive-die (順送金型) development** where the stack can, from **user-supplied press-part 3D models**, run:

| Pillar | Tool / domain | Outcome |
|--------|----------------|---------|
| Injection / cavity fill | **Moldflow-class** VOF (interFoam, closed cavity, pack) | Fill fraction, short shot, pack window -- not duct laminar proxies |
| Tolerance / stack-up | **Cetol 6 Sigma-class** | Defensible tolerance chains on real assemblies |
| Press forming | **OpenRadioss** (and related) | **Bending** and **blanking** analysis executed correctly on real geometry |

Every second of automation must move one of these pillars forward. Activity that does not is **waste** until reframed or stopped.

---

## 2. Meaning Gate (mandatory before any CAE / fleet / Telegram / loop work)

### 2.1 Moldflow video visual gate (mandatory, fail-closed)

Before sending any Moldflow/OpenFOAM fill animation to Telegram, the sender MUST:

1. Extract representative start, middle, and end frames from the candidate video.
2. Run the local visual checker first (no cloud/API call by default).
3. Confirm the frames show the canonical 3-D cavity geometry, the configured gate, and monotonic VOF resin-fill progression.
4. Match the video manifest/case hash to the approved STL and run.
5. Suppress delivery when the local check fails, is ambiguous, or the manifest/hash is missing. A cloud/API visual check is an optional fallback only and never overrides a failed geometry/hash check.

Legacy flat-plate, 2-D `|U|`, stale-queue, or otherwise unproven videos MUST NOT be sent.

Answer **in writing** (plan, handover, or issue comment) before starting or continuing:

1. **Physical truth:** What phenomenon are we modeling (e.g. closed-cavity VOF fill vs thin-duct icoFoam)?
2. **Category / solver match:** Does `category`, `solver_binary`, and `physics_category` match that phenomenon?
3. **Metric / artifact:** What KPI or artifact proves progress toward the North Star?
4. **Anti-pattern check:** Is this a meaningless repeat (wrong category, 2D |U| for molding, dry-run theater, Telegram noise)?
5. **Self-growth:** What will we **remember** (T019, ByteRover, bd) if we learn something this session?

**Fail-closed:** If (1) or (2) fails, **do not** run loops, send Telegram visuals, or burn GPU until corrected.

---

## 3. Incident T019 (2026-06-02) -- resin_flow vs cavity fill

| What happened | Why it was meaningless |
|---------------|-------------------------|
| LAVIE 24/7 loop on `resin_flow` | `resin_flow_v001` = rectangular duct **icoFoam** laminar flow |
| ParaView 2D **\|U\|** to Telegram | Not injection molding; not fill fraction; not actionable for die design |
| User asked for cavity fill + 3D video | Agent optimized **delivery format** before validating **physics target** |

**Root cause (5Why summary):**

1. Why useless Telegram? -- Sent |U| snapshots, not VOF fill.
2. Why |U|? -- Default ParaView path for OpenFOAM SUCCESS.
3. Why wrong OpenFOAM case? -- Allocation pinned to `resin_flow`.
4. Why pinned? -- Overrides / inertia; no Meaning Gate on category.
5. Why no gate? -- No enforced check: category vs North Star.

**Corrective actions (implemented):**

- `lavie_te_allocation_overrides.json` -> `resin_fill_cad` + `resin_fill_closed_pack`
- `_openfoam_skip_paraview()` in `cae_te_engine.py`; env off on LAVIE remote trial
- Telegram: **3D VOF fill MP4** (and OpenRadioss von Mises MP4 on K10) only; delete after send
- LAVIE fill video: **K10 pull render** (`lavie_cae_video_support.py`) after SUCCESS; engine on `host=lavie` does not send fill MP4 (INC-089)
- **Never `docker compose down` on LAVIE** to fix the job worker -- use `lavie_restart_job_worker_only.ps1` (OpenFOAM/OpenRadioss must not stop even 1s)

---

## 4. Forbidden patterns (all activities)

- Running T&E loops on a category that does not match the stated user goal
- Telegram / dashboard outputs that look busy but do not measure North Star KPIs
- Repeating FAILED trials without changing hypothesis (category, params, or code)
- **SUCCESS without per-trial evolution** (identical params+KPI fingerprint vs prior trial on same track) -- see **P026**
- **FEM Impact cache-only SUCCESS** (`SKIP_RECOMPUTE` / reused VTK) without KPI delta
- **Moldflow VOF SUCCESS** when `fill_complete=false` (short shot)
- Treating "loop is running" as success without fill %, pack ratio, shear zone, or tolerance evidence
- Skipping `trouble_history.md` **[T019]** and this doc when touching CAE, LAVIE, K10 fleet, or moldflow

---

## 5. Required patterns

| When | Read |
|------|------|
| Session start (CAE/fleet) | `data/workspace/memory/trouble_history.md` **[T019]** |
| Before LAVIE/K10 loop change | `data/workspace/lavie_te_allocation_overrides.json` + this doc |
| Before Telegram CAE visual | Confirm VOF MP4 or OR von Mises MP4 -- not legacy |U| for mold |
| LAVIE moldflow SUCCESS + video | K10 loop -> `send_fill_video_after_success` (worker probe; K10 pull if no ffmpeg) |
| After incident or policy change | `bd remember --key cae-north-star-t019` + `brv curate` |

---

## 6. Self-growth checklist (every session)

- Did this session add a **durable** memory (bd / ByteRover / T019 section)?
- Did we **stop** or **fix** a meaningless loop?
- Can we cite **one number** closer to North Star (fill %, pack ratio, blanking KPI, tolerance mm)?

---

*Last updated: 2026-06-02 JST*
