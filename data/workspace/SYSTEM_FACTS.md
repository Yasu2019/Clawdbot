# 📘 Clawstack V2 System Manual (SYSTEM_FACTS.md)

**Version:** 2.0 (2026-02-08)
**Target Audience:** Clawdbot (Autonomous Agent) & System Administrators

---

## 1. 🏗️ System Architecture

Clawstack V2 is a Docker-based autonomous engineering platform running on a high-spec Windows Host.

### 1.1 Hardware Context

- **Host:** Windows 11 (WSL2 Backend)
- **CPU:** Intel Core i9-13900HK
- **RAM:** 48GB (DDR5)
- **GPU:** Integrated (Iris Xe) - *LLMs run on CPU/RAM*

### 1.2 Docker Service Mesh

| Service | Internal DNS | Port | Role |
|:---|:---|:---|:---|
| **antigravity** | `antigravity` | 5678 | **Core Logic.** Python, R, FreeCAD, Blender, Physics. |
| **ollama** | `ollama` | 11434 | **AI Engine.** Hosting Local LLMs. |
| **postgres** | `postgres` | 5432 | **Long-Term Memory.** Structured Data. |
| **redis** | `redis` | 6379 | **Short-Term Memory.** Job queues, Cache. |
| **paperless** | `paperless` | 8000 | **Document Input.** OCR & Email ingestion. |
| **nodered** | `nodered` | 1880 | **IoT Logic.** Visual automation flows. |
| **mosquitto** | `mosquitto` | 1883 | **IoT Broker.** MQTT (Sensor Data). |
| **quality_dashboard**| `quality_dashboard`| 8090 | **Visualization.** Streamlit UI. |

---

## 2. 🧠 Intelligence Strategy (Autonomous Delegation Architecture)

To maximize performance and capabilities without exhausting API budgets, the system uses a 3-tier approach.

### 2.1 Coordination & Chat (The "Coordinator")

- **Model:** `Google Gemini 2.5 Flash` (Cloud via OpenClaw Gateway)
- **Role:** Real-time conversational interface, task delegation, and progress reporting.
- **Resource Usage:** Free Tier Cloud API (Rate Limit: 20/day).

### 2.2 Internal Engineering Team (The "Specialist")

- **Model:** `Qwen2.5-Coder:32B` & `DeepSeek-R1` (Local GPU via `/work/scripts/ask_specialist.py`)
- **Role:** Heavy lifting, writing complex Python/R scripts, CAE protocol block generation, and processing local IP data.
- **Resource Usage:** Local VRAM (up to 25GB) - **Unlimited & Free**.

### 2.3 Edge Reasoning & Host Advisory (The "Consultants")

- **Models:**
  - `Host Antigravity` (Gemini Advanced outside Docker) -> **Strategic Consultant** for human-to-AI planning.
  - `ChatGPT Plus` (Codex CLI via Container) -> **Last Resort Fallback** for extreme physics simulation troubleshooting.
- **Resource Usage:** Google Workspace & ChatGPT Plus quotas.

---

## 3. 💾 Data & Memory

### 3.1 File System

- **`/work`**: The **ONLY** workspace for temporary files, scripts, and simulation outputs.
- **`/data/paperless/consume`**: Input folder for documents/emails.
  - *Host Path:* `D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\email`

### 3.2 Database Schema (PostgreSQL)

*See `data/workspace/clawdbot_schema.sql` for details.*

1. **`action_items`**: Tracks requests extracted from emails/chat.
    - *Columns:* Requester, Assignee, Request, Due Date, Status (Open/Closed).
2. **`quality_issues`**: Tracks QIF/PIF reports.
    - *Columns:* Issue Type, Details, Issuer, Status.
3. **`meeting_records`**: Summaries of meetings.
    - *Columns:* Organizer, Decisions, Action Items.

---

## 4. 🛠️ Operational Capabilities

### 4.1 Engineering (CAD/CAE)

- **FreeCAD (Headless):** Can generate 3D models and perform 3D tolerance analysis via Python scripts (`freecadcmd`).
- **OpenRadioss:** Can run explicit dynamics simulations (Crash/Drop test).
- **ElmerFEM:** Can run implicit FEA (Heat/Stress).
- **OpenFOAM:** Can run CFD simulations (Fluid Dynamics).

### 4.2 Quality Assurance (QA)

- **Statistical Analysis:** R (`SixSigma`, `qcc`) for Control Charts, ANOVA, Capability Analysis (Cpk).
- **FMEA:** Automated generation and risk scoring via Quality Dashboard.

### 4.3 IoT & Automation

- **Sensor Monitoring:** Node-RED flows capture MQTT data (Temp/Vibration) -> Store to DB -> Alert if OOC (Out of Control).
- **Email Processing:** Paperless ingest -> LLM Parse -> DB Insert -> Daily Report.

### 4.4 Knowledge Ingestion (RAG)

- **IATF Standards:** Watches `/data/paperless/consume/IATF_documents`.
- **Process:** Extracts text -> Embeds with `nomic-embed-text` -> Stores in **Qdrant** (`iatf_knowledge`).
- **Usage:** Retrieve standard clauses during chat or FMEA analysis.

### 4.5 Cost Monitoring

- **Script:** `scripts/check_billing.py` (Python)
- **Role:** Fetches daily API costs from Google Cloud via Service Account.
- **Reporting:** Included in Nightly Report.
- **Usage:** `docker exec -it clawstack-antigravity-1 python3 /work/scripts/check_billing.py`

### 4.6 Search Knowledge (RAG CLI)

- **Script:** `/work/scripts/query_iatf.py`
- **Role:** Queries the Qdrant knowledge base (using `nomic-embed-text`) and answers via `qwen2.5-coder`.
- **Usage:**

  ```bash
  docker exec -it clawstack-antigravity-1 python3 /work/scripts/query_iatf.py "MSA 1 person methodology?"
  ```

### 4.7 Sequential Press Mechanism (Progressive Die)

- **Feed Method:** Sensor-based detection of punched edge -> Feed 1 pitch.
- **Error Characteristics:**
  - Theoretically reduces cumulative error compared to mechanical feed.
  - However, sensor accuracy and gear backlash are unknown variables.
  - **Tolerance Strategy:** Treat as "Cumulative Error" (Worst Case) until proven otherwise.

### 4.8 Advanced Reasoning (Claude CLI)

- **Command:** `claude` (Docker container: `clawstack-antigravity-1`)
- **Version:** `2.1.42`
- **Role:** Complex problem-solving, nuanced understanding, in-depth analysis (Tier 2).
- **Usage Examples:**

  ```bash
  docker exec -it clawstack-antigravity-1 claude -p "Are you ready?"
  docker exec -it clawstack-antigravity-1 claude -f /path/to/document.txt -p "Summarize this document and identify key risks."
  ```

---

## 5. 📜 Protocols & Promises

Ref: `clawdbot_protocol_v2.md` & `PROMISES.md`

- **P004 (Local First):** Always maximize local compute before asking for Cloud API.
- **P015 (Self-Correction):** Attempt 3 fixes before giving up.
- **P016 (Email Report):** Generate the 3-part Email Summary Report daily.

---
*End of Manual*
