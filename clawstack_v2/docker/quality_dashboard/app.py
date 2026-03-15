import streamlit as st
import pandas as pd
import subprocess
import json
import urllib.request
import os
import datetime
import shutil
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
        return f"⚠️ AI Offline: {e}"

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

# --- SIDEBAR ---
st.sidebar.title("QA Toolkit 💎")

# File Upload Section in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📄 Upload Knowledge")
uploaded_file = st.sidebar.file_uploader("Add to Knowledge Base", type=["pdf", "xlsx", "docx", "pptx", "dxf", "txt"])
if uploaded_file is not None:
    if st.sidebar.button("Upload & Ingest"):
        with st.sidebar.status("Uploading..."):
            success, path, status = save_uploaded_file(uploaded_file, INGEST_DIR)
            if success:
                st.write(f"✅ {status}: {INGEST_DIR}")
                if status == "Saved": st.write("⏳ Ingestion started")
            else:
                st.error(f"Failed: {path}")

st.sidebar.markdown("---")

page = st.sidebar.radio("Select Tool", [
    "Home", 
    "Work Instruction Generator",
    "FMEA Editor", 
    "FTA (Fault Tree)", 
    "Why-Why Analysis",
    "Work Study",
    "3D Converter",
    "📐 公差解析",
    "書籍原稿生成",
    "📧 Email報告 (P016)"
])

# --- PAGES ---

if page == "Home":
    st.title("🛡️ Clawstack QA Portal")
    st.markdown(f"""
    **New Feature:**
    *   **📝 Work Instruction Generator:** Upload Documents/Video/Audio to `/consume/WIP`. AI generates standard work steps.
    
    **Knowledge Base:**
    *   **Ingest:** Upload to `/consume/PFMEA_5WHY_FTA_etc`.
    *   **RAG:** Documents are indexed for FMEA/FTA analysis.
    """)

elif page == "Work Instruction Generator":
    st.header("📝 Work Instruction Generator")
    st.info("Upload raw materials (PDF, Excel, Video, Audio). AI will draft a Standard Operating Procedure (SOP).")
    
    uploaded_wip = st.file_uploader("Upload Raw Material", accept_multiple_files=True)
    
    if uploaded_wip:
        if st.button("🚀 Generate Instruction"):
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
            
            status.write("🧠 AI Generating SOP...")
            
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
                if st.button("💾 Save SOP"):
                    with open(os.path.join(WORK_DIR, fn), "w", encoding="utf-8") as f:
                        f.write(sop)
                    st.success(f"Saved to {WORK_DIR}/{fn}")

elif page == "FMEA Editor":
    st.header("📊 FMEA (Knowledge Aware)")
    process_step = st.text_input("Process Step", "Battery Weld")
    
    if st.button("✨ Ask AI"):
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
    st.header("🌳 Fault Tree")
    top_event = st.text_input("Top Event", "Motor Stall")
    if st.button("✨ Suggest Causes"):
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
    st.header("❓ 5-Whys (Logic Check)")
    problem = st.text_input("Problem", "Leakage")
    whys = [st.text_input(f"{i}. Why?", key=f"w{i}") for i in range(1, 6)]
    if st.button("🔄 Verify Logic"):
        chain = " -> Therefore -> ".join([w for w in whys if w][::-1] + [problem])
        res = ask_ai(f"Verify this logic chain: {chain}")
        st.markdown(res)

elif page == "Work Study":
    st.header("⏱️ Work Study")
    uploaded_vid = st.file_uploader("Upload Video", type=["mp4", "avi"])
    if uploaded_vid:
        success, path, _ = save_uploaded_file(uploaded_vid, WORK_DIR)
        if success: st.success(f"Video ready at {path}")

elif page == "3D Converter":
    st.header("🔧 3D Converter")
    st.markdown("""
    **2D/3D ファイル変換ツール**
    
    | 変換 | 入力 | 出力 | 用途 |
    |------|------|------|------|
    | **DXF → STEP/STL** | 2D図面(.dxf) | 3Dモデル | 押し出しで3D化 |
    | **Model → HTML** | STEP/STL/OBJ | インタラクティブHTML | ブラウザで回転・拡大 |
    | **Model → PDF** | STEP/STL/OBJ | 3D PDF | Acrobat Reader用 |
    
    ---
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("① ファイルをアップロード")
        conv_type = st.radio("変換タイプ", ["DXF → STEP/STL", "Model → 3D HTML", "Model → 3D PDF"])
        
        if conv_type == "DXF → STEP/STL":
            uploaded_3d = st.file_uploader("DXFファイル", type=["dxf"], key="dxf_upload")
            height = st.number_input("押し出し高さ (mm)", min_value=0.1, value=10.0, step=0.5)
            output_format = st.selectbox("出力形式", ["STEP", "STL"])
        else:
            uploaded_3d = st.file_uploader("3Dモデル", type=["step", "stp", "stl", "obj"], key="model_upload")
    
    with col2:
        st.subheader("② 変換実行")
        if st.button("🚀 変換開始", use_container_width=True):
            if uploaded_3d is None:
                st.error("ファイルをアップロードしてください")
            else:
                import subprocess
                import tempfile
                
                with tempfile.TemporaryDirectory() as td:
                    # Save uploaded file
                    input_path = os.path.join(td, uploaded_3d.name)
                    with open(input_path, "wb") as f:
                        f.write(uploaded_3d.getbuffer())
                    
                    try:
                        if conv_type == "DXF → STEP/STL":
                            ext = "step" if output_format == "STEP" else "stl"
                            output_path = os.path.join(td, f"output.{ext}")
                            cmd = ["python3", "/work/scripts/dxf23d.py", input_path, output_path, "--height", str(height)]
                        elif conv_type == "Model → 3D HTML":
                            output_path = os.path.join(td, "output.html")
                            cmd = ["python3", "/work/scripts/model2html.py", input_path, output_path]
                        else:  # 3D PDF
                            output_path = os.path.join(td, "output.pdf")
                            cmd = ["python3", "/work/scripts/model2pdf.py", input_path, output_path]
                        
                        with st.spinner("変換中..."):
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                        
                        if result.returncode != 0:
                            st.error(f"変換エラー: {result.stderr or result.stdout}")
                        elif os.path.exists(output_path):
                            st.success("✅ 変換完了!")
                            with open(output_path, "rb") as f:
                                st.download_button(
                                    "📥 ダウンロード",
                                    f.read(),
                                    file_name=os.path.basename(output_path),
                                    use_container_width=True
                                )
                        else:
                            st.error("出力ファイルが生成されませんでした")
                    except subprocess.TimeoutExpired:
                        st.error("変換がタイムアウトしました (5分超過)")
                    except Exception as e:
                        st.error(f"エラー: {e}")
    
    st.markdown("---")
    st.info("""
    **注意事項:**
    - **DXF → STEP/STL:** 閉じたポリラインのみ3D化されます。レイヤー "CONTOUR" がデフォルトです。
    - **3D HTML:** Google model-viewer を使用。すべてのブラウザで動作します。
    - **3D PDF:** Adobe Acrobat Reader でのみ3D操作可能です（ブラウザPDFビューアでは不可）。
    """)

# -------------------------
# 公差解析ページ (Cetol6Sigma Style with 3D Viewer)
# -------------------------
elif page == "📐 公差解析":
    st.header("📐 公差解析ツール (Cetol6Sigma Style)")
    
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
    tab_model, tab_dims, tab_result = st.tabs(["🔷 3Dモデル & 抽出", "⛓️ 公差チェーン", "📊 解析結果"])
    
    # === Tab 1: 3D Model & Extraction ===
    with tab_model:
        col_upload, col_3d = st.columns([1, 2])
        
        with col_upload:
            st.subheader("📁 ファイルアップロード")
            uploaded_cad = st.file_uploader("STEP/STL ファイル", type=["step", "stp", "stl"], key="tol_upload")
            
            if uploaded_cad:
                st.success(f"✅ {uploaded_cad.name} ({len(uploaded_cad.getvalue())/1024:.1f} KB)")
                default_tolerance = st.number_input("デフォルト公差 (±mm)", min_value=0.001, value=0.1, step=0.01)
                
                if st.button("🔍 3Dモデル読み込み & 寸法抽出", use_container_width=True, type="primary"):
                    import tempfile
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_cad.name)[1]) as tf:
                        tf.write(uploaded_cad.getbuffer())
                        temp_path = tf.name
                    
                    with st.spinner("メッシュ抽出中..."):
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
                                st.success("✅ STLメッシュ読み込み完了")
                                
                            else:
                                # For STEP, use docker exec to antigravity with FreeCAD
                                docker_temp = f"/tmp/cad_input{ext}"
                                
                                # Copy file to container
                                copy_cmd = f'docker cp "{temp_path}" clawstack-antigravity-1:{docker_temp}'
                                result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)
                                
                                if result.returncode != 0:
                                    st.error(f"ファイルコピーエラー: {result.stderr}")
                                else:
                                    # Run extraction script
                                    extract_cmd = f'docker exec clawstack-antigravity-1 python3 /work/scripts/extract_mesh.py {docker_temp}'
                                    result = subprocess.run(extract_cmd, shell=True, capture_output=True, text=True, timeout=120)
                                    
                                    if result.returncode == 0 and result.stdout:
                                        mesh_result = json.loads(result.stdout)
                                        if "error" in mesh_result:
                                            st.error(f"抽出エラー: {mesh_result['error']}")
                                        else:
                                            st.session_state.mesh_data = mesh_result
                                            st.session_state.extracted_dims = mesh_result.get("dimensions", [])
                                            for d in st.session_state.extracted_dims:
                                                d["tolerance"] = default_tolerance
                                            st.success(f"✅ {len(st.session_state.extracted_dims)} 寸法を抽出")
                                    else:
                                        st.warning("⚠️ STEP抽出失敗。手動入力モードを使用してください。")
                                        st.session_state.mesh_data = None
                            
                        except Exception as e:
                            st.error(f"処理エラー: {e}")
                        finally:
                            os.unlink(temp_path)
                    
                    st.rerun()
            
            # Extracted dimensions list
            if st.session_state.extracted_dims:
                st.markdown("---")
                st.subheader("📏 抽出された寸法")
                for i, dim in enumerate(st.session_state.extracted_dims[:10]):  # Show first 10
                    col_d1, col_d2 = st.columns([3, 1])
                    with col_d1:
                        label = dim.get("label", chr(65 + i))
                        st.write(f"**{label}**: {dim['name']} = {dim['nominal']:.3f} mm")
                    with col_d2:
                        if st.button("➕", key=f"add_dim_{i}", help="チェーンに追加"):
                            st.session_state.tol_dimensions.append({
                                "name": dim['name'],
                                "nominal": dim['nominal'],
                                "tolerance": dim.get('tolerance', 0.1),
                                "direction": "+"
                            })
                            st.rerun()
        
        with col_3d:
            st.subheader("🔷 3Dビュー")
            
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
                        hovertext='クリックで面を選択'
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
                        name='X寸法'
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
                    st.success(f"🎯 クリック検出: {selected_points}")
                    # Get clicked point info
                    for pt in selected_points:
                        if 'pointNumber' in pt:
                            face_idx = pt['pointNumber'] // 3  # Approximate face index
                            st.write(f"選択された面: 約 {face_idx}")
                            
                            # Add dimension from clicked face
                            if st.session_state.extracted_dims and face_idx < len(st.session_state.extracted_dims):
                                dim = st.session_state.extracted_dims[face_idx]
                                if st.button(f"➕ {dim['name']} をチェーンに追加", key=f"add_click_{face_idx}"):
                                    st.session_state.tol_dimensions.append({
                                        "name": dim['name'],
                                        "nominal": dim['nominal'],
                                        "tolerance": dim.get('tolerance', 0.1),
                                        "direction": "+"
                                    })
                                    st.rerun()
                
                # Face selection UI
                st.markdown("---")
                st.subheader("🎯 面選択")
                if st.session_state.extracted_dims:
                    # Create face selector with colors
                    face_options = {f"{chr(65+i)}: {d['name']} ({d['nominal']:.2f}mm)": i 
                                   for i, d in enumerate(st.session_state.extracted_dims[:20])}
                    
                    selected_face = st.selectbox("寸法を選択", list(face_options.keys()), key="face_select")
                    
                    col_sel1, col_sel2 = st.columns(2)
                    with col_sel1:
                        direction = st.radio("方向", ["+", "-"], horizontal=True, key="dir_select")
                    with col_sel2:
                        if st.button("⛓️ チェーンに追加", type="primary", use_container_width=True):
                            idx = face_options[selected_face]
                            dim = st.session_state.extracted_dims[idx]
                            st.session_state.tol_dimensions.append({
                                "name": dim['name'],
                                "nominal": dim['nominal'],
                                "tolerance": dim.get('tolerance', 0.1),
                                "direction": direction
                            })
                            st.success(f"✅ {dim['name']} を追加しました")
                            st.rerun()
                else:
                    st.caption("📏 ファイルをアップロードして寸法を抽出してください")
            else:
                st.info("📁 左側からSTEP/STLファイルをアップロードして3Dモデルを表示")
                
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
                    title="デモ: 単位立方体"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # === Tab 2: Tolerance Chain ===
    with tab_dims:
        col_add, col_chain = st.columns([1, 2])
        
        with col_add:
            st.subheader("➕ 寸法を追加")
            
            with st.form("add_dim_form"):
                dim_name = st.text_input("寸法名", f"DIM_{len(st.session_state.tol_dimensions)+1}")
                dim_nominal = st.number_input("公称値 (mm)", value=10.0, step=0.1)
                dim_tol = st.number_input("公差 (±mm)", value=0.1, step=0.01, min_value=0.001)
                dim_direction = st.radio("方向", ["+", "-"], horizontal=True, 
                                        help="+ = 正方向に寄与, - = 負方向に寄与")
                
                if st.form_submit_button("➕ チェーンに追加", use_container_width=True):
                    st.session_state.tol_dimensions.append({
                        "name": dim_name,
                        "nominal": dim_nominal,
                        "tolerance": dim_tol,
                        "direction": dim_direction
                    })
                    st.rerun()
            
            if st.button("🗑️ チェーンをクリア", use_container_width=True):
                st.session_state.tol_dimensions = []
                st.session_state.tol_result = None
                st.rerun()
        
        with col_chain:
            st.subheader("⛓️ 公差チェーン")
            
            if st.session_state.tol_dimensions:
                dims_df = pd.DataFrame(st.session_state.tol_dimensions)
                edited_dims = st.data_editor(
                    dims_df,
                    use_container_width=True,
                    num_rows="dynamic",
                    column_config={
                        "name": st.column_config.TextColumn("寸法名"),
                        "nominal": st.column_config.NumberColumn("公称値 (mm)", format="%.4f"),
                        "tolerance": st.column_config.NumberColumn("公差 (±mm)", format="%.4f"),
                        "direction": st.column_config.SelectboxColumn("方向", options=["+", "-"])
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
                    st.metric("チェーン公称値", f"{chain_nominal:.4f} mm")
                with col_m2:
                    st.metric("寸法数", len(st.session_state.tol_dimensions))
                
                if st.button("📊 解析実行", use_container_width=True, type="primary"):
                    import math
                    import random
                    
                    dims = st.session_state.tol_dimensions
                    
                    # Worst Case
                    wc_upper = sum(d["tolerance"] for d in dims)
                    
                    # RSS (3σ)
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
                st.info("📐 左側から寸法を追加するか、3Dモデルタブで寸法を選択してください")
    
    # === Tab 3: Results ===
    with tab_result:
        if st.session_state.tol_result:
            r = st.session_state.tol_result
            
            # Summary cards
            st.subheader("📊 解析サマリ")
            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                st.metric("公称値", f"{r['nominal']:.4f} mm")
            with col_r2:
                st.metric("Worst Case", f"±{r['wc_upper']:.4f} mm", delta_color="off")
            with col_r3:
                st.metric("RSS (3σ)", f"±{r['rss']:.4f} mm", delta_color="off")
            with col_r4:
                st.metric("Monte Carlo σ", f"{r['mc_std']:.4f} mm", delta_color="off")
            
            # Results comparison table
            st.markdown("---")
            results_df = pd.DataFrame([
                {"手法": "Worst Case", "上限": r['nominal'] + r['wc_upper'], "下限": r['nominal'] - r['wc_upper'], "範囲": r['wc_upper'] * 2},
                {"手法": "RSS (3σ)", "上限": r['nominal'] + r['rss'], "下限": r['nominal'] - r['rss'], "範囲": r['rss'] * 2},
                {"手法": "Monte Carlo (3σ)", "上限": r['mc_mean'] + 3*r['mc_std'], "下限": r['mc_mean'] - 3*r['mc_std'], "範囲": 6*r['mc_std']},
            ])
            st.dataframe(results_df, use_container_width=True, hide_index=True)
            
            # Sensitivity chart
            col_sens, col_hist = st.columns(2)
            
            with col_sens:
                st.subheader("🎯 感度分析")
                sens_df = pd.DataFrame([{"寸法": k, "寄与度": v} for k, v in r['sensitivities'].items()])
                sens_df = sens_df.sort_values("寄与度", ascending=True)
                
                import plotly.express as px
                fig_sens = px.bar(sens_df, x="寄与度", y="寸法", orientation='h',
                                 color="寄与度", color_continuous_scale="Blues")
                fig_sens.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig_sens, use_container_width=True)
            
            with col_hist:
                st.subheader("📈 Monte Carlo分布")
                import plotly.express as px
                
                fig_hist = px.histogram(x=r['mc_histogram'], nbins=50)
                fig_hist.add_vline(x=r['mc_mean'], line_dash="dash", line_color="red", annotation_text="μ")
                fig_hist.add_vline(x=r['mc_mean'] - 3*r['mc_std'], line_dash="dot", line_color="orange")
                fig_hist.add_vline(x=r['mc_mean'] + 3*r['mc_std'], line_dash="dot", line_color="orange")
                fig_hist.update_layout(height=300, xaxis_title="累積公差 (mm)", yaxis_title="頻度")
                st.plotly_chart(fig_hist, use_container_width=True)
            
            # Export buttons
            st.markdown("---")
            col_exp1, col_exp2 = st.columns(2)
            
            with col_exp1:
                report_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>公差解析レポート</title>
<style>body{{font-family:sans-serif;padding:20px;background:#1a1a2e;color:#eee}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #444;padding:8px}}
th{{background:#667eea}}.metric{{background:#2d2d44;padding:15px;border-radius:8px;margin:5px}}</style></head>
<body><h1>📊 公差解析レポート</h1>
<p>生成: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<div style="display:flex;gap:10px;">
<div class="metric"><h3>公称値</h3><p>{r['nominal']:.4f} mm</p></div>
<div class="metric"><h3>Worst Case</h3><p>±{r['wc_upper']:.4f} mm</p></div>
<div class="metric"><h3>RSS</h3><p>±{r['rss']:.4f} mm</p></div>
<div class="metric"><h3>MC σ</h3><p>{r['mc_std']:.4f} mm</p></div>
</div>
<h2>寸法一覧</h2><table><tr><th>名称</th><th>公称値</th><th>公差</th><th>方向</th><th>寄与度</th></tr>
{"".join(f'<tr><td>{d["name"]}</td><td>{d["nominal"]:.4f}</td><td>±{d["tolerance"]:.4f}</td><td>{d["direction"]}</td><td>{r["sensitivities"].get(d["name"],0):.1f}%</td></tr>' for d in st.session_state.tol_dimensions)}
</table></body></html>"""
                st.download_button("📄 HTMLレポート", report_html, "tolerance_report.html", "text/html", use_container_width=True)
            
            with col_exp2:
                csv_data = "名称,公称値,公差,方向,寄与度\n" + "\n".join(
                    f'{d["name"]},{d["nominal"]},{d["tolerance"]},{d["direction"]},{r["sensitivities"].get(d["name"],0):.1f}'
                    for d in st.session_state.tol_dimensions
                )
                st.download_button("📊 CSVエクスポート", csv_data, "tolerance_data.csv", "text/csv", use_container_width=True)
        else:
            st.info("📐 公差チェーンタブで寸法を追加し、解析を実行してください")

elif page == "書籍原稿生成":
    st.header("📚 書籍原稿生成 (Kindle Unlimited)")
    st.markdown("""
    **使い方:**
    1. `/consume/Kindle/` にプロジェクトフォルダを作成（例: `FEM_Impact`）
    2. 資料（PDF, PPTX, TXT, DOCX）をフォルダに配置
    3. IMPACT FEMを起動してスクリーンショットを取得（オプション）
    4. AIが資料と画像を読み込み、原稿を生成
    
    ---
    """)
    
    # List available Kindle project folders
    kindle_projects = []
    if os.path.exists(KINDLE_DIR):
        kindle_projects = [d for d in os.listdir(KINDLE_DIR) if os.path.isdir(os.path.join(KINDLE_DIR, d))]
    
    if not kindle_projects:
        st.warning(f"Kindleプロジェクトが見つかりません。`{KINDLE_DIR}/` にフォルダを作成してください。")
    else:
        selected_project = st.selectbox("📁 プロジェクト選択", kindle_projects)
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
        
        st.write(f"**資料ファイル ({len(project_files)}件):**")
        for f in project_files[:10]:  # Show first 10
            fpath = os.path.join(project_path, f)
            size_kb = os.path.getsize(fpath) / 1024
            st.write(f"- {f} ({size_kb:.1f} KB)")
        if len(project_files) > 10:
            st.write(f"... 他 {len(project_files) - 10} 件")
        
        # IMPACT Control Section
        st.markdown("---")
        st.subheader("📸 IMPACT FEM スクリーンショット")
        
        impact_col1, impact_col2, impact_col3 = st.columns(3)
        
        with impact_col1:
            if st.button("🚀 IMPACT起動", use_container_width=True):
                import subprocess
                try:
                    result = subprocess.run(
                        ["bash", "/work/scripts/impact_vnc.sh", "start"],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        st.success("✅ IMPACT起動完了!")
                        st.info("🌐 http://localhost:6080/vnc.html でGUI操作可能")
                    else:
                        st.error(f"エラー: {result.stderr or result.stdout}")
                except Exception as e:
                    st.error(f"起動失敗: {e}")
        
        with impact_col2:
            screenshot_name = st.text_input("スクショ名", f"screen_{datetime.datetime.now().strftime('%H%M%S')}")
            if st.button("📷 スクリーンショット取得", use_container_width=True):
                import subprocess
                screenshot_path = os.path.join(images_dir, f"{screenshot_name}.png")
                try:
                    result = subprocess.run(
                        ["bash", "/work/scripts/impact_vnc.sh", "screenshot", screenshot_path],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0 and os.path.exists(screenshot_path):
                        st.success(f"✅ 保存: {screenshot_path}")
                        st.image(screenshot_path, caption=screenshot_name, width=300)
                    else:
                        st.error(f"エラー: {result.stderr or result.stdout}")
                except Exception as e:
                    st.error(f"取得失敗: {e}")
        
        with impact_col3:
            if st.button("🛑 IMPACT停止", use_container_width=True):
                import subprocess
                try:
                    subprocess.run(["bash", "/work/scripts/impact_vnc.sh", "stop"], timeout=10)
                    st.success("✅ IMPACT停止完了")
                except Exception as e:
                    st.warning(f"停止中にエラー: {e}")
        
        # Show existing images
        existing_images = [f for f in os.listdir(images_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))] if os.path.exists(images_dir) else []
        if existing_images:
            with st.expander(f"📷 保存済み画像 ({len(existing_images)}枚)"):
                img_cols = st.columns(3)
                for i, img in enumerate(existing_images[:9]):
                    with img_cols[i % 3]:
                        st.image(os.path.join(images_dir, img), caption=img, width=150)
        
        # ---------------------------------------------------------
        # ③ シミュレーション実行 (P018)
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("③ Impact FEM シミュレーション実行 (P018)")
        
        # Filter .in files
        in_files = [f for f in project_files if f.lower().endswith(".in")]
        
        if not in_files:
            st.info("⚠️ `.in` ファイル（入力データ）が見つかりません。")
        else:
            selected_in_file = st.selectbox("対象の入力ファイル (.in)", in_files)
            target_in_path = os.path.join(project_path, selected_in_file)
            
            c1, c2 = st.columns(2)
            
            with c1:
                if st.button("🚀 シミュレーション実行 (Background)", use_container_width=True):
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
                        
                        with st.spinner("シミュレーション実行中... (ログは下に表示されます)"):
                            process = subprocess.Popen(
                                java_cmd, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True, 
                                cwd=os.path.dirname(target_in_path) # Run in file's dir
                            )
                            stdout, stderr = process.communicate()
                            
                            if process.returncode == 0:
                                st.success("✅ 計算完了！")
                            else:
                                st.error(f"❌ エラー発生 (Exit Code: {process.returncode})")
                            
                            with st.expander("実行ログ (STDOUT)", expanded=True):
                                st.code(stdout)
                            if stderr:
                                with st.expander("エラーログ (STDERR)", expanded=True):
                                    st.code(stderr)
                                    
                    except Exception as e:
                        st.error(f"Execution Error: {e}")

            with c2:
                if st.button("📘 この解析の解説生成 (AI)", use_container_width=True):
                    with st.spinner("解析内容を分析中..."):
                         # Read the .in file
                        try:
                            with open(target_in_path, "r", encoding="utf-8", errors="ignore") as f:
                                in_content = f.read()
                            
                            prompt = f"""
あなたはCAE解析の専門家です。以下のImpact FEM入力ファイル(`{selected_in_file}`)を分析し、
このシミュレーションが「何を」「どういう条件で」解析しようとしているのか、
一般のエンジニアにもわかるように解説レポートを作成してください。

# 項目
1. **解析の目的**: 何が何に衝突するのか、など
2. **モデル概要**: ノード数、要素タイプ、材料（Materials）
3. **境界条件 (Constraints)**: どこが固定されているか、初速度はいくらか
4. **期待される結果**: どのような物理現象（貫通、跳ね返り、変形）が見られるはずか

# 入力ファイル内容
{in_content[:20000]}
"""
                            explanation = ask_ai(prompt)
                            st.markdown(explanation)
                        except Exception as e:
                            st.error(f"Analysis Error: {e}")

        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("① 資料読み込み")
            include_code = st.checkbox("ソースコード(.py, .java, .md等)も含める", value=True)
            if st.button("🔍 資料を解析", use_container_width=True):
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
                        st.warning(f"{f}: 読み込みエラー ({e})")
                
                st.session_state.kindle_content = combined_text
                st.session_state.kindle_images = existing_images
                st.success(f"✅ {len(combined_text)}文字読み込み完了 + 画像{len(existing_images)}枚")
                with st.expander("読み込み内容プレビュー"):
                    st.text(combined_text[:3000] + "..." if len(combined_text) > 3000 else combined_text)
        
        with col2:
            st.subheader("② 原稿生成")
            book_title = st.text_input("書籍タイトル", f"{selected_project}入門")
            target_pages = st.number_input("目標ページ数", min_value=10, max_value=200, value=50)
            
            if st.button("✨ AIで原稿生成", use_container_width=True):
                if "kindle_content" not in st.session_state or not st.session_state.kindle_content:
                    st.error("先に「資料を解析」を実行してください")
                else:
                    # Build image references
                    image_refs = ""
                    if existing_images:
                        image_refs = "\n\n利用可能な画像:\n" + "\n".join([f"- {img}" for img in existing_images])
                    
                    prompt = f"""
あなたはプロの技術書ライターです。以下の資料（ソースコード、ドキュメント、スライド）を元に、
Kindle出版用の技術書「{book_title}」の原稿(Markdown形式)を執筆してください。

# 要件
- ターゲット: 初学者から中級者
- 文字数: {target_pages * 400}文字程度を目指す
- 構成:
  1. はじめに（プロジェクトの概要）
  2. **環境構築と起動方法**（コードやスクリプトから推測し、具体的なコマンドを記載すること）
  3. 主要機能の解説（ソースコードの構造解析を含むこと）
  4. チュートリアル（具体的な操作手順）
  5. まとめ
- 文体: 親しみやすい「です・ます」調
- 画像の挿入: 以下の画像を適切な場所に挿入してください。形式: ![説明](images/ファイル名)
  (特にGUIのスクリーンショットや図解がある場合は積極的に使うこと)

# 画像リスト
{image_refs}

# 資料・ソースコード
{st.session_state.kindle_content[:150000]} 
"""
                    with st.spinner("原稿生成中... (数分かかる場合があります)"):
                        result = ask_ai(prompt)
                    
                    st.session_state.kindle_manuscript = result
                    st.success("✅ 原稿生成完了!")
        
        # Display manuscript
        if "kindle_manuscript" in st.session_state and st.session_state.kindle_manuscript:
            st.markdown("---")
            st.subheader("📖 生成された原稿")
            st.markdown(st.session_state.kindle_manuscript)
            
            # Save button
            fn = f"{selected_project}_原稿_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.md"
            if st.download_button("📥 Markdownでダウンロード", st.session_state.kindle_manuscript, file_name=fn):
                st.success(f"保存完了: {fn}")

        # Check for existing reports
        st.markdown("---")
        st.subheader("📂 保存済み原稿")
        report_files = [f for f in os.listdir(WORK_DIR) if f.startswith(selected_project) and f.endswith(".md")] if os.path.exists(WORK_DIR) else []
        
        if report_files:
            for rf in report_files:
                rf_path = os.path.join(WORK_DIR, rf)
                with open(rf_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                col_d1, col_d2 = st.columns([3, 1])
                with col_d1:
                    st.text(f"📄 {rf} ({os.path.getsize(rf_path)/1024:.1f} KB)")
                with col_d2:
                    st.download_button("📥 ダウンロード", content, file_name=rf, key=f"dl_{rf}")
        else:
            st.info("保存された原稿はありません。")

# -------------------------
# P016: Email Reporting
# -------------------------
elif page == "📧 Email報告 (P016)":
    st.header("📧 Email Daily Report (P016)")
    st.info("P016: 依頼・QIF・会議の3点セットを毎日まとめ報告します。")

    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Date Filter
        today = datetime.date.today()
        start_date = st.date_input("開始日", today)
        end_date = st.date_input("終了日", today)
        
        if st.button("🚀 レポート生成", use_container_width=True):
            with st.spinner("メール解析中... (数分かかります)"):
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
                    st.success("✅ レポート生成完了!")
                    st.text_area("Log Output", result.stdout, height=200)
                except subprocess.CalledProcessError as e:
                    st.error(f"Error: {e}")
                    st.text_area("Error Output", e.stderr, height=200)

    # List Reports
    st.markdown("---")
    st.subheader("📂 過去のレポート")
    
    if os.path.exists(WORK_DIR):
        reports = [f for f in os.listdir(WORK_DIR) if f.startswith("Email_Report_") and f.endswith(".md")]
        reports.sort(reverse=True)
        
        if reports:
            selected_report = st.selectbox("レポートを選択", reports)
            
            if selected_report:
                rpath = os.path.join(WORK_DIR, selected_report)
                with open(rpath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                st.markdown(content)
                st.download_button("📥 ダウンロード", content, file_name=selected_report)
        else:
            st.info("レポートはまだ生成されていません。")

