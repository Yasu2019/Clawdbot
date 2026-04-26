# Clawstack Canonical Application Mapping (Apr 2026)

This document defines the canonical 6-zone structure and the applications within each zone.

## ZONE 1: AI COCKPIT (CORE AGENT)
- **Agent Cockpit**: Primary VNC interface to the autonomous engineer (Gateway 1).
- **LiteLLM Admin**: Management of the 10+ local and cloud models.
- **System Role Map**: Definition of AI agent identities and permissions.

## ZONE 2: ENGINEERING & DESIGN
- **Three-D Workbench**: 3D launcher for Blender/Three.js assets.
- **DXF2STEP**: Primary geometry conversion pipeline.
- **DXF_FCStd Protocol**: Feature-based modeling over DXF.
- **GD&T Overlay Studio**: Visual annotation of technical drawings.
- **Tolerance Hub**: Gap analysis and manufacturing tolerances.
- **3D Fab-Forge**: Integrated 3D printing and prototyping hub.
- **Kinematics Hub**: Motion simulation and robotic assembly planning.
- **Molding Hub**: Specialized tooling and injection molding analysis.
- **Radioss Hub**: High-performance FEA/Crash simulation.

## ZONE 3: QUALITY & AUDIT HUB
- **Quality Insights**: Main dashboard for inspection metrics.
- **Visual QA (Image2QA)**: AI-driven audit photo analysis and education.
- **QMS Audit**: IATF 16949 compliance and checklist management.
- **Stitch UI Evaluation**: Visual verification of front-end components.

## ZONE 4: KNOWLEDGE & RAG HUB
- **Knowledge Hub**: Central RAG interface for company documents and emails.
- **Ingestion Control Center**: Real-time monitor for Gmail & Paperless ingestion.
- **Paperless-ngx**: Legal and archival document management.
- **Inbox Uploader**: Manual asset upload to the RAG pipeline.
- **Pub Hub**: Publishing and technical manual distribution.

## ZONE 5: AUTOMATION & OPS
- **Node-RED**: Real-time event orchestration.
- **n8n Automation**: High-level workflow orchestration and API integration.
- **Observability Hub**: System-wide health, CPU/Mem, and Docker monitoring.
- **Operations Toolbox**: One-off scripts and recovery tools.
- **File Sync (Rclone)**: Differential mirroring of corporate servers.
- **Auto Repair Console**: Self-healing protocol manager.
- **Workspace Agents Hub**: Production safety guards (SQL/HITL) and QA analysis.

## ZONE  zone 6: CREATIVE STUDIO
- **Creative Studio**: Master hub for AI video and scripts.
- **Auto LP Generator**: automated landing page and documentation creation.
- **AI Video Engine**: Staged pipeline for cinematic generation.
- **Audio Lab**: Voice-over and sound effect generation.
- **Mini-Game Factory**: WebGL-based educational game creation.

---

## ARCHIVE / LEGACY
- Moved to `apps/_legacy/` to reduce redundancy:
  - `agent_harness_status`, `ai_engineering_harness_status` (Consolidated into Observability Hub)
  - `ai_video_engine`, `video_factory` (Consolidated into Creative Studio)
  - `learning_memory` (Consolidated into Knowledge Hub)
  - `note_pro`, `open_notebook_obsidian` (Consolidated into Knowledge Hub)
  - `kindle_author` (Consolidated into Creative Studio / Pub Hub)
  - `pdca_lab`, `rla_history` (Legacy RL protocols)
