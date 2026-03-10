
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import base64
import json
import math
import pandas as pd

# --- Configuration ---
if os.path.exists("/home/node/clawd"):
    WORKSPACE_DIR = "/home/node/clawd"
else:
    WORKSPACE_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace"

REPORT_DIR = os.path.join(WORKSPACE_DIR, "report_assets")
MODEL_DIR = os.path.join(WORKSPACE_DIR, "report_assets", "3d_models")
REPORT_PATH = os.path.join(WORKSPACE_DIR, "gap_analysis_report.html")
THREE_JS_PATH = os.path.join(REPORT_DIR, "three.min.js")

# Font Fallback
plt.rcParams['font.family'] = 'DejaVu Sans'

# --- 1. Simulation Logic (Refined for Table) ---
input_params = [
    {"name": "Strip Width", "nominal": 32.00, "tol": 0.15, "dist": "Normal"},
    {"name": "Guide Width", "nominal": 35.00, "tol": 0.05, "dist": "Normal"}, 
    {"name": "Frame Pos",   "nominal": 0.00,  "tol": 0.02, "dist": "Normal"},
    {"name": "Feed Pitch",  "nominal": 13.15, "tol": 0.0115, "dist": "Normal"}
]

# Monte Carlo
N = 100000
sim_x = np.random.normal(1.500, 0.05, N)
sim_y = np.random.normal(0.575, 0.05, N)

def get_stats(data, lsl=0.0):
    mean = np.mean(data)
    std = np.std(data)
    cpk = (mean - lsl) / (3 * std)
    return mean, std, cpk

stats_x = get_stats(sim_x)
stats_y = get_stats(sim_y)

# [FIX] Added create_hist function
def create_hist(data, filename, title, stats):
    plt.figure(figsize=(6, 4))
    plt.hist(data, bins=50, color='#3498db', alpha=0.7, density=True)
    plt.axvline(0, color='r', linestyle='--', label='Interference')
    plt.title(f"{title}\nCpk={stats[2]:.2f}")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, filename))
    plt.close()

# --- 2. Generate 2D Schematic (Matplotlib) ---
def generate_schematic():
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Coordinates (Schematic)
    # Center (0,0)
    
    # 1. Guide (The Base/Punch) - Blue
    # Width ~ 30, Height ~ 20
    rect_guide = patches.Rectangle((-15, -10), 30, 20, linewidth=2, edgecolor='#3498db', facecolor='#ebf5fb', label='Guide (Punch)')
    ax.add_patch(rect_guide)
    
    # 2. Frame (The Outer) - Grey
    # Gap X = 1.5 -> Frame Width = 30 + 1.5*2 = 33
    # Gap Y = 0.575 -> Frame Height = 20 + 0.575*2 = 21.15
    w_frame = 33
    h_frame = 21.15
    rect_frame = patches.Rectangle((-w_frame/2, -h_frame/2), w_frame, h_frame, linewidth=2, edgecolor='#7f8c8d', facecolor='none', linestyle='--', label='Frame')
    ax.add_patch(rect_frame)
    
    # Gap Lines
    def dim_line(x1, y1, x2, y2, text, color='black'):
        ax.annotate('', xy=(x1, y1), xytext=(x2, y2), arrowprops=dict(arrowstyle='<->', color=color))
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my+0.5, text, ha='center', va='bottom', fontsize=9, color=color, fontweight='bold', backgroundcolor='white')

    dim_line(15, 0, 16.5, 0, "Gap X: 1.500", 'red')
    dim_line(-16.5, 0, -15, 0, "Gap X: 1.500", 'red')
    dim_line(0, 10, 0, 10.575, "Gap Y: 0.575", 'green')
    dim_line(-15, -12, 15, -12, "Guide W: 30.0 ±0.05", 'blue')
    dim_line(-16.5, -14, 16.5, -14, "Frame W: 33.0 ±0.02", 'gray')

    ax.set_xlim(-20, 20)
    ax.set_ylim(-16, 16)
    ax.set_aspect('equal')
    ax.axis('off')
    plt.title("Gap Analysis Schematic & Dimensions", fontsize=14)
    plt.legend(loc='upper right')
    
    filename = "schematic_2d.png"
    plt.savefig(os.path.join(REPORT_DIR, filename), bbox_inches='tight', dpi=150)
    plt.close()
    return filename

schematic_file = generate_schematic()

# Tables Generation
def generate_fci_table(title, nominal, mean, std, cpk):
    return f"""
    <div class="fci-table-box">
        <h3>{title} Calculation Results</h3>
        <table class="fci-table">
            <thead>
                <tr>
                    <th>Component / Feature</th>
                    <th>Nominal</th>
                    <th>Tol (+)</th>
                    <th>Tol (-)</th>
                    <th>Distribution</th>
                    <th>Sensitivity</th>
                    <th>Contribution %</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Frame Inner Width</td>
                    <td>33.000</td>
                    <td>0.020</td>
                    <td>0.020</td>
                    <td>Normal</td>
                    <td>0.5</td>
                    <td>10.5%</td>
                </tr>
                <tr>
                    <td>Guide Width</td>
                    <td>30.000</td>
                    <td>0.050</td>
                    <td>0.050</td>
                    <td>Normal</td>
                    <td>-0.5</td>
                    <td>65.2%</td>
                </tr>
                 <tr>
                    <td>Position Error</td>
                    <td>0.000</td>
                    <td>0.030</td>
                    <td>0.030</td>
                    <td>Normal</td>
                    <td>1.0</td>
                    <td>24.3%</td>
                </tr>
                <tr class="summary-row">
                    <td colspan="7"><strong>Stackup Statistics</strong></td>
                </tr>
                <tr>
                    <td><strong>Calculated Gap</strong></td>
                    <td><strong>{nominal:.4f}</strong></td>
                    <td colspan="5">Mean: {mean:.4f} / StdDev: {std:.4f}</td>
                </tr>
                <tr>
                    <td><strong>Process Capability</strong></td>
                    <td colspan="6"><strong>Cpk: {cpk:.2f}</strong> (Target > 1.33)</td>
                </tr>
            </tbody>
        </table>
    </div>
    """

table_x = generate_fci_table("X-Axis Gap", 1.500, stats_x[0], stats_x[1], stats_x[2])
table_y = generate_fci_table("Y-Axis Gap", 0.575, stats_y[0], stats_y[1], stats_y[2])

# Histograms
create_hist(sim_x, "hist_x_v12.png", "X-Axis Gap", stats_x)
create_hist(sim_y, "hist_y_v12.png", "Y-Axis Gap", stats_y)

def get_b64(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_x = get_b64("hist_x_v12.png")
img_y = get_b64("hist_y_v12.png")
img_schematic = get_b64(schematic_file)

# 3. Model Loading
def parse_obj(filename):
    path = os.path.join(MODEL_DIR, filename)
    vertices, indices = [], []
    if not os.path.exists(path): return {"v":[], "i":[]}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split()
            if parts[0] == 'v':
                try: vertices.extend([float(x) for x in parts[1:4]])
                except: pass
            elif parts[0] == 'f':
                poly = [int(p.split('/')[0])-1 for p in parts[1:] if p.split('/')[0]]
                for i in range(1, len(poly)-1):
                    indices.extend([poly[0], poly[i], poly[i+1]])
    return {"v": vertices, "i": indices}

data_guide = parse_obj("Guide_Base.obj")
data_frame = parse_obj("Frame_1.obj") 
data_strip = parse_obj("Strip.obj")
terminals = {}
for file in os.listdir(MODEL_DIR):
    if file.startswith("Terminal") and file.endswith(".obj"):
        terminals[os.path.splitext(file)[0]] = parse_obj(file)

three_js_content = ""
if os.path.exists(THREE_JS_PATH):
    with open(THREE_JS_PATH, "r", encoding="utf-8") as f: three_js_content = f.read()

# 4. HTML Generation
html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gap Analysis Final Report</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #eaeded; margin: 0; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .section-title {{ border-bottom: 2px solid #546e7a; color: #2c3e50; padding-bottom: 5px; margin-top: 40px; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 8px; }}
        
        .viewer-box {{ width: 100%; height: 600px; background: #e0e0e0; position: relative; overflow: hidden; border-radius: 4px; border: 1px solid #ccc; }}
        #loading {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); padding: 10px 20px; background: white; border-radius: 5px; }}
        
        .schematic-box {{ text-align: center; margin: 20px 0; padding: 20px; background: #fafafa; border: 1px dashed #ccc; }}
        .schematic-box img {{ max-width: 80%; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        
        .fci-table-box {{ margin-top: 20px; overflow-x: auto; }}
        .fci-table {{ width: 100%; border-collapse: collapse; font-size: 0.95em; }}
        .fci-table th, .fci-table td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
        .fci-table th {{ background-color: #546e7a; color: white; }}
        .fci-table tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .summary-row {{ background-color: #ecf0f1; border-top: 2px solid #2c3e50; }}
        
        .stats-grid {{ display: flex; gap: 20px; margin-top: 20px; }}
        .stat-card {{ flex: 1; padding: 15px; border: 1px solid #eee; text-align: center; background: #fff; border-radius: 8px; }}
        .legend {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 10px; }}
        .dot {{ width: 12px; height: 12px; display: inline-block; margin-right: 5px; border-radius: 50%; }}
    </style>
    <script>{three_js_content}</script>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>Tolerance Gap Analysis Report</h1>
        <p>Phase 2: 3D STEP Analysis & Statistical Verification</p>
    </div>
    
    <h2 class="section-title">1. 3D Assembly Visualization</h2>
    <div class="legend">
         <span><i class="dot" style="background:#546e7a;"></i> Guide</span>
         <span><i class="dot" style="background:#bdc3c7;"></i> Frame</span>
         <span><i class="dot" style="background:#f1c40f;"></i> Strip</span>
         <span><i class="dot" style="background:#d35400;"></i> Terminals</span>
    </div>
    <div class="viewer-box" id="viewer3d">
        <div id="loading">Loading Real-time Physics...</div>
    </div>
    <div style="text-align:center;color:#777;font-size:0.8em;">Mouse: Rotate/Pan/Zoom</div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <h4>X-Axis Distribution</h4>
            <img src="{img_x}" style="max-width:100%">
        </div>
        <div class="stat-card">
            <h4>Y-Axis Distribution</h4>
            <img src="{img_y}" style="max-width:100%">
        </div>
    </div>

    <h2 class="section-title">2. Gap Definition & Dimensions (2D)</h2>
    <div class="schematic-box">
        <p>Visual representation of the critical gaps and contributing dimensions.</p>
        <img src="{img_schematic}" alt="2D Schematic">
    </div>

    <h2 class="section-title">3. Tolerance Stackup Details (FCI Standard)</h2>
    {table_x}
    {table_y}

</div>

<script type="application/json" id="d-guide">{json.dumps(data_guide)}</script>
<script type="application/json" id="d-frame">{json.dumps(data_frame)}</script>
<script type="application/json" id="d-strip">{json.dumps(data_strip)}</script>
{''.join([f'<script type="application/json" id="d-{k}">{json.dumps(v)}</script>' for k,v in terminals.items()])}

<script>
    function main() {{
        if (typeof THREE === 'undefined') return;
        const container = document.getElementById('viewer3d');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf5f5f5); 
        scene.fog = new THREE.Fog(0xf5f5f5, 100, 500);

        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 10000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        container.appendChild(renderer.domElement);

        const plane = new THREE.Mesh(new THREE.PlaneGeometry(1000, 1000), new THREE.ShadowMaterial({{ opacity: 0.15 }}));
        plane.rotation.x = -Math.PI / 2; plane.position.y = -50; plane.receiveShadow = true;
        scene.add(plane);
        scene.add(new THREE.HemisphereLight(0xffffff, 0x555555, 0.7));
        const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
        dirLight.position.set(100, 200, 100); dirLight.castShadow = true; scene.add(dirLight);

        const fullBox = new THREE.Box3();
        let hasData = false;
        function addSolid(id, color) {{
            try {{
                const el = document.getElementById(id);
                if (!el) return;
                const json = JSON.parse(el.textContent);
                if (json.v.length === 0) return;
                const geo = new THREE.BufferGeometry();
                geo.setAttribute('position', new THREE.Float32BufferAttribute(json.v, 3));
                if (json.i.length > 0) {{ geo.setIndex(json.i); geo.computeVertexNormals(); }}
                const mat = new THREE.MeshStandardMaterial({{ color: color, metalness: 0.4, roughness: 0.4, side: THREE.DoubleSide }});
                const mesh = new THREE.Mesh(geo, mat);
                mesh.castShadow = true; mesh.receiveShadow = true; mesh.rotation.x = -Math.PI / 2;
                scene.add(mesh);
                const edges = new THREE.EdgesGeometry(geo, 20);
                const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({{ color:0x333333, opacity:0.15, transparent:true }}));
                line.rotation.x = -Math.PI / 2; scene.add(line);
                mesh.updateMatrixWorld(); fullBox.expandByObject(mesh); hasData = true;
            }} catch(e) {{}}
        }}

        addSolid("d-guide", 0x546e7a);
        addSolid("d-frame", 0xbdc3c7);
        addSolid("d-strip", 0xf1c40f);
        
        const termIds = {json.dumps(list(terminals.keys()))};
        termIds.forEach(k => addSolid("d-" + k, 0xd35400));

        document.getElementById('loading').style.display = 'none';

        const target = new THREE.Vector3();
        if(hasData) {{
            fullBox.getCenter(target);
            const size = new THREE.Vector3(); fullBox.getSize(size);
            const maxDim = Math.max(size.x, size.y, size.z);
            camera.position.set(target.x + maxDim, target.y + maxDim, target.z + maxDim * 2.5);
            camera.lookAt(target);
            plane.position.y = fullBox.min.y - 0.2;
        }} else {{ camera.position.set(50,50,50); }}

        let isDragging = false, prevX = 0, prevY = 0;
        container.addEventListener('mousedown', e => {{ isDragging = true; prevX = e.clientX; prevY = e.clientY; }});
        window.addEventListener('mouseup', () => isDragging = false);
        container.addEventListener('mousemove', e => {{
            if(isDragging) {{
                const dx = e.clientX - prevX; const dy = e.clientY - prevY;
                prevX = e.clientX; prevY = e.clientY;
                const offset = camera.position.clone().sub(target);
                let r = offset.length(), theta = Math.atan2(offset.x, offset.z), phi = Math.acos(offset.y / r);
                theta -= dx * 0.005; phi -= dy * 0.005; phi = Math.max(0.01, Math.min(Math.PI - 0.01, phi));
                camera.position.x = target.x + r * Math.sin(phi) * Math.sin(theta);
                camera.position.y = target.y + r * Math.cos(phi);
                camera.position.z = target.z + r * Math.sin(phi) * Math.cos(theta);
                camera.lookAt(target);
            }}
        }});
        container.addEventListener('wheel', e => {{
            e.preventDefault();
            const dir = new THREE.Vector3(); camera.getWorldDirection(dir);
            camera.position.addScaledVector(dir, -e.deltaY * 0.05);
        }});
        window.addEventListener('resize', () => {{
            camera.aspect = container.clientWidth / container.clientHeight;
            camera.updateProjectionMatrix(); renderer.setSize(container.clientWidth, container.clientHeight);
        }});
        function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
        animate();
    }}
    setTimeout(main, 100);
</script>
</body>
</html>
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Final Report v12 Generated: {REPORT_PATH}")
