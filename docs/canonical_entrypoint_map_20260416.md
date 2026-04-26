# Canonical Entrypoint Map

Date: 2026-04-16
Status: active routing reference
Purpose: define the 1-to-1 mapping between operator intent and the starting surface

## 7-Domain Functional Structure

To reduce ambiguity, all tasks and tools are grouped into 7 canonical domains. Each domain has one primary "First Click" surface.

| Domain | Primary Entry Point (Canonical) | Purpose |
|---|---|---|
| **1. Operations** | `apps/operations_toolbox/index.html` | Maintenance, repair, system health, cleanup |
| **2. Quality** | `http://localhost:3004/users/sign_in` | IATF compliance, Audit, business data |
| **3. Geometry** | `apps/three_d_workbench/index.html` | CAD (DXF/STEP/3D), GD&T, folder-first workflows |
| **4. CAE** | `apps/radioss_hub/index.html` | Simulation, solvers (Radioss, Elmer, Impact), dynamics |
| **5. Ingestion** | `apps/ingestion_rag_control_center/index.html` | Gmail/Paperless status, RAG observability |
| **6. Learning** | `apps/learning_memory/index.html` | Agent patterns, autonomous growth memory, strategy scout |
| **7. Content** | `apps/video_factory/index.html` | Video generation, eBooks, note drafting, AI art |

## "Start Here" Logic

- **Conversational**: Start at `OpenClaw Chat (AI)`.
- **File-driven**: Start at `Inbox Uploader`.
- **Status-driven**: Start at `Ingestion / RAG Control Center`.
- **Project-driven**: Start at the relevant domain hub.

## Sub-Entry Points

### Operations
- `data/workspace/apps/system_role_map/index.html` (Reference)
- `data/workspace/apps/codex_protocol_hub/index.html` (Governance)

### Quality
- `data/workspace/apps/qms_audit/index.html` (Audit Protocol)
- `http://localhost:8090` (Quality Dashboard)

### Geometry
- `data/workspace/apps/tolerance_hub/index.html` (Specialized)
- `data/workspace/apps/gdt_overlay_studio/index.html` (GD&T)
- `data/workspace/apps/dxf_fcstd_protocol/index.html` (DXF Handoff)

### CAE
- `apps/molding_hub/index.html` (Specialized)

### Ingestion
- `data/workspace/apps/email_search/index.html` (Deep dive)
- `data/workspace/ingest_dashboard.html` (Legacy monitor)

## Guidelines for Addition

Do not add a new top-level card to the Portal unless it clearly owns a new domain or is a high-frequency action that doesn't fit into the existing 7 hubs. Prefer adding sub-links within the domain hubs.
