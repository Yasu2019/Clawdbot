---
type: "query"
date: "2026-08-27T21:53:27.342062+00:00"
question: "How should Portal CAE/CETOL/VIAI pages show current status without claiming commercial parity?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["cetol6sigma", "visual_inspection_ai", "portal.html"]
---

# Q: How should Portal CAE/CETOL/VIAI pages show current status without claiming commercial parity?

## Answer

Read live JSON into a FACT bar with timestamps. CETOL: cetol_golden_status.json plus reports age. VIAI is http://127.0.0.1:18010 /api/health and /api/metrics. If a page stays on loading while JSON is HTTP 200, extract the inline script and run node --check (INC-189: duplicate shaft_bearing else after snap_fit). Never call golden 1D stack commercial Cetol, or OpenFOAM fill commercial Moldflow. Canonical docs/knowledge/app_page_fact_bar_cetol_viai_20260827.md INC-189 T082 S033 bd app-page-fact-bar-cetol-viai-20260827.

## Outcome

- Signal: useful

## Source Nodes

- cetol6sigma
- visual_inspection_ai
- portal.html