
import numpy as np
import matplotlib.pyplot as plt
import os
import base64
import json
import math

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

# --- 1. Simulation Logic (Preserved) ---
tols_x = { "Strip": 0.15, "Punch": 0.05, "Frame": 0.02, "Feed": 0.0115 }
tols_y = { "Strip": 0.15, "Punch": 0.05, "Frame": 0.02 }

sim_x = np.random.normal(1.500, 0.05, 100000)
sim_y = np.random.normal(0.575, 0.05, 100000)

def get_stats(data, lsl=0.0):
    mean = np.mean(data)
    std = np.std(data)
    cpk = (mean - lsl) / (3 * std)
    return mean, std, cpk

stats_x = get_stats(sim_x)
stats_y = get_stats(sim_y)

def create_hist(data, filename, title, stats):
    plt.figure(figsize=(6, 4))
    plt.hist(data, bins=50, color='#3498db', alpha=0.7, density=True)
    plt.axvline(0, color='r', linestyle='--', label='Interference')
    plt.title(f"{title}\nCpk={stats[2]:.2f}")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, filename))
    plt.close()

create_hist(sim_x, "hist_x_v9.png", "X-Axis Gap", stats_x)
create_hist(sim_y, "hist_y_v9.png", "Y-Axis Gap", stats_y)

def get_b64(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_x = get_b64("hist_x_v9.png")
img_y = get_b64("hist_y_v9.png")

# --- 2. 3D Model Processing (Mesh Support) ---
def parse_obj(filename):
    path = os.path.join(MODEL_DIR, filename)
    vertices = []
    indices = []
    print(f"Loading {filename}...")
    
    if not os.path.exists(path):
        return {"v": [], "i": []}

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            parts = line.split()
            if parts[0] == 'v':
                # v x y z
                try:
                    v = [float(x) for x in parts[1:4]]
                    vertices.extend(v)
                except: pass
            
            elif parts[0] == 'f':
                # f v1/vt/vn v2...
                # Triangulate logic: assume standard convex polygon (fan)
                # Parse indices (1-based) and convert to 0-based
                # Only take the vertex index (before first /)
                poly_verts = []
                for p in parts[1:]:
                    v_idx_str = p.split('/')[0]
                    poly_verts.append(int(v_idx_str) - 1)
                
                # Simple fan triangulation for n-gons (usually FreeCAD exports triangles or quads)
                # 0, 1, 2; 0, 2, 3; ...
                for i in range(1, len(poly_verts) - 1):
                    indices.extend([poly_verts[0], poly_verts[i], poly_verts[i+1]])

    print(f"  -> Vertices: {len(vertices)//3}, Indices: {len(indices)}")
    return {"v": vertices, "i": indices}

# Load full mesh data
data_frame = parse_obj("frame.obj")
data_punch = parse_obj("punch.obj")
data_strip = parse_obj("product_1.obj")

# --- 3. Read Three.js Library ---
three_js_content = ""
if os.path.exists(THREE_JS_PATH):
    with open(THREE_JS_PATH, "r", encoding="utf-8") as f:
        three_js_content = f.read()

# --- 4. HTML Generation ---
html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gap Analysis Report (Wireframe)</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #f4f4f9; margin: 0; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 8px; }}
        .viewer-box {{ width: 100%; height: 600px; background: #222; position: relative; overflow: hidden; border-radius: 4px; border: 1px solid #444; }}
        #loading {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; }}
        
        .stats-grid {{ display: flex; gap: 20px; margin-top: 30px; }}
        .stat-card {{ flex: 1; padding: 20px; border: 1px solid #eee; text-align: center; background: #fff; border-radius: 8px; }}
        img {{ max-width: 100%; height: auto; border: 1px solid #eee; }}
        
        .legend {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 15px; font-weight: bold; font-size: 0.9em; }}
        .dot {{ width: 12px; height: 12px; display: inline-block; margin-right: 5px; }}
    </style>
    <script>{three_js_content}</script>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>Tolerance Gap Analysis Report (v9)</h1>
        <p>Wireframe Visualization Mode</p>
    </div>

    <div class="legend">
        <span><i class="dot" style="background:#aaaaaa;"></i> Frame</span>
        <span><i class="dot" style="background:#5dade2;"></i> Punch</span>
        <span><i class="dot" style="background:#f4d03f;"></i> Strip</span>
    </div>
    
    <div class="viewer-box" id="viewer3d">
        <div id="loading">Initializing Mesh Engine...</div>
    </div>
    <div style="text-align:center; font-size:0.8em; color:#666; margin-top:5px;">
        Left Mouse: Rotate | Right Mouse: Pan | Scroll: Zoom
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <h3>X-Axis (Gap 1.5mm)</h3>
            <img src="{img_x}">
            <p>Cpk: {stats_x[2]:.2f}</p>
        </div>
        <div class="stat-card">
            <h3>Y-Axis (Gap 0.575mm)</h3>
            <img src="{img_y}">
            <p>Cpk: {stats_y[2]:.2f}</p>
        </div>
    </div>
</div>

<!-- MESH DATA -->
<script type="application/json" id="d-frame">{json.dumps(data_frame)}</script>
<script type="application/json" id="d-punch">{json.dumps(data_punch)}</script>
<script type="application/json" id="d-strip">{json.dumps(data_strip)}</script>

<script>
    function main() {{
        if (typeof THREE === 'undefined') return;

        const container = document.getElementById('viewer3d');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x222222);

        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 10000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(renderer.domElement);

        scene.add(new THREE.AxesHelper(20));
        const grid = new THREE.GridHelper(300, 60, 0x444444, 0x2a2a2a);
        grid.rotation.x = Math.PI/2;
        scene.add(grid);

        // Lighting (Simple)
        const ambient = new THREE.AmbientLight(0xffffff, 0.6);
        scene.add(ambient);
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(50, 50, 100);
        scene.add(dirLight);

        const fullBox = new THREE.Box3();
        let hasData = false;

        function addMesh(id, color) {{
            try {{
                const txt = document.getElementById(id).textContent;
                const json = JSON.parse(txt);
                if (json.v.length === 0) return;

                const geo = new THREE.BufferGeometry();
                geo.setAttribute('position', new THREE.Float32BufferAttribute(json.v, 3));
                if (json.i.length > 0) {{
                    geo.setIndex(json.i);
                }}

                // Wireframe Material
                const mat = new THREE.MeshBasicMaterial({{ 
                    color: color, 
                    wireframe: true,
                    opacity: 0.8,
                    transparent: true
                }});

                const mesh = new THREE.Mesh(geo, mat);
                scene.add(mesh);

                geo.computeBoundingBox();
                fullBox.expandByObject(mesh);
                hasData = true;
            }} catch(e) {{ console.error(e); }}
        }}

        addMesh("d-frame", 0xaaaaaa);
        addMesh("d-punch", 0x5dade2);
        addMesh("d-strip", 0xf4d03f);

        document.getElementById('loading').style.display = 'none';

        // Auto Center
        const target = new THREE.Vector3();
        if(hasData) {{
            fullBox.getCenter(target);
            const size = new THREE.Vector3();
            fullBox.getSize(size);
            const maxDim = Math.max(size.x, size.y, size.z);
            
            camera.position.x = target.x + maxDim;
            camera.position.y = target.y + maxDim * 0.5;
            camera.position.z = target.z + maxDim * 2.5;
            
            camera.lookAt(target);
        }} else {{
            camera.position.set(50,50,50);
            camera.lookAt(0,0,0);
        }}

        // Controls
        let isDragging = false;
        let prevX = 0, prevY = 0;
        
        container.addEventListener('mousedown', e => {{ isDragging = true; prevX = e.clientX; prevY = e.clientY; }});
        window.addEventListener('mouseup', () => isDragging = false);
        container.addEventListener('mousemove', e => {{
            if(isDragging) {{
                const deltaX = e.clientX - prevX;
                const deltaY = e.clientY - prevY;
                prevX = e.clientX; prevY = e.clientY;

                const offset = camera.position.clone().sub(target);
                let r = offset.length();
                let theta = Math.atan2(offset.x, offset.z);
                let phi = Math.acos(offset.y / r);

                theta -= deltaX * 0.005;
                phi -= deltaY * 0.005;
                phi = Math.max(0.01, Math.min(Math.PI - 0.01, phi));

                camera.position.x = target.x + r * Math.sin(phi) * Math.sin(theta);
                camera.position.y = target.y + r * Math.cos(phi);
                camera.position.z = target.z + r * Math.sin(phi) * Math.cos(theta);
                camera.lookAt(target);
            }}
        }});
        
        container.addEventListener('wheel', e => {{
            e.preventDefault();
            const dir = new THREE.Vector3();
            camera.getWorldDirection(dir);
            camera.position.addScaledVector(dir, -e.deltaY * 0.05);
        }});
        
        window.addEventListener('resize', () => {{
            camera.aspect = container.clientWidth / container.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(container.clientWidth, container.clientHeight);
        }});

        function animate() {{
            requestAnimationFrame(animate);
            renderer.render(scene, camera);
        }}
        animate();
    }}
    setTimeout(main, 100);
</script>
</body>
</html>
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Final Report v9 (Wireframe) Generated: {REPORT_PATH}")
