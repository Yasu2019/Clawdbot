# DXF2STEP Combined Geometry QC Checklist (mandatory)



> **Incident:** INC-124 / INC-125  

> **Trouble:** [T039] [T040] `data/workspace/memory/trouble_history.md`  

> **Beads:** `bd remember --key dxf2step-s11-multiview-overlap-inc124`, `dxf2step-combined-geometry-inc125`  

> **Protocol:** `docs/dxf2step_quality_gate_protocol.md`  

> **Full report:** `quality_incident_report_20260620_dxf2step_combined_geometry_inc125.md`



## Before extrude (layout / layer skip)



| # | Check | Pass criteria | Fail action |

|---|--------|---------------|-------------|

| DXF-QC02 | Layout layer bbox | Skip **A4** 208x293, **A3** 420x297, **A2** 594x420 before extrude | `extrude_frame_layers_skipped` in build_log |

| DXF-QC02b | Area ratio (legacy) | No layer area > **20x** smallest part-profile layer | Drop in `_frame_layers_to_skip` / `_filter_frame_layers` |



## Before / during profile extraction



| # | Check | Pass criteria | Fail action |

|---|--------|---------------|-------------|

| DXF-QC04 | Same-layer auxiliary views | **One** primary island on TOP layer (side views removed) | `_keep_largest_connected_cluster`; log `auxiliary_clusters_dropped` |

| DXF-QC04b | P46-class vertical column | Dominant **X column** segments + arcs kept (no open loop) | Do not drop arcs outside largest bbox-only island |

| DXF-QC04c | Closed outer plate + holes | `line_to_hole_bbox_ratio >= 1.20` when CIRCLE>=3; block punch extrude | `closed_loop_qc_failures` in build_log; verdict FAILED (INC-132 P20) |

| DXF-QC04d | Profile+hole layer split | Merge outline from skipped frame layer into hole layer | `profile_hole_layer_merge` in build_log (P20 layer 1+13) |

| DXF-QC04e | Through-hole cut | CIRCLE wires cut from plate solid; `holes_cut>=1` when CIRCLE>=3 | `hole_cut_qc_failures`; verdict FAILED (INC-132 P20 punch studs) |



## Multiview reconstruction



| # | Check | Pass criteria | Fail action |

|---|--------|---------------|-------------|

| DXF-QC10 | Layer bbox ratio | No layout layer in multiview pairing | `reconstruction_frame_layers_dropped` |

| DXF-QC10b | View semantics | Front/top/right = **same part**, not title block / sheet | Manual `--view-assignments` or skip multiview |

| DXF-QC10c | Layer count | 2+ valid part layers OR 1 -> single_profile | `_export_single_layer_combined` |

| DXF-QC07 | Multiview fallback | If intersect fails, promote **smallest non-layout** successful layer | `reconstruction_status=single_profile_extrude` |



## After combined STEP / PNG



| # | Check | Pass criteria | Fail action |

|---|--------|---------------|-------------|

| DXF-QC11 | TOP VIEW silhouette | **One** primary closed outline (no second unrelated rectangle/profile) | `verdict=FAILED`, NG registry, no Telegram SUCCESS |

| DXF-QC09 | Audit registry | Latest trial passes `audit_dxf2step_combined_geometry.py` | `GEOMETRY_NG` on dashboard; exclude from best trial |

| DXF-QC12 | `reconstruction_status` | Not `compound_fallback`; `combined_quality_ok=true` | Block downstream CAE/Moldflow |

| DXF-QC13 | `primary_fcstd` | `combined.FCStd` or named **part** layer (not frame/sheet) | Fix archive primary before handoff |

| DXF-QC14 | Manifest bbox | Sheet thickness plausible (not 100mm+ length as Lz for busbar) | Review orientation / wrong combine |

| DXF-QC15 | Front/Right PNG | **HLR visible edges** via `TechDraw.projectEx` (0-6); not raw wireframe | Hidden (7-9) omitted |

| DXF-QC17 | Outer profile vs holes | Adjudicate **disconnected outer outlines** only; CIRCLE / inner cutouts = machining | False GEOMETRY_PARTIAL_OK on hole-heavy busbar (INC-131) |

| DXF-QC18 | Original DXF visual gate | Agent or user **eyeballs** `original_dxf.png` before formal_adjudication / Telegram OK | Blind automation; wrong island narrative |
| DXF-QC18b | Local vision LLM compare | Ollama VL compares `original_dxf.png` vs `combined_views.png`; save `dxf2step_visual_llm_review.json` | DXF/3D mismatch undetected before Telegram |



## Forbidden (INC-124 / INC-125)



- `layers=2/2` + `combined=True` alone as SUCCESS

- Ship `combined.FCStd` when TOP VIEW shows overlapping unrelated outlines

- Use frame/sheet layer as front view in multiview

- Promote layout layer to combined when part layer succeeded

- Skip audit after `dxf2step_worker.py` changes



## Agent pre-work (mandatory)



1. Read `trouble_history.md` **[T039]** + **[T040]**

2. Read this checklist

3. After worker change: smoke P38 + P4 + P46 @10mm + full audit



## Evidence archive (per trial)



- `combined_views.png` -- visual gate

- `build_log.json` -- `extrude_frame_layers_skipped`, `auxiliary_clusters_dropped`, `reconstruction_status`, `combined_quality_ok`

- `reconstruct_multiview.py` -- view map audit (if multiview attempted)



## Reference trials



| Trial | Verdict | Note |

|-------|---------|------|

| `tp-dxf-9d04f260` | **NG** | S11 double TOP -- do not use |

| `tp-dxf-dc852457` | **OK** | S11 frame dropped |

| `tp-dxf-5941a119` | **NG** | P38 frame+part+side view |

| `tp-dxf-8e205f0e` | **OK** | P38 fixed @10mm |

| `tp-dxf-1c5a1c9d` | **OK** | P4 A3 sheet skip + fallback |

| `tp-dxf-fcf3cc4c` | **OK** | P46 X-column filter |

| `tp-dxf-0430c2ca` | **OK** | D3 busbar; holes != islands (INC-131) |

| `tp-dxf-959d5e60` | **NG** | D3 true 3-outline multi-layout (INC-130) |


