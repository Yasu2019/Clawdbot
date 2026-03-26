import streamlit as st
import pandas as pd
import subprocess
import json
import urllib.request
import os
import datetime
import shutil
import sys
import pypdf
import docx
import openpyxl

# --- CONFIG ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
QDRANT_URL = "http://qdrant:6333"
WORK_DIR = "/work/qa_reports" # Reports
CONSUME_DIR = "/consume" # Paperless Input

# Subfolders
INGEST_DIR = os.path.join(CONSUME_DIR, "PFMEA_5WHY_FTA_etc")
WIP_DIR = os.path.join(CONSUME_DIR, "WIP")
KINDLE_DIR = os.path.join(CONSUME_DIR, "Kindle")

GEN_MODEL = os.getenv("OLLAMA_GEN_MODEL", "qwen3:14b")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
COLLECTION_NAME = "iatf_knowledge"

for d in [WORK_DIR, INGEST_DIR, WIP_DIR, KINDLE_DIR]:
    os.makedirs(d, exist_ok=True)

st.set_page_config(page_title="Clawstack QA Dashboard", layout="wide")

PLATING_FLAG = os.getenv("ENABLE_PLATING_REFLOW_LAB", "1").lower() not in ("0", "false", "off")
if "/work/scripts" not in sys.path:
    sys.path.append("/work/scripts")

try:
    from plating_quality_analysis import (
        build_initial_case,
        load_defaults as load_plating_defaults,
        load_recent_cases,
        run_analysis as run_plating_analysis,
        save_case as save_plating_case,
        save_uploaded_image as save_plating_uploaded_image,
    )
except Exception:
    build_initial_case = None
    load_plating_defaults = None
    load_recent_cases = None
    run_plating_analysis = None
    save_plating_case = None
    save_plating_uploaded_image = None

# --- UTILS (No external deps) ---

def get_embedding(text):
    try:
        url = f"{OLLAMA_URL}/api/embeddings"
        data = {"model": EMBED_MODEL, "prompt": text}
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'))
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))['embedding']
    except Exception as e:
        return []

def search_qdrant(vector, limit=3):
    try:
        url = f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search"
        data = {"vector": vector, "limit": limit, "with_payload": True}
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            results = json.loads(response.read().decode('utf-8')).get('result', [])
            return "\n\n".join([f"[{r['payload'].get('source', '?')}] {r['payload'].get('text', '')}" for r in results])
    except Exception:
        return "" 

def ask_ai(prompt, context_text=""):
    system_prompt = "You are a Quality Assurance Expert."
    if context_text:
        system_prompt += f"\n\nREFERENCE DOCUMENTS:\n{context_text}\n\nUse these references to answer."
    try:
        data = {"model": GEN_MODEL, "prompt": f"{system_prompt}\n\nTask: {prompt}", "stream": False}
        req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=json.dumps(data).encode('utf-8'))
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8')).get('response', '').strip()
    except Exception as e:
        return f"笞・・AI Offline: {e}"

def extract_text_immediate(filepath):
    """Refactored extraction logic for immediate use"""
    ext = os.path.splitext(filepath)[1].lower()
    text = ""
    try:
        if ext == ".pdf":
            reader = pypdf.PdfReader(filepath)
            for p in reader.pages: text += p.extract_text() + "\n"
        elif ext in [".docx", ".doc"]:
            doc = docx.Document(filepath)
            for p in doc.paragraphs: text += p.text + "\n"
        elif ext in [".xlsx", ".xls"]:
            wb = openpyxl.load_workbook(filepath, data_only=True)
            for s in wb.sheetnames:
                for r in wb[s].iter_rows(values_only=True):
                    text += " ".join([str(c) for c in r if c]) + "\n"
        elif ext == ".txt":
            with open(filepath, "r", encoding="utf-8") as f: text = f.read()
    except Exception as e:
        return f"[Error extracting {ext}: {e}]"
    return text

def save_uploaded_file(uploaded_file, target_folder):
    try:
        file_path = os.path.join(target_folder, uploaded_file.name)
        if os.path.exists(file_path):
            return True, file_path, "Exists"
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True, file_path, "Saved"
    except Exception as e:
        return False, str(e), "Error"


def render_plating_quality_page():
    st.header("Plating Quality Analysis")
    st.caption("Thermal FEM plus reduced-order plating/reflow indicators.")

    required = [
        build_initial_case,
        load_plating_defaults,
        load_recent_cases,
        run_plating_analysis,
        save_plating_case,
        save_plating_uploaded_image,
    ]
    if not all(required):
        st.error("plating_quality_analysis.py could not be loaded. Check /work/scripts.")
        return

    defaults = load_plating_defaults()
    if "plating_case" not in st.session_state:
        st.session_state.plating_case = build_initial_case(defaults)
    if "plating_results" not in st.session_state:
        st.session_state.plating_results = {}
    if "plating_images" not in st.session_state:
        st.session_state.plating_images = []

    case = st.session_state.plating_case
    results = st.session_state.plating_results

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Project", case["project"]["project_name"])
    top2.metric("Stackup", case["project"]["stackup"])
    top3.metric("Status", case["project"]["status"])
    top4.metric("Mode", case["analysis"]["analysis_mode"])

    tab_input, tab_images, tab_result, tab_history = st.tabs(["Inputs", "Assets", "Results", "History"])

    with tab_input:
        left, right = st.columns(2)
        with left:
            st.subheader("Project")
            case["project"]["project_name"] = st.text_input("Project name", case["project"]["project_name"])
            case["project"]["part_number"] = st.text_input("Part number", case["project"]["part_number"])
            case["project"]["revision"] = st.text_input("Revision", case["project"]["revision"])
            case["project"]["material_system"] = st.text_input("Material system", case["project"]["material_system"])
            case["project"]["substrate"] = st.text_input("Substrate", case["project"]["substrate"])
            case["project"]["stackup"] = st.text_input("Stackup", case["project"]["stackup"])
            status_options = ["draft", "ready", "running", "done", "error"]
            status_value = case["project"]["status"] if case["project"]["status"] in status_options else "draft"
            case["project"]["status"] = st.selectbox("Status", status_options, index=status_options.index(status_value))

            st.subheader("Specification")
            case["spec"]["substrate_type"] = st.text_input("Substrate type", case["spec"]["substrate_type"])
            case["spec"]["substrate_grade"] = st.text_input("Substrate grade", case["spec"]["substrate_grade"])
            case["spec"]["substrate_thickness_um"] = st.number_input("Substrate thickness (um)", value=float(case["spec"]["substrate_thickness_um"]), step=10.0)
            case["spec"]["ep_layer_enabled"] = st.checkbox("EP layer enabled", value=bool(case["spec"]["ep_layer_enabled"]))
            case["spec"]["ni_thickness_target_um"] = st.number_input("Ni target thickness (um)", value=float(case["spec"]["ni_thickness_target_um"]), step=0.05, format="%.3f")
            case["spec"]["sn_thickness_target_um"] = st.number_input("Sn target thickness (um)", value=float(case["spec"]["sn_thickness_target_um"]), step=0.05, format="%.3f")
            case["spec"]["ni_sn_max_um"] = st.number_input("Ni-Sn max (um)", value=float(case["spec"]["ni_sn_max_um"]), step=0.1)
            case["spec"]["initial_imc_thickness_um"] = st.number_input("Initial IMC thickness (um)", value=float(case["spec"]["initial_imc_thickness_um"]), step=0.01, format="%.3f")
            case["spec"]["surface_roughness_ra_um"] = st.number_input("Surface roughness Ra (um)", value=float(case["spec"]["surface_roughness_ra_um"]), step=0.01, format="%.3f")
            case["spec"]["plating_side_mode"] = st.selectbox("Plating side mode", ["single", "double"], index=0 if case["spec"]["plating_side_mode"] == "single" else 1)
            case["spec"]["note_spec"] = st.text_area("Notes", case["spec"].get("note_spec", ""), height=80)

        with right:
            st.subheader("Plating")
            case["plating"]["plating_line_type"] = st.text_input("Line type", case["plating"]["plating_line_type"])
            case["plating"]["plating_machine_name"] = st.text_input("Machine name", case["plating"]["plating_machine_name"])
            case["plating"]["plating_bath_name"] = st.text_input("Bath name", case["plating"]["plating_bath_name"])
            case["plating"]["plating_current_density_adm2"] = st.number_input("Current density (A/dm2)", min_value=1.0, max_value=30.0, value=float(case["plating"]["plating_current_density_adm2"]), step=0.1)
            case["plating"]["plating_current_mode"] = st.text_input("Current mode", case["plating"]["plating_current_mode"])
            case["plating"]["plating_line_speed_m_min"] = st.number_input("Line speed (m/min)", value=float(case["plating"]["plating_line_speed_m_min"]), step=0.1)
            case["plating"]["plating_bath_temp_c"] = st.number_input("Bath temp (C)", value=float(case["plating"]["plating_bath_temp_c"]), step=1.0)
            case["plating"]["plating_time_sec"] = st.number_input("Plating time (sec)", value=float(case["plating"]["plating_time_sec"]), step=1.0)
            case["plating"]["agitation_mode"] = st.text_input("Agitation mode", case["plating"]["agitation_mode"])
            case["plating"]["anode_type"] = st.text_input("Anode type", case["plating"]["anode_type"])
            case["plating"]["xrf_measurement_enabled"] = st.checkbox("XRF enabled", value=bool(case["plating"]["xrf_measurement_enabled"]))
            case["plating"]["xrf_points_count"] = st.number_input("XRF points", value=int(case["plating"]["xrf_points_count"]), step=1)
            case["plating"]["thickness_uniformity_index"] = st.number_input("Uniformity index", value=float(case["plating"]["thickness_uniformity_index"]), step=0.1)
            case["plating"]["surface_orientation_note"] = st.text_area("Orientation note", case["plating"]["surface_orientation_note"], height=80)

            st.subheader("Reflow")
            case["reflow"]["reflow_machine_type"] = st.text_input("Machine type", case["reflow"]["reflow_machine_type"])
            case["reflow"]["reflow_machine_name"] = st.text_input("Machine name", case["reflow"]["reflow_machine_name"])
            atm_options = ["air", "nitrogen", "vacuum"]
            atm = case["reflow"]["atmosphere_type"] if case["reflow"]["atmosphere_type"] in atm_options else "air"
            case["reflow"]["atmosphere_type"] = st.selectbox("Atmosphere", atm_options, index=atm_options.index(atm))
            case["reflow"]["o2_ppm"] = st.number_input("O2 (ppm)", value=float(case["reflow"]["o2_ppm"]), step=100.0)
            case["reflow"]["zones_count"] = st.number_input("Zone count", value=int(case["reflow"]["zones_count"]), step=1)
            case["reflow"]["conveyor_speed_mm_min"] = st.number_input("Conveyor speed (mm/min)", value=float(case["reflow"]["conveyor_speed_mm_min"]), step=10.0)
            case["reflow"]["board_or_carrier_type"] = st.text_input("Board/carrier", case["reflow"]["board_or_carrier_type"])
            case["reflow"]["flux_or_residue_condition"] = st.text_input("Flux/residue condition", case["reflow"]["flux_or_residue_condition"])
            case["reflow"]["reflow_repeat_count"] = st.number_input("Reflow repeat count", value=int(case["reflow"]["reflow_repeat_count"]), step=1)
            case["reflow"]["cooling_mode"] = st.text_input("Cooling mode", case["reflow"]["cooling_mode"])

        low_left, low_right = st.columns(2)
        with low_left:
            st.subheader("Temperature Profile")
            case["profile"]["profile_template_name"] = st.text_input("Template", case["profile"]["profile_template_name"])
            case["profile"]["start_temp_c"] = st.number_input("Start temp (C)", value=float(case["profile"]["start_temp_c"]), step=1.0)
            case["profile"]["preheat_target_c"] = st.number_input("Preheat target (C)", value=float(case["profile"]["preheat_target_c"]), step=1.0)
            case["profile"]["preheat_time_sec"] = st.number_input("Preheat time (sec)", value=float(case["profile"]["preheat_time_sec"]), step=5.0)
            case["profile"]["soak_min_c"] = st.number_input("Soak min (C)", value=float(case["profile"]["soak_min_c"]), step=1.0)
            case["profile"]["soak_max_c"] = st.number_input("Soak max (C)", value=float(case["profile"]["soak_max_c"]), step=1.0)
            case["profile"]["soak_time_sec"] = st.number_input("Soak time (sec)", value=float(case["profile"]["soak_time_sec"]), step=5.0)
            case["profile"]["ramp_to_peak_sec"] = st.number_input("Ramp to peak (sec)", value=float(case["profile"]["ramp_to_peak_sec"]), step=5.0)
            case["profile"]["peak_temp_c"] = st.number_input("Peak temp (C)", value=float(case["profile"]["peak_temp_c"]), step=1.0)
            case["profile"]["tal_over_liquidus_sec"] = st.number_input("TAL (sec)", value=float(case["profile"]["tal_over_liquidus_sec"]), step=1.0)
            case["profile"]["liquidus_temp_c"] = st.number_input("Liquidus temp (C)", value=float(case["profile"]["liquidus_temp_c"]), step=1.0)
            case["profile"]["cool_to_temp_c"] = st.number_input("Cool to (C)", value=float(case["profile"]["cool_to_temp_c"]), step=1.0)
            case["profile"]["cool_time_sec"] = st.number_input("Cool time (sec)", value=float(case["profile"]["cool_time_sec"]), step=5.0)
            case["profile"]["ramp_rate_c_per_sec"] = st.number_input("Ramp rate (C/sec)", value=float(case["profile"]["ramp_rate_c_per_sec"]), step=0.1)
            case["profile"]["cool_rate_c_per_sec"] = st.number_input("Cool rate (C/sec)", value=float(case["profile"]["cool_rate_c_per_sec"]), step=0.1)

        with low_right:
            st.subheader("Analysis")
            mode_options = ["plating_plus_reflow_coupled", "reflow_only", "plating_only"]
            mode = case["analysis"]["analysis_mode"] if case["analysis"]["analysis_mode"] in mode_options else mode_options[0]
            case["analysis"]["analysis_mode"] = st.selectbox("Analysis mode", mode_options, index=mode_options.index(mode))
            dim_options = ["1D", "2D", "3D"]
            dim = case["analysis"]["model_dimension"] if case["analysis"]["model_dimension"] in dim_options else "2D"
            case["analysis"]["model_dimension"] = st.selectbox("Model dimension", dim_options, index=dim_options.index(dim))
            solver_options = ["scikit-fem", "pycalphad", "elmer", "openfoam"]
            solver = case["analysis"]["solver_backend"] if case["analysis"]["solver_backend"] in solver_options else "scikit-fem"
            case["analysis"]["solver_backend"] = st.selectbox("Solver backend", solver_options, index=solver_options.index(solver))
            case["analysis"]["use_pycalphad"] = st.checkbox("Use pycalphad", value=bool(case["analysis"]["use_pycalphad"]))
            case["analysis"]["use_scikit_fem"] = st.checkbox("Use scikit-fem", value=bool(case["analysis"]["use_scikit_fem"]))
            case["analysis"]["use_fenicsx_if_available"] = st.checkbox("Use FEniCSx if available", value=bool(case["analysis"]["use_fenicsx_if_available"]))
            case["analysis"]["use_openfoam_if_available"] = st.checkbox("Use OpenFOAM if available", value=bool(case["analysis"]["use_openfoam_if_available"]))
            case["analysis"]["use_calculix_if_available"] = st.checkbox("Use CalculiX if available", value=bool(case["analysis"]["use_calculix_if_available"]))
            case["analysis"]["use_elmer_if_available"] = st.checkbox("Use Elmer if available", value=bool(case["analysis"]["use_elmer_if_available"]))
            case["analysis"]["use_paraview_export"] = st.checkbox("Export ParaView artifacts", value=bool(case["analysis"]["use_paraview_export"]))
            case["analysis"]["mesh_size_um"] = st.number_input("Mesh size (um)", value=float(case["analysis"]["mesh_size_um"]), step=0.01, format="%.3f")
            case["analysis"]["time_step_sec"] = st.number_input("Time step (sec)", value=float(case["analysis"]["time_step_sec"]), step=0.1)
            case["analysis"]["total_sim_time_sec"] = st.number_input("Total sim time (sec)", value=float(case["analysis"]["total_sim_time_sec"]), step=10.0)
            case["analysis"]["thermal_coupling_enabled"] = st.checkbox("Thermal coupling", value=bool(case["analysis"]["thermal_coupling_enabled"]))
            case["analysis"]["diffusion_enabled"] = st.checkbox("Diffusion enabled", value=bool(case["analysis"]["diffusion_enabled"]))
            case["analysis"]["imc_growth_enabled"] = st.checkbox("IMC growth enabled", value=bool(case["analysis"]["imc_growth_enabled"]))
            case["analysis"]["void_risk_enabled"] = st.checkbox("Void risk enabled", value=bool(case["analysis"]["void_risk_enabled"]))
            case["analysis"]["adhesion_risk_enabled"] = st.checkbox("Adhesion risk enabled", value=bool(case["analysis"]["adhesion_risk_enabled"]))

        a1, a2, a3 = st.columns([1, 1, 2])
        with a1:
            if st.button("Save case", use_container_width=True):
                case["project"]["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                save_plating_case(case, results, st.session_state.plating_images)
                st.success("Case saved.")
        with a2:
            if st.button("Run analysis", use_container_width=True, type="primary"):
                case["project"]["status"] = "running"
                case["project"]["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state.plating_results = run_plating_analysis(case)
                case["project"]["status"] = "done"
                save_plating_case(case, st.session_state.plating_results, st.session_state.plating_images)
                st.success("Analysis completed.")
                st.rerun()
        with a3:
            st.caption("Thermal FEM is solved explicitly. Diffusion, IMC growth, liquid fraction, and crystal order are currently reduced-order proxies.")

    with tab_images:
        st.subheader("Observation Assets")
        upload_col, meta_col = st.columns([1, 1])
        with upload_col:
            uploaded_images = st.file_uploader("Upload SEM / FIB / EDX / XRF / CSV", type=["png", "jpg", "jpeg", "tif", "tiff", "csv"], accept_multiple_files=True, key="plating_image_upload")
        with meta_col:
            location_tag = st.text_input("location_tag", "front-center")
            magnification = st.text_input("magnification", "500x")
            pre_or_post = st.selectbox("pre_or_post_reflow", ["pre", "post"])
            sample_id = st.text_input("sample_id", case["project"]["part_number"])
            image_note = st.text_area("note", "", height=80)

        if uploaded_images and st.button("Save uploaded assets", type="primary"):
            saved = 0
            for item in uploaded_images:
                saved_path = save_plating_uploaded_image(case["project"]["case_id"], item)
                st.session_state.plating_images.append({
                    "file_name": item.name,
                    "saved_path": saved_path,
                    "location_tag": location_tag,
                    "magnification": magnification,
                    "pre_or_post_reflow": pre_or_post,
                    "sample_id": sample_id,
                    "note": image_note,
                })
                saved += 1
            save_plating_case(case, results, st.session_state.plating_images)
            st.success(f"Saved {saved} assets.")

        if st.session_state.plating_images:
            st.dataframe(pd.DataFrame(st.session_state.plating_images), use_container_width=True, hide_index=True)

    with tab_result:
        st.subheader("Results")
        if not results:
            st.info("Run analysis to generate outputs.")
        else:
            fidelity = results.get("model_fidelity", {})
            if fidelity:
                st.info("Thermal field uses FEM. Other fields remain reduced-order for now.")
                st.json(fidelity, expanded=False)

            preds = results["predictions"]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Sn remaining (um)", preds["predicted_sn_remaining_um"])
            m2.metric("Ni remaining (um)", preds["predicted_ni_remaining_um"])
            m3.metric("IMC thickness (um)", preds["predicted_imc_thickness_um"])
            m4.metric("Peak stress (MPa)", preds["predicted_peak_stress_mpa"])

            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Void risk", preds["predicted_void_risk_score"], preds["predicted_void_risk_class"])
            r2.metric("Adhesion risk", preds["predicted_adhesion_risk_score"], preds["predicted_adhesion_risk_class"])
            r3.metric("Surface melt risk", preds["predicted_surface_melt_score"], preds["predicted_surface_melt_warning_badge"])
            r4.metric("Wetting score", preds["predicted_wetting_score"])

            derived = results["derived"]
            st.write(f"TAL: **{derived['tal_recomputed_sec']} sec** / Melt score: **{derived['melt_score']}** / Peak: **{derived['peak_temp_c']} C**")

            curve_df = pd.DataFrame(results["profile_curve"])
            st.line_chart(curve_df.rename(columns={"time_sec": "index"}).set_index("index")[["temp_c"]], use_container_width=True)
            st.dataframe(pd.DataFrame([preds]), use_container_width=True, hide_index=True)

            artifacts = results.get("artifacts", {})
            if artifacts:
                st.markdown("---")
                st.subheader("ParaView / VTK Output")
                b1, b2, b3 = st.columns(3)
                with b1:
                    st.caption(f"Output dir: `{artifacts.get('output_dir', '')}`")
                    if artifacts.get("field_vtu") and os.path.exists(artifacts["field_vtu"]):
                        with open(artifacts["field_vtu"], "rb") as handle:
                            st.download_button("Download VTU", handle.read(), file_name=os.path.basename(artifacts["field_vtu"]), use_container_width=True)
                with b2:
                    if artifacts.get("profile_csv") and os.path.exists(artifacts["profile_csv"]):
                        with open(artifacts["profile_csv"], "rb") as handle:
                            st.download_button("Download profile CSV", handle.read(), file_name=os.path.basename(artifacts["profile_csv"]), use_container_width=True)
                with b3:
                    if artifacts.get("summary_json") and os.path.exists(artifacts["summary_json"]):
                        with open(artifacts["summary_json"], "rb") as handle:
                            st.download_button("Download summary JSON", handle.read(), file_name=os.path.basename(artifacts["summary_json"]), use_container_width=True)

                c1, c2 = st.columns(2)
                with c1:
                    if artifacts.get("timeline_pvd") and os.path.exists(artifacts["timeline_pvd"]):
                        with open(artifacts["timeline_pvd"], "rb") as handle:
                            st.download_button("Download PVD timeline", handle.read(), file_name=os.path.basename(artifacts["timeline_pvd"]), use_container_width=True)
                with c2:
                    if artifacts.get("timeline_summary_json") and os.path.exists(artifacts["timeline_summary_json"]):
                        with open(artifacts["timeline_summary_json"], "rb") as handle:
                            st.download_button("Download timeline JSON", handle.read(), file_name=os.path.basename(artifacts["timeline_summary_json"]), use_container_width=True)

                if artifacts.get("snapshot_count"):
                    st.caption(f"Transient VTU snapshots: {artifacts['snapshot_count']}")
                if artifacts.get("paraview_preview_png") and os.path.exists(artifacts["paraview_preview_png"]):
                    st.image(artifacts["paraview_preview_png"], caption="ParaView-compatible preview", use_container_width=True)
                else:
                    st.warning("Preview PNG was not generated, but VTU/PVD output is available.")

    with tab_history:
        st.subheader("Recent cases")
        recent = load_recent_cases(limit=10)
        if not recent:
            st.info("No saved cases found.")
        else:
            history_rows = []
            for item in recent:
                payload = item.get("case", {})
                history_rows.append({
                    "case_id": payload.get("project", {}).get("case_id", ""),
                    "project_name": payload.get("project", {}).get("project_name", ""),
                    "status": payload.get("project", {}).get("status", ""),
                    "updated_at": payload.get("project", {}).get("updated_at", ""),
                    "solver": payload.get("analysis", {}).get("solver_backend", ""),
                })
            st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)



# --- SIDEBAR ---
st.sidebar.title("QA Toolkit")

# File Upload Section in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Upload Knowledge")
uploaded_file = st.sidebar.file_uploader("Add to Knowledge Base", type=["pdf", "xlsx", "docx", "pptx", "dxf", "txt"])
if uploaded_file is not None:
    if st.sidebar.button("Upload & Ingest"):
        with st.sidebar.status("Uploading..."):
            success, path, status = save_uploaded_file(uploaded_file, INGEST_DIR)
            if success:
                st.write(f"笨・{status}: {INGEST_DIR}")
                if status == "Saved": st.write("竢ｳ Ingestion started")
            else:
                st.error(f"Failed: {path}")

st.sidebar.markdown("---")

page = st.sidebar.radio("Select Tool", [
    "Home", 
    *([] if not PLATING_FLAG else ["Plating Quality Analysis"]),
    "Work Instruction Generator",
    "FMEA Editor", 
    "FTA (Fault Tree)", 
    "Why-Why Analysis",
    "Work Study",
    "3D Converter",
    "Tolerance Analysis",
    "Kindle Manuscript",
    "Email Daily Report (P016)"
])

# --- PAGES ---

if page == "Home":
    st.title("Clawstack QA Portal")
    st.markdown(f"""
    **New Feature:**
    *   **統 Work Instruction Generator:** Upload Documents/Video/Audio to `/consume/WIP`. AI generates standard work steps.
    
    **Knowledge Base:**
    *   **Ingest:** Upload to `/consume/PFMEA_5WHY_FTA_etc`.
    *   **RAG:** Documents are indexed for FMEA/FTA analysis.
    """)
    if PLATING_FLAG:
        st.markdown("---")
        st.subheader("Plating Quality Analysis")
        card_col1, card_col2 = st.columns([3, 2])
        with card_col1:
            st.markdown(
                """
                **Plating / Reflow Analysis**

                Enter plating line conditions, reflow conditions, thermal profile, and inspection assets.
                The Portal stores case inputs, runs analysis, and keeps generated artifacts together.
                """
            )
        with card_col2:
            st.info("Use the left sidebar to open `Plating Quality Analysis` and run the analysis.")

elif page == "Plating Quality Analysis":
    render_plating_quality_page()

elif page == "Work Instruction Generator":
    st.header("統 Work Instruction Generator")
    st.info("Upload raw materials (PDF, Excel, Video, Audio). AI will draft a Standard Operating Procedure (SOP).")
    
    uploaded_wip = st.file_uploader("Upload Raw Material", accept_multiple_files=True)
    
    if uploaded_wip:
        if st.button("噫 Generate Instruction"):
            combined_text = ""
            media_files = []
            
            progress = st.progress(0)
            status = st.empty()
            
            for i, uf in enumerate(uploaded_wip):
                status.write(f"Processing {uf.name}...")
                success, path, stat = save_uploaded_file(uf, WIP_DIR)
                
                if success:
                    ext = os.path.splitext(path)[1].lower()
                    if ext in [".pdf", ".docx", ".xlsx", ".txt"]:
                        txt = extract_text_immediate(path)
                        combined_text += f"\n\n--- Source: {uf.name} ---\n{txt}"
                    elif ext in [".mp4", ".avi", ".mov", ".mp3", ".wav"]:
                        media_files.append(uf.name)
                        combined_text += f"\n\n--- Source: {uf.name} ---\n[Media File Present: Analysis requires Vision/Audio Module update. Using context from documents if available.]"
                
                progress.progress((i + 1) / len(uploaded_wip))
            
            status.write("ｧ AI Generating SOP...")
            
            prompt = f"""
            Create a detailed 'Work Instruction' (Standard Operating Procedure) based on the following raw materials.
            Structure it with:
            1. Title
            2. Safety Warnings (Important!)
            3. Tools Required
            4. Step-by-Step Instructions (Concrete, Action-Oriented)
            
            RAW MATERIAL CONTENT:
            {combined_text[:6000]} 
            """
            # Truncate to avoid context limit overflow if huge
            
            sop = ask_ai(prompt)
            
            col1, col2 = st.columns([2,1])
            with col1:
                st.subheader("Draft Instruction")
                st.markdown(sop)
            with col2:
                if media_files:
                    st.warning(f"Media files referenced ({len(media_files)}). AI relied on text documents for detail.")
                
                fn = f"SOP_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.md"
                if st.button("沈 Save SOP"):
                    with open(os.path.join(WORK_DIR, fn), "w", encoding="utf-8") as f:
                        f.write(sop)
                    st.success(f"Saved to {WORK_DIR}/{fn}")

elif page == "FMEA Editor":
    st.header("投 FMEA (Knowledge Aware)")
    process_step = st.text_input("Process Step", "Battery Weld")
    
    if st.button("笨ｨ Ask AI"):
        with st.spinner("Searching..."):
            vec = get_embedding(process_step)
            context = search_qdrant(vec)
            res = ask_ai(f"Suggest 3 Failure Modes for '{process_step}'. Format: Mode, Effect, Severity.", context)
            if context:
                with st.expander("References"):
                    st.markdown(context[:1000])
            st.info(res)
            
    # Use existing dataframe logic...
    if 'fmea_data' not in st.session_state:
        st.session_state.fmea_data = pd.DataFrame([{"Process Step": process_step, "Mode": "", "Effect": "", "S": 0, "O": 0, "D": 0, "RPN": 0}])
    edited_df = st.data_editor(st.session_state.fmea_data, num_rows="dynamic", use_container_width=True)

elif page == "FTA (Fault Tree)":
    st.header("元 Fault Tree")
    top_event = st.text_input("Top Event", "Motor Stall")
    if st.button("笨ｨ Suggest Causes"):
        with st.spinner("Analyzing..."):
            vec = get_embedding(top_event)
            context = search_qdrant(vec)
            res = ask_ai(f"List 5 root causes for '{top_event}'.", context)
            st.text_area("AI Suggestions", res)
            
    nodes = st.text_area("Define Causes (Lines)", "Overload\nShort Circuit").split('\n')
    mermaid = f"graph TD\nTOP[\"{top_event}\"] --> OR((OR))"
    for i, n in enumerate(nodes):
        if n.strip(): mermaid += f"\nOR --> C{i}[\"{n.strip()}\"]"
    st.mermaid(mermaid)

elif page == "Why-Why Analysis":
    st.header("笶・5-Whys (Logic Check)")
    problem = st.text_input("Problem", "Leakage")
    whys = [st.text_input(f"{i}. Why?", key=f"w{i}") for i in range(1, 6)]
    if st.button("売 Verify Logic"):
        chain = " -> Therefore -> ".join([w for w in whys if w][::-1] + [problem])
        res = ask_ai(f"Verify this logic chain: {chain}")
        st.markdown(res)

elif page == "Work Study":
    st.header("竢ｱ・・Work Study")
    uploaded_vid = st.file_uploader("Upload Video", type=["mp4", "avi"])
    if uploaded_vid:
        success, path, _ = save_uploaded_file(uploaded_vid, WORK_DIR)
        if success: st.success(f"Video ready at {path}")

elif page == "3D Converter":
    st.header("3D Converter")
    st.markdown("""
    **2D / 3D conversion tools**
    
    | Conversion | Input | Output | Usage |
    |------|------|------|------|
    | **DXF -> STEP/STL** | DXF | STEP or STL | Simple extrusion-based 3D generation |
    | **Model -> 3D HTML** | STEP/STL/OBJ | Interactive HTML | Browser preview and sharing |
    | **Model -> 3D PDF** | STEP/STL/OBJ | 3D PDF | Adobe Acrobat Reader compatible |
    
    ---
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Upload File")
        conv_type = st.radio("Conversion Type", ["DXF -> STEP/STL", "Model -> 3D HTML", "Model -> 3D PDF"])
        
        if conv_type == "DXF -> STEP/STL":
            uploaded_3d = st.file_uploader("DXF file", type=["dxf"], key="dxf_upload")
            height = st.number_input("Extrusion height (mm)", min_value=0.1, value=10.0, step=0.5)
            output_format = st.selectbox("Output format", ["STEP", "STL"])
        else:
            uploaded_3d = st.file_uploader("3D model", type=["step", "stp", "stl", "obj"], key="model_upload")
    
    with col2:
        st.subheader("Run Conversion")
        if st.button("Start Conversion", use_container_width=True):
            if uploaded_3d is None:
                st.error("Please upload a file first.")
            else:
                import subprocess
                import tempfile
                
                with tempfile.TemporaryDirectory() as td:
                    # Save uploaded file
                    input_path = os.path.join(td, uploaded_3d.name)
                    with open(input_path, "wb") as f:
                        f.write(uploaded_3d.getbuffer())
                    
                    try:
                        if conv_type == "DXF -> STEP/STL":
                            ext = "step" if output_format == "STEP" else "stl"
                            output_path = os.path.join(td, f"output.{ext}")
                            cmd = ["python3", "/work/scripts/dxf23d.py", input_path, output_path, "--height", str(height)]
                        elif conv_type == "Model -> 3D HTML":
                            output_path = os.path.join(td, "output.html")
                            cmd = ["python3", "/work/scripts/model2html.py", input_path, output_path]
                        else:  # 3D PDF
                            output_path = os.path.join(td, "output.pdf")
                            cmd = ["python3", "/work/scripts/model2pdf.py", input_path, output_path]
                        
                        with st.spinner("Converting..."):
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                        
                        if result.returncode != 0:
                            st.error(f"Conversion failed: {result.stderr or result.stdout}")
                        elif os.path.exists(output_path):
                            st.success("Conversion completed.")
                            if conv_type == "Model -> 3D HTML":
                                with open(output_path, "rb") as f:
                                    st.download_button(
                                        "Download 3D HTML",
                                        f.read(),
                                        file_name=os.path.basename(output_path),
                                        mime="text/html",
                                        use_container_width=True,
                                    )
                                st.caption("The downloaded HTML can be opened locally by double-clicking it in a browser.")
                            else:
                                preview_path = os.path.join(
                                    td,
                                    os.path.splitext(os.path.basename(output_path))[0] + "_outline_preview.pdf",
                                )
                                dl1, dl2 = st.columns(2)
                                with dl1:
                                    with open(output_path, "rb") as f:
                                        st.download_button(
                                            "Download 3D PDF",
                                            f.read(),
                                            file_name=os.path.basename(output_path),
                                            use_container_width=True
                                        )
                                with dl2:
                                    if os.path.exists(preview_path):
                                        with open(preview_path, "rb") as f:
                                            st.download_button(
                                                "Download Outline Preview",
                                                f.read(),
                                                file_name=os.path.basename(preview_path),
                                                use_container_width=True
                                            )
                        else:
                            st.error("Output file was not generated.")
                    except subprocess.TimeoutExpired:
                        st.error("Conversion timed out after 5 minutes.")
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    st.markdown("---")
    st.info("""
    **Notes**
    - **DXF -> STEP/STL:** best for simple contour-based extrusion workflows.
    - **3D HTML:** uses browser-friendly interactive preview output.
    - **3D PDF:** creates Acrobat-compatible 3D PDF from STEP/STL/OBJ.
    """)

# -------------------------
# 蜈ｬ蟾ｮ隗｣譫舌・繝ｼ繧ｸ (Cetol6Sigma Style with 3D Viewer)
# -------------------------
elif page == "Tolerance Analysis":
    st.header("Tolerance Analysis Tool (Cetol6Sigma Style)")
    
    # Initialize session state
    if 'tol_dimensions' not in st.session_state:
        st.session_state.tol_dimensions = []
    if 'tol_result' not in st.session_state:
        st.session_state.tol_result = None
    if 'mesh_data' not in st.session_state:
        st.session_state.mesh_data = None
    if 'extracted_dims' not in st.session_state:
        st.session_state.extracted_dims = []
    
    # Tab layout
    tab_model, tab_dims, tab_result = st.tabs(["塙 3D繝｢繝・Ν & 謚ｽ蜃ｺ", "笵難ｸ・蜈ｬ蟾ｮ繝√ぉ繝ｼ繝ｳ", "投 隗｣譫千ｵ先棡"])
    
    # === Tab 1: 3D Model & Extraction ===
    with tab_model:
        col_upload, col_3d = st.columns([1, 2])
        
        with col_upload:
            st.subheader("Upload CAD File")
            uploaded_cad = st.file_uploader("STEP/STL 繝輔ぃ繧､繝ｫ", type=["step", "stp", "stl"], key="tol_upload")
            
            if uploaded_cad:
                st.success(f"笨・{uploaded_cad.name} ({len(uploaded_cad.getvalue())/1024:.1f} KB)")
                default_tolerance = st.number_input("繝・ヵ繧ｩ繝ｫ繝亥・蟾ｮ (ﾂｱmm)", min_value=0.001, value=0.1, step=0.01)
                
                if st.button("剥 3D繝｢繝・Ν隱ｭ縺ｿ霎ｼ縺ｿ & 蟇ｸ豕墓歓蜃ｺ", use_container_width=True, type="primary"):
                    import tempfile
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_cad.name)[1]) as tf:
                        tf.write(uploaded_cad.getbuffer())
                        temp_path = tf.name
                    
                    with st.spinner("繝｡繝・す繝･謚ｽ蜃ｺ荳ｭ..."):
                        try:
                            ext = os.path.splitext(uploaded_cad.name)[1].lower()
                            
                            if ext == ".stl":
                                # Use trimesh for STL (available in quality_dashboard)
                                import trimesh
                                mesh = trimesh.load(temp_path)
                                
                                st.session_state.mesh_data = {
                                    "vertices": mesh.vertices.tolist(),
                                    "faces": mesh.faces.tolist(),
                                    "face_colors": ["#667eea"] * len(mesh.faces)
                                }
                                
                                # Extract bounding box dimensions
                                size = mesh.bounds[1] - mesh.bounds[0]
                                st.session_state.extracted_dims = [
                                    {"id": "X", "name": f"BBox X", "nominal": round(float(size[0]), 4), "tolerance": default_tolerance, "label": "X"},
                                    {"id": "Y", "name": f"BBox Y", "nominal": round(float(size[1]), 4), "tolerance": default_tolerance, "label": "Y"},
                                    {"id": "Z", "name": f"BBox Z", "nominal": round(float(size[2]), 4), "tolerance": default_tolerance, "label": "Z"},
                                ]
                                st.success("STL mesh extraction completed.")
                                
                            else:
                                # For STEP, use docker exec to antigravity with FreeCAD
                                docker_temp = f"/tmp/cad_input{ext}"
                                
                                # Copy file to container
                                copy_cmd = f'docker cp "{temp_path}" clawstack-antigravity-1:{docker_temp}'
                                result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)
                                
                                if result.returncode != 0:
                                    st.error(f"繝輔ぃ繧､繝ｫ繧ｳ繝斐・繧ｨ繝ｩ繝ｼ: {result.stderr}")
                                else:
                                    # Run extraction script
                                    extract_cmd = f'docker exec clawstack-antigravity-1 python3 /work/scripts/extract_mesh.py {docker_temp}'
                                    result = subprocess.run(extract_cmd, shell=True, capture_output=True, text=True, timeout=120)
                                    
                                    if result.returncode == 0 and result.stdout:
                                        mesh_result = json.loads(result.stdout)
                                        if "error" in mesh_result:
                                            st.error(f"謚ｽ蜃ｺ繧ｨ繝ｩ繝ｼ: {mesh_result['error']}")
                                        else:
                                            st.session_state.mesh_data = mesh_result
                                            st.session_state.extracted_dims = mesh_result.get("dimensions", [])
                                            for d in st.session_state.extracted_dims:
                                                d["tolerance"] = default_tolerance
                                            st.success(f"笨・{len(st.session_state.extracted_dims)} 蟇ｸ豕輔ｒ謚ｽ蜃ｺ")
                                    else:
                                        st.warning("STEP extraction failed. Falling back to external mesh mode.")
                                        st.session_state.mesh_data = None
                            
                        except Exception as e:
                            st.error(f"蜃ｦ逅・お繝ｩ繝ｼ: {e}")
                        finally:
                            os.unlink(temp_path)
                    
                    st.rerun()
            
            # Extracted dimensions list
            if st.session_state.extracted_dims:
                st.markdown("---")
                st.subheader("Extracted Dimensions")
                for i, dim in enumerate(st.session_state.extracted_dims[:10]):  # Show first 10
                    col_d1, col_d2 = st.columns([3, 1])
                    with col_d1:
                        label = dim.get("label", chr(65 + i))
                        st.write(f"**{label}**: {dim['name']} = {dim['nominal']:.3f} mm")
                    with col_d2:
                        if st.button("Add", key=f"add_dim_{i}", help="Add this dimension to the chain"):
                            st.session_state.tol_dimensions.append({
                                "name": dim['name'],
                                "nominal": dim['nominal'],
                                "tolerance": dim.get('tolerance', 0.1),
                                "direction": "+"
                            })
                            st.rerun()
        
        with col_3d:
            st.subheader("塙 3D繝薙Η繝ｼ")
            
            if st.session_state.mesh_data and "vertices" in st.session_state.mesh_data:
                import plotly.graph_objects as go
                import numpy as np
                
                mesh = st.session_state.mesh_data
                verts = np.array(mesh["vertices"])
                faces = np.array(mesh["faces"])
                
                # Create mesh3d trace
                fig = go.Figure(data=[
                    go.Mesh3d(
                        x=verts[:, 0],
                        y=verts[:, 1],
                        z=verts[:, 2],
                        i=faces[:, 0],
                        j=faces[:, 1],
                        k=faces[:, 2],
                        color='#667eea',
                        opacity=0.8,
                        flatshading=True,
                        lighting=dict(ambient=0.5, diffuse=0.8, specular=0.3),
                        lightposition=dict(x=100, y=100, z=100),
                        hoverinfo='text',
                        hovertext='Click mesh faces to inspect dimensions'
                    )
                ])
                
                # Add face labels if available
                if "bounding_box" in mesh and mesh["bounding_box"]:
                    bbox = mesh["bounding_box"]
                    center = [(bbox["min"][i] + bbox["max"][i]) / 2 for i in range(3)]
                    
                    # Add dimension annotations
                    fig.add_trace(go.Scatter3d(
                        x=[bbox["min"][0], bbox["max"][0]],
                        y=[center[1], center[1]],
                        z=[bbox["min"][2], bbox["min"][2]],
                        mode='lines+text',
                        line=dict(color='red', width=3),
                        text=['', f'X: {bbox["size"][0]:.2f}'],
                        textposition='top center',
                        name='X dimension'
                    ))
                
                fig.update_layout(
                    scene=dict(
                        aspectmode='data',
                        camera=dict(eye=dict(x=1.5, y=1.5, z=1.0)),
                        bgcolor='#1a1a2e'
                    ),
                    paper_bgcolor='#1a1a2e',
                    margin=dict(l=0, r=0, t=0, b=0),
                    height=500,
                    clickmode='event+select'
                )
                
                # Use plotly_events for click detection
                from streamlit_plotly_events import plotly_events
                
                selected_points = plotly_events(
                    fig,
                    click_event=True,
                    hover_event=False,
                    select_event=False,
                    override_height=500,
                    key="mesh_click"
                )
                
                # Handle click events
                if selected_points:
                    st.success(f"識 繧ｯ繝ｪ繝・け讀懷・: {selected_points}")
                    # Get clicked point info
                    for pt in selected_points:
                        if 'pointNumber' in pt:
                            face_idx = pt['pointNumber'] // 3  # Approximate face index
                            st.write(f"驕ｸ謚槭＆繧後◆髱｢: 邏・{face_idx}")
                            
                            # Add dimension from clicked face
                            if st.session_state.extracted_dims and face_idx < len(st.session_state.extracted_dims):
                                dim = st.session_state.extracted_dims[face_idx]
                                if st.button(f"筐・{dim['name']} 繧偵メ繧ｧ繝ｼ繝ｳ縺ｫ霑ｽ蜉", key=f"add_click_{face_idx}"):
                                    st.session_state.tol_dimensions.append({
                                        "name": dim['name'],
                                        "nominal": dim['nominal'],
                                        "tolerance": dim.get('tolerance', 0.1),
                                        "direction": "+"
                                    })
                                    st.rerun()
                
                # Face selection UI
                st.markdown("---")
                st.subheader("Face Selection")
                if st.session_state.extracted_dims:
                    # Create face selector with colors
                    face_options = {f"{chr(65+i)}: {d['name']} ({d['nominal']:.2f}mm)": i 
                                   for i, d in enumerate(st.session_state.extracted_dims[:20])}
                    
                    selected_face = st.selectbox("Select dimension", list(face_options.keys()), key="face_select")
                    
                    col_sel1, col_sel2 = st.columns(2)
                    with col_sel1:
                        direction = st.radio("Direction", ["+", "-"], horizontal=True, key="dir_select")
                    with col_sel2:
                        if st.button("笵難ｸ・繝√ぉ繝ｼ繝ｳ縺ｫ霑ｽ蜉", type="primary", use_container_width=True):
                            idx = face_options[selected_face]
                            dim = st.session_state.extracted_dims[idx]
                            st.session_state.tol_dimensions.append({
                                "name": dim['name'],
                                "nominal": dim['nominal'],
                                "tolerance": dim.get('tolerance', 0.1),
                                "direction": direction
                            })
                            st.success(f"笨・{dim['name']} 繧定ｿｽ蜉縺励∪縺励◆")
                            st.rerun()
                else:
                    st.caption("棟 繝輔ぃ繧､繝ｫ繧偵い繝・・繝ｭ繝ｼ繝峨＠縺ｦ蟇ｸ豕輔ｒ謚ｽ蜃ｺ縺励※縺上□縺輔＞")
            else:
                st.info("刀 蟾ｦ蛛ｴ縺九ｉSTEP/STL繝輔ぃ繧､繝ｫ繧偵い繝・・繝ｭ繝ｼ繝峨＠縺ｦ3D繝｢繝・Ν繧定｡ｨ遉ｺ")
                
                # Show placeholder 3D
                import plotly.graph_objects as go
                import numpy as np
                
                # Demo box
                fig = go.Figure(data=[
                    go.Mesh3d(
                        x=[0, 0, 1, 1, 0, 0, 1, 1],
                        y=[0, 1, 1, 0, 0, 1, 1, 0],
                        z=[0, 0, 0, 0, 1, 1, 1, 1],
                        i=[0, 0, 1, 1, 4, 4, 0, 2, 1, 5, 0, 4],
                        j=[1, 2, 2, 3, 5, 6, 4, 3, 5, 6, 1, 5],
                        k=[2, 3, 6, 7, 6, 7, 1, 7, 6, 2, 4, 1],
                        color='#667eea',
                        opacity=0.5,
                        flatshading=True
                    )
                ])
                fig.update_layout(
                    scene=dict(aspectmode='cube', bgcolor='#1a1a2e'),
                    paper_bgcolor='#1a1a2e',
                    margin=dict(l=0, r=0, t=30, b=0),
                    height=400,
                    title="Demo: placeholder model"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # === Tab 2: Tolerance Chain ===
    with tab_dims:
        col_add, col_chain = st.columns([1, 2])
        
        with col_add:
            st.subheader("筐・蟇ｸ豕輔ｒ霑ｽ蜉")
            
            with st.form("add_dim_form"):
                dim_name = st.text_input("蟇ｸ豕募錐", f"DIM_{len(st.session_state.tol_dimensions)+1}")
                dim_nominal = st.number_input("蜈ｬ遘ｰ蛟､ (mm)", value=10.0, step=0.1)
                dim_tol = st.number_input("蜈ｬ蟾ｮ (ﾂｱmm)", value=0.1, step=0.01, min_value=0.001)
                dim_direction = st.radio("Direction", ["+", "-"], horizontal=True,
                                        help="+ = positive chain direction, - = negative chain direction")
                
                if st.form_submit_button("筐・繝√ぉ繝ｼ繝ｳ縺ｫ霑ｽ蜉", use_container_width=True):
                    st.session_state.tol_dimensions.append({
                        "name": dim_name,
                        "nominal": dim_nominal,
                        "tolerance": dim_tol,
                        "direction": dim_direction
                    })
                    st.rerun()
            
            if st.button("卵・・繝√ぉ繝ｼ繝ｳ繧偵け繝ｪ繧｢", use_container_width=True):
                st.session_state.tol_dimensions = []
                st.session_state.tol_result = None
                st.rerun()
        
        with col_chain:
            st.subheader("笵難ｸ・蜈ｬ蟾ｮ繝√ぉ繝ｼ繝ｳ")
            
            if st.session_state.tol_dimensions:
                dims_df = pd.DataFrame(st.session_state.tol_dimensions)
                edited_dims = st.data_editor(
                    dims_df,
                    use_container_width=True,
                    num_rows="dynamic",
                    column_config={
                        "name": st.column_config.TextColumn("蟇ｸ豕募錐"),
                        "nominal": st.column_config.NumberColumn("蜈ｬ遘ｰ蛟､ (mm)", format="%.4f"),
                        "tolerance": st.column_config.NumberColumn("蜈ｬ蟾ｮ (ﾂｱmm)", format="%.4f"),
                        "direction": st.column_config.SelectboxColumn("Direction", options=["+", "-"])
                    }
                )
                st.session_state.tol_dimensions = edited_dims.to_dict('records')
                
                # Chain summary
                chain_nominal = sum(
                    d["nominal"] * (1 if d["direction"] == "+" else -1)
                    for d in st.session_state.tol_dimensions
                )
                
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric("繝√ぉ繝ｼ繝ｳ蜈ｬ遘ｰ蛟､", f"{chain_nominal:.4f} mm")
                with col_m2:
                    st.metric("蟇ｸ豕墓焚", len(st.session_state.tol_dimensions))
                
                if st.button("Run Analysis", use_container_width=True, type="primary"):
                    import math
                    import random
                    
                    dims = st.session_state.tol_dimensions
                    
                    # Worst Case
                    wc_upper = sum(d["tolerance"] for d in dims)
                    
                    # RSS (3ﾏ・
                    rss = math.sqrt(sum(d["tolerance"]**2 for d in dims))
                    
                    # Monte Carlo
                    mc_samples = 10000
                    mc_results = []
                    for _ in range(mc_samples):
                        sample = sum(
                            (d["nominal"] + random.gauss(0, d["tolerance"]/3)) * (1 if d["direction"] == "+" else -1)
                            for d in dims
                        )
                        mc_results.append(sample)
                    
                    mc_mean = sum(mc_results) / len(mc_results)
                    mc_std = math.sqrt(sum((x - mc_mean)**2 for x in mc_results) / len(mc_results))
                    
                    # Sensitivity
                    total_var = sum(d["tolerance"]**2 for d in dims)
                    sensitivities = {d["name"]: (d["tolerance"]**2 / total_var * 100) if total_var > 0 else 0 for d in dims}
                    
                    st.session_state.tol_result = {
                        "nominal": chain_nominal,
                        "wc_upper": wc_upper,
                        "rss": rss,
                        "mc_mean": mc_mean,
                        "mc_std": mc_std,
                        "sensitivities": sensitivities,
                        "mc_histogram": mc_results
                    }
                    st.rerun()
            else:
                st.info("盗 蟾ｦ蛛ｴ縺九ｉ蟇ｸ豕輔ｒ霑ｽ蜉縺吶ｋ縺九・D繝｢繝・Ν繧ｿ繝悶〒蟇ｸ豕輔ｒ驕ｸ謚槭＠縺ｦ縺上□縺輔＞")
    
    # === Tab 3: Results ===
    with tab_result:
        if st.session_state.tol_result:
            r = st.session_state.tol_result
            
            # Summary cards
            st.subheader("投 隗｣譫舌し繝槭Μ")
            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                st.metric("蜈ｬ遘ｰ蛟､", f"{r['nominal']:.4f} mm")
            with col_r2:
                st.metric("Worst Case", f"ﾂｱ{r['wc_upper']:.4f} mm", delta_color="off")
            with col_r3:
                st.metric("RSS (3ﾏ・", f"ﾂｱ{r['rss']:.4f} mm", delta_color="off")
            with col_r4:
                st.metric("Monte Carlo σ", f"{r['mc_std']:.4f} mm", delta_color="off")
            
            # Results comparison table
            st.markdown("---")
            results_df = pd.DataFrame([
                {"Method": "Worst Case", "Upper": r['nominal'] + r['wc_upper'], "Lower": r['nominal'] - r['wc_upper'], "Span": r['wc_upper'] * 2},
                {"Method": "RSS (3σ)", "Upper": r['nominal'] + r['rss'], "Lower": r['nominal'] - r['rss'], "Span": r['rss'] * 2},
                {"Method": "Monte Carlo (3σ)", "Upper": r['mc_mean'] + 3*r['mc_std'], "Lower": r['mc_mean'] - 3*r['mc_std'], "Span": 6*r['mc_std']},
            ])
            st.dataframe(results_df, use_container_width=True, hide_index=True)
            
            # Sensitivity chart
            col_sens, col_hist = st.columns(2)
            
            with col_sens:
                st.subheader("識 諢溷ｺｦ蛻・梵")
                sens_df = pd.DataFrame([{"Dimension": k, "Sensitivity": v} for k, v in r['sensitivities'].items()])
                sens_df = sens_df.sort_values("Sensitivity", ascending=True)
                
                import plotly.express as px
                fig_sens = px.bar(sens_df, x="Sensitivity", y="Dimension", orientation='h',
                                 color="Sensitivity", color_continuous_scale="Blues")
                fig_sens.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig_sens, use_container_width=True)
            
            with col_hist:
                st.subheader("Monte Carlo Histogram")
                import plotly.express as px
                
                fig_hist = px.histogram(x=r['mc_histogram'], nbins=50)
                fig_hist.add_vline(x=r['mc_mean'], line_dash="dash", line_color="red", annotation_text="ﾎｼ")
                fig_hist.add_vline(x=r['mc_mean'] - 3*r['mc_std'], line_dash="dot", line_color="orange")
                fig_hist.add_vline(x=r['mc_mean'] + 3*r['mc_std'], line_dash="dot", line_color="orange")
                fig_hist.update_layout(height=300, xaxis_title="邏ｯ遨榊・蟾ｮ (mm)", yaxis_title="鬆ｻ蠎ｦ")
                st.plotly_chart(fig_hist, use_container_width=True)
            
            # Export buttons
            st.markdown("---")
            col_exp1, col_exp2 = st.columns(2)
            
            with col_exp1:
                report_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>蜈ｬ蟾ｮ隗｣譫舌Ξ繝昴・繝・/title>
<style>body{{font-family:sans-serif;padding:20px;background:#1a1a2e;color:#eee}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #444;padding:8px}}
th{{background:#667eea}}.metric{{background:#2d2d44;padding:15px;border-radius:8px;margin:5px}}</style></head>
<body><h1>投 蜈ｬ蟾ｮ隗｣譫舌Ξ繝昴・繝・/h1>
<p>逕滓・: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<div style="display:flex;gap:10px;">
<div class="metric"><h3>蜈ｬ遘ｰ蛟､</h3><p>{r['nominal']:.4f} mm</p></div>
<div class="metric"><h3>Worst Case</h3><p>ﾂｱ{r['wc_upper']:.4f} mm</p></div>
<div class="metric"><h3>RSS</h3><p>ﾂｱ{r['rss']:.4f} mm</p></div>
<div class="metric"><h3>MC ﾏ・/h3><p>{r['mc_std']:.4f} mm</p></div>
</div>
<h2>蟇ｸ豕穂ｸ隕ｧ</h2><table><tr><th>蜷咲ｧｰ</th><th>蜈ｬ遘ｰ蛟､</th><th>蜈ｬ蟾ｮ</th><th>譁ｹ蜷・/th><th>蟇・ｸ主ｺｦ</th></tr>
{"".join(f'<tr><td>{d["name"]}</td><td>{d["nominal"]:.4f}</td><td>ﾂｱ{d["tolerance"]:.4f}</td><td>{d["direction"]}</td><td>{r["sensitivities"].get(d["name"],0):.1f}%</td></tr>' for d in st.session_state.tol_dimensions)}
</table></body></html>"""
                st.download_button("Download HTML Report", report_html, "tolerance_report.html", "text/html", use_container_width=True)
            
            with col_exp2:
                csv_data = "蜷咲ｧｰ,蜈ｬ遘ｰ蛟､,蜈ｬ蟾ｮ,譁ｹ蜷・蟇・ｸ主ｺｦ\n" + "\n".join(
                    f'{d["name"]},{d["nominal"]},{d["tolerance"]},{d["direction"]},{r["sensitivities"].get(d["name"],0):.1f}'
                    for d in st.session_state.tol_dimensions
                )
                st.download_button("Download CSV", csv_data, "tolerance_data.csv", "text/csv", use_container_width=True)
        else:
            st.info("Add dimensions in the tolerance table to run the analysis.")

elif page == "Kindle Manuscript":
    st.header("答 譖ｸ邀榊次遞ｿ逕滓・ (Kindle Unlimited)")
    st.markdown("""
    **菴ｿ縺・婿:**
    1. `/consume/Kindle/` 縺ｫ繝励Ο繧ｸ繧ｧ繧ｯ繝医ヵ繧ｩ繝ｫ繝繧剃ｽ懈・・井ｾ・ `FEM_Impact`・・
    2. 雉・侭・・DF, PPTX, TXT, DOCX・峨ｒ繝輔か繝ｫ繝縺ｫ驟咲ｽｮ
    3. IMPACT FEM繧定ｵｷ蜍輔＠縺ｦ繧ｹ繧ｯ繝ｪ繝ｼ繝ｳ繧ｷ繝ｧ繝・ヨ繧貞叙蠕暦ｼ医が繝励す繝ｧ繝ｳ・・
    4. AI縺瑚ｳ・侭縺ｨ逕ｻ蜒上ｒ隱ｭ縺ｿ霎ｼ縺ｿ縲∝次遞ｿ繧堤函謌・
    
    ---
    """)
    
    # List available Kindle project folders
    kindle_projects = []
    if os.path.exists(KINDLE_DIR):
        kindle_projects = [d for d in os.listdir(KINDLE_DIR) if os.path.isdir(os.path.join(KINDLE_DIR, d))]
    
    if not kindle_projects:
        st.warning(f"No Kindle projects were found. Place project folders under `{KINDLE_DIR}/`.")
    else:
        selected_project = st.selectbox("Select project", kindle_projects)
        project_path = os.path.join(KINDLE_DIR, selected_project)
        images_dir = os.path.join(project_path, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        # List files in selected project (Recursively)
        project_files = []
        for root, dirs, files in os.walk(project_path):
            for f in files:
                # Exclude hidden files or system files if needed
                if not f.startswith('.'):
                    # Store relative path for cleaner display
                    rel_path = os.path.relpath(os.path.join(root, f), project_path)
                    project_files.append(rel_path)
        
        st.write(f"**雉・侭繝輔ぃ繧､繝ｫ ({len(project_files)}莉ｶ):**")
        for f in project_files[:10]:  # Show first 10
            fpath = os.path.join(project_path, f)
            size_kb = os.path.getsize(fpath) / 1024
            st.write(f"- {f} ({size_kb:.1f} KB)")
        if len(project_files) > 10:
            st.write(f"... 莉・{len(project_files) - 10} 莉ｶ")
        
        # IMPACT Control Section
        st.markdown("---")
        st.subheader("萄 IMPACT FEM 繧ｹ繧ｯ繝ｪ繝ｼ繝ｳ繧ｷ繝ｧ繝・ヨ")
        
        impact_col1, impact_col2, impact_col3 = st.columns(3)
        
        with impact_col1:
            if st.button("Start IMPACT", use_container_width=True):
                import subprocess
                try:
                    result = subprocess.run(
                        ["bash", "/work/scripts/impact_vnc.sh", "start"],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        st.success("笨・IMPACT襍ｷ蜍募ｮ御ｺ・")
                        st.info("倹 http://localhost:6080/vnc.html 縺ｧGUI謫堺ｽ懷庄閭ｽ")
                    else:
                        st.error(f"繧ｨ繝ｩ繝ｼ: {result.stderr or result.stdout}")
                except Exception as e:
                    st.error(f"襍ｷ蜍募､ｱ謨・ {e}")
        
        with impact_col2:
            screenshot_name = st.text_input("Screenshot name", f"screen_{datetime.datetime.now().strftime('%H%M%S')}")
            if st.button("Capture Screenshot", use_container_width=True):
                import subprocess
                screenshot_path = os.path.join(images_dir, f"{screenshot_name}.png")
                try:
                    result = subprocess.run(
                        ["bash", "/work/scripts/impact_vnc.sh", "screenshot", screenshot_path],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0 and os.path.exists(screenshot_path):
                        st.success(f"笨・菫晏ｭ・ {screenshot_path}")
                        st.image(screenshot_path, caption=screenshot_name, width=300)
                    else:
                        st.error(f"繧ｨ繝ｩ繝ｼ: {result.stderr or result.stdout}")
                except Exception as e:
                    st.error(f"蜿門ｾ怜､ｱ謨・ {e}")
        
        with impact_col3:
            if st.button("尅 IMPACT蛛懈ｭ｢", use_container_width=True):
                import subprocess
                try:
                    subprocess.run(["bash", "/work/scripts/impact_vnc.sh", "stop"], timeout=10)
                    st.success("IMPACT stopped.")
                except Exception as e:
                    st.warning(f"蛛懈ｭ｢荳ｭ縺ｫ繧ｨ繝ｩ繝ｼ: {e}")
        
        # Show existing images
        existing_images = [f for f in os.listdir(images_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))] if os.path.exists(images_dir) else []
        if existing_images:
            with st.expander(f"胴 菫晏ｭ俶ｸ医∩逕ｻ蜒・({len(existing_images)}譫・"):
                img_cols = st.columns(3)
                for i, img in enumerate(existing_images[:9]):
                    with img_cols[i % 3]:
                        st.image(os.path.join(images_dir, img), caption=img, width=150)
        
        # ---------------------------------------------------------
        # 竭｢ 繧ｷ繝溘Η繝ｬ繝ｼ繧ｷ繝ｧ繝ｳ螳溯｡・(P018)
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("竭｢ Impact FEM 繧ｷ繝溘Η繝ｬ繝ｼ繧ｷ繝ｧ繝ｳ螳溯｡・(P018)")
        
        # Filter .in files
        in_files = [f for f in project_files if f.lower().endswith(".in")]
        
        if not in_files:
            st.info("No `.in` input file was found.")
        else:
            selected_in_file = st.selectbox("蟇ｾ雎｡縺ｮ蜈･蜉帙ヵ繧｡繧､繝ｫ (.in)", in_files)
            target_in_path = os.path.join(project_path, selected_in_file)
            
            c1, c2 = st.columns(2)
            
            with c1:
                if st.button("噫 繧ｷ繝溘Η繝ｬ繝ｼ繧ｷ繝ｧ繝ｳ螳溯｡・(Background)", use_container_width=True):
                    # Command construction for Container Environment
                    # Classpath assumes /opt/impact structure
                    classpath = "/opt/impact/bin:/opt/impact/lib/*"
                    java_cmd = [
                        "java", 
                        "-Xmx2048m", 
                        "-cp", classpath,
                        "run.Impact", 
                        target_in_path
                    ]
                    
                    st.write(f"Executing: `{' '.join(java_cmd)}`")
                    
                    try:
                        # Run in background (nohup style) or blocking? 
                        # For simple UX, let's do blocking with a spinner for now, 
                        # or use subprocess.Popen for background if long running.
                        # Given Streamlit's nature, blocking is easier to show logs, 
                        # but for long sims, background is better.
                        # Let's try blocking for immediate feedback on simple models like Bullet_AKM.
                        
                        with st.spinner("繧ｷ繝溘Η繝ｬ繝ｼ繧ｷ繝ｧ繝ｳ螳溯｡御ｸｭ... (繝ｭ繧ｰ縺ｯ荳九↓陦ｨ遉ｺ縺輔ｌ縺ｾ縺・"):
                            process = subprocess.Popen(
                                java_cmd, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True, 
                                cwd=os.path.dirname(target_in_path) # Run in file's dir
                            )
                            stdout, stderr = process.communicate()
                            
                            if process.returncode == 0:
                                st.success("Simulation completed.")
                            else:
                                st.error(f"笶・繧ｨ繝ｩ繝ｼ逋ｺ逕・(Exit Code: {process.returncode})")
                            
                            with st.expander("螳溯｡後Ο繧ｰ (STDOUT)", expanded=True):
                                st.code(stdout)
                            if stderr:
                                with st.expander("繧ｨ繝ｩ繝ｼ繝ｭ繧ｰ (STDERR)", expanded=True):
                                    st.code(stderr)
                                    
                    except Exception as e:
                        st.error(f"Execution Error: {e}")

            with c2:
                if st.button("祷 縺薙・隗｣譫舌・隗｣隱ｬ逕滓・ (AI)", use_container_width=True):
                    with st.spinner("隗｣譫仙・螳ｹ繧貞・譫蝉ｸｭ..."):
                         # Read the .in file
                        try:
                            with open(target_in_path, "r", encoding="utf-8", errors="ignore") as f:
                                in_content = f.read()
                            
                            prompt = f"""
縺ゅ↑縺溘・CAE隗｣譫舌・蟆る摩螳ｶ縺ｧ縺吶ゆｻ･荳九・Impact FEM蜈･蜉帙ヵ繧｡繧､繝ｫ(`{selected_in_file}`)繧貞・譫舌＠縲・
縺薙・繧ｷ繝溘Η繝ｬ繝ｼ繧ｷ繝ｧ繝ｳ縺後御ｽ輔ｒ縲阪後←縺・＞縺・擅莉ｶ縺ｧ縲崎ｧ｣譫舌＠繧医≧縺ｨ縺励※縺・ｋ縺ｮ縺九・
荳闊ｬ縺ｮ繧ｨ繝ｳ繧ｸ繝九い縺ｫ繧ゅｏ縺九ｋ繧医≧縺ｫ隗｣隱ｬ繝ｬ繝昴・繝医ｒ菴懈・縺励※縺上□縺輔＞縲・

# 鬆・岼
1. **隗｣譫舌・逶ｮ逧・*: 菴輔′菴輔↓陦晉ｪ√☆繧九・縺九√↑縺ｩ
2. **繝｢繝・Ν讎りｦ・*: 繝弱・繝画焚縲∬ｦ∫ｴ繧ｿ繧､繝励∵攝譁呻ｼ・aterials・・
3. **蠅・阜譚｡莉ｶ (Constraints)**: 縺ｩ縺薙′蝗ｺ螳壹＆繧後※縺・ｋ縺九∝・騾溷ｺｦ縺ｯ縺・￥繧峨°
4. **譛溷ｾ・＆繧後ｋ邨先棡**: 縺ｩ縺ｮ繧医≧縺ｪ迚ｩ逅・樟雎｡・郁ｲｫ騾壹∬ｷｳ縺ｭ霑斐ｊ縲∝､牙ｽ｢・峨′隕九ｉ繧後ｋ縺ｯ縺壹°

# 蜈･蜉帙ヵ繧｡繧､繝ｫ蜀・ｮｹ
{in_content[:20000]}
"""
                            explanation = ask_ai(prompt)
                            st.markdown(explanation)
                        except Exception as e:
                            st.error(f"Analysis Error: {e}")

        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("竭 雉・侭隱ｭ縺ｿ霎ｼ縺ｿ")
            include_code = st.checkbox("繧ｽ繝ｼ繧ｹ繧ｳ繝ｼ繝・.py, .java, .md遲・繧ょ性繧√ｋ", value=True)
            if st.button("Analyze Materials", use_container_width=True):
                combined_text = ""
                for f in project_files:
                    fpath = os.path.join(project_path, f)
                    ext = f.lower().split('.')[-1]
                    try:
                        # Text / Code Files
                        if ext in ["txt", "sh", "py", "java", "c", "cpp", "h", "md", "json", "yml", "yaml", "bat", "ps1", "properties", "in"]:
                            if include_code or ext == "txt":
                                with open(fpath, "r", encoding="utf-8", errors="ignore") as tf:
                                    combined_text += f"\n\n=== FILE: {f} ===\n" + tf.read()
                        elif ext == "pdf":
                            reader = pypdf.PdfReader(fpath)
                            combined_text += f"\n\n=== {f} ===\n" + "\n".join([p.extract_text() or "" for p in reader.pages])
                        elif ext == "docx":
                            doc = docx.Document(fpath)
                            combined_text += f"\n\n=== {f} ===\n" + "\n".join([p.text for p in doc.paragraphs])
                        elif ext == "pptx":
                            from pptx import Presentation
                            prs = Presentation(fpath)
                            slides_text = []
                            for slide in prs.slides:
                                for shape in slide.shapes:
                                    if hasattr(shape, "text"):
                                        slides_text.append(shape.text)
                            combined_text += f"\n\n=== {f} ===\n" + "\n".join(slides_text)
                    except Exception as e:
                        st.warning(f"{f}: 隱ｭ縺ｿ霎ｼ縺ｿ繧ｨ繝ｩ繝ｼ ({e})")
                
                st.session_state.kindle_content = combined_text
                st.session_state.kindle_images = existing_images
                st.success(f"Loaded {len(combined_text)} characters and {len(existing_images)} images.")
                with st.expander("隱ｭ縺ｿ霎ｼ縺ｿ蜀・ｮｹ繝励Ξ繝薙Η繝ｼ"):
                    st.text(combined_text[:3000] + "..." if len(combined_text) > 3000 else combined_text)
        
        with col2:
            st.subheader("竭｡ 蜴溽ｨｿ逕滓・")
            book_title = st.text_input("譖ｸ邀阪ち繧､繝医Ν", f"{selected_project}蜈･髢")
            target_pages = st.number_input("逶ｮ讓吶・繝ｼ繧ｸ謨ｰ", min_value=10, max_value=200, value=50)
            
            if st.button("笨ｨ AI縺ｧ蜴溽ｨｿ逕滓・", use_container_width=True):
                if "kindle_content" not in st.session_state or not st.session_state.kindle_content:
                    st.error("蜈医↓縲瑚ｳ・侭繧定ｧ｣譫舌阪ｒ螳溯｡後＠縺ｦ縺上□縺輔＞")
                else:
                    # Build image references
                    image_refs = ""
                    if existing_images:
                        image_refs = "\n\n蛻ｩ逕ｨ蜿ｯ閭ｽ縺ｪ逕ｻ蜒・\n" + "\n".join([f"- {img}" for img in existing_images])
                    
                    prompt = f"""
Create a Kindle-ready Markdown manuscript.

Title: {book_title}
Target pages: {target_pages}
Target length guideline: about {target_pages * 400} Japanese characters.

Requirements:
- Organize the material into a practical, readable book structure.
- Use the supplied technical materials and screenshots as source material.
- Explain engineering concepts clearly for readers.
- Return Markdown only.

Available images:
{image_refs}

Source materials:
{st.session_state.kindle_content[:150000]}
"""
                    with st.spinner("蜴溽ｨｿ逕滓・荳ｭ... (謨ｰ蛻・°縺九ｋ蝣ｴ蜷医′縺ゅｊ縺ｾ縺・"):
                        result = ask_ai(prompt)
                    
                    st.session_state.kindle_manuscript = result
                    st.success("Manuscript generation completed.")
        
        # Display manuscript
        if "kindle_manuscript" in st.session_state and st.session_state.kindle_manuscript:
            st.markdown("---")
            st.subheader("当 逕滓・縺輔ｌ縺溷次遞ｿ")
            st.markdown(st.session_state.kindle_manuscript)
            
            # Save button
            fn = f"{selected_project}_蜴溽ｨｿ_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.md"
            if st.download_button("Download Markdown", st.session_state.kindle_manuscript, file_name=fn):
                st.success(f"菫晏ｭ伜ｮ御ｺ・ {fn}")

        # Check for existing reports
        st.markdown("---")
        st.subheader("唐 菫晏ｭ俶ｸ医∩蜴溽ｨｿ")
        report_files = [f for f in os.listdir(WORK_DIR) if f.startswith(selected_project) and f.endswith(".md")] if os.path.exists(WORK_DIR) else []
        
        if report_files:
            for rf in report_files:
                rf_path = os.path.join(WORK_DIR, rf)
                with open(rf_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                col_d1, col_d2 = st.columns([3, 1])
                with col_d1:
                    st.text(f"塘 {rf} ({os.path.getsize(rf_path)/1024:.1f} KB)")
                with col_d2:
                    st.download_button("Download", content, file_name=rf, key=f"dl_{rf}")
        else:
            st.info("No saved manuscript reports were found.")

# -------------------------
# P016: Email Reporting
# -------------------------
elif page == "Email Daily Report (P016)":
    st.header("透 Email Daily Report (P016)")
    st.info("P016 bundles requests, QIF items, and meeting notes into a daily report.")

    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Date Filter
        today = datetime.date.today()
        start_date = st.date_input("髢句ｧ区律", today)
        end_date = st.date_input("邨ゆｺ・律", today)
        
        if st.button("Generate Report", use_container_width=True):
            with st.spinner("繝｡繝ｼ繝ｫ隗｣譫蝉ｸｭ... (謨ｰ蛻・°縺九ｊ縺ｾ縺・"):
                # Copy script if not present (safety check)
                if not os.path.exists("/app/generate_email_report.py"):
                    try:
                        import shutil
                        shutil.copy("/work/scripts/generate_email_report.py", "/app/generate_email_report.py")
                    except:
                        pass
                
                # Execute with Date Arguments
                cmd = [
                    "python3", "/work/scripts/generate_email_report.py",
                    "--start", str(start_date),
                    "--end", str(end_date)
                ]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    st.success("笨・繝ｬ繝昴・繝育函謌仙ｮ御ｺ・")
                    st.text_area("Log Output", result.stdout, height=200)
                except subprocess.CalledProcessError as e:
                    st.error(f"Error: {e}")
                    st.text_area("Error Output", e.stderr, height=200)

    # List Reports
    st.markdown("---")
    st.subheader("Available Reports")
    
    if os.path.exists(WORK_DIR):
        reports = [f for f in os.listdir(WORK_DIR) if f.startswith("Email_Report_") and f.endswith(".md")]
        reports.sort(reverse=True)
        
        if reports:
            selected_report = st.selectbox("Select report", reports)
            
            if selected_report:
                rpath = os.path.join(WORK_DIR, selected_report)
                with open(rpath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                st.markdown(content)
                st.download_button("Download", content, file_name=selected_report)
        else:
            st.info("No reports are available yet.")

