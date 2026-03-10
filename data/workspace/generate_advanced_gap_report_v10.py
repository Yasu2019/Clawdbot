
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

# --- 1. Simulation Logic ---
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

create_hist(sim_x, "hist_x_v10.png", "X-Axis Gap", stats_x)
create_hist(sim_y, "hist_y_v10.png", "Y-Axis Gap", stats_y)

def get_b64(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_x = get_b64("hist_x_v10.png")
img_y = get_b64("hist_y_v10.png")

# --- 2. 3D Model Parsing (Robust) ---
def parse_obj(filename):
    path = os.path.join(MODEL_DIR, filename)
    vertices = []
    indices = []
    print(f"Loading {filename}...")
    
    if not os.path.exists(path):
        print(f"  [ERROR] File not found: {path}")
        return {"v": [], "i": []}

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            parts = line.split()
            if parts[0] == 'v':
                try:
                    v = [float(x) for x in parts[1:4]]
                    vertices.extend(v)
                except: pass
            
            elif parts[0] == 'f':
                # Handle f v1 v2 v3 OR f v1/vt/vn v2...
                poly_verts = []
                for p in parts[1:]:
                    val = p.split('/')[0]
                    if val:
                        poly_verts.append(int(val) - 1)
                
                # Triangulate (Fan)
                # 0-1-2, 0-2-3, ...
                for i in range(1, len(poly_verts) - 1):
                    indices.extend([poly_verts[0], poly_verts[i], poly_verts[i+1]])

    print(f"  -> Vertices: {len(vertices)//3}, Indices: {len(indices)}")
    return {"v": vertices, "i": indices}

# Load ALL relevant models (Added guide/die if found)
data_frame = parse_obj("frame.obj")
data_punch = parse_obj("punch.obj")
data_strip = parse_obj("product_1.obj")

# Check for Guide/Die options
# Based on ls, we might see 'guide.obj' or 'die_plate.obj'. 
# For now, I'll attempt to load 'guide.obj' if it exists, otherwise check common names.
# UPDATE: Based on previous context, user said "Guide (Base Jig)". "Frame" might be the Guide?
# Wait, "Frame" usually implies the structure. 
# I will attempt to load ALL .obj files in the directory to be safe.

extra_models = {}
for file in os.listdir(MODEL_DIR):
    if file.endswith(".obj") and file not in ["frame.obj", "punch.obj", "product_1.obj"]:
        name = os.path.splitext(file)[0]
        extra_models[name] = parse_obj(file)

# --- 3. Read Three.js ---
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
    <title>Gap Analysis Report (Solid)</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #eaeded; margin: 0; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 8px; }}
        .viewer-box {{ width: 100%; height: 700px; background: #e0e0e0; position: relative; overflow: hidden; border-radius: 4px; border: 1px solid #ccc; }}
        #loading {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #333; font-weight: bold; }}
        
        .stats-grid {{ display: flex; gap: 20px; margin-top: 30px; }}
        .stat-card {{ flex: 1; padding: 20px; border: 1px solid #eee; text-align: center; background: #fff; border-radius: 8px; }}
        img {{ max-width: 100%; height: auto; border: 1px solid #eee; }}
        
        .legend {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 15px; font-weight: bold; font-size: 0.9em; }}
        .dot {{ width: 15px; height: 15px; display: inline-block; margin-right: 5px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.2); }}
    </style>
    <script>{three_js_content}</script>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>Tolerance Gap Analysis Report (v10)</h1>
        <p>Solid Visualization Mode • N=100,000 Simulation</p>
    </div>

    <div class="legend">
        <span><i class="dot" style="background:#b0bec5;"></i> Frame (Guide)</span>
        <span><i class="dot" style="background:#3498db;"></i> Punch</span>
        <span><i class="dot" style="background:#f1c40f;"></i> Strip</span>
        <!-- Dynamically added extras -->
        {''.join([f'<span><i class="dot" style="background:#95a5a6;"></i> {k.title()}</span>' for k in extra_models.keys()])}
    </div>
    
    <div class="viewer-box" id="viewer3d">
        <div id="loading">Initializing Solid Engine...</div>
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

<!-- DATA -->
<script type="application/json" id="d-frame">{json.dumps(data_frame)}</script>
<script type="application/json" id="d-punch">{json.dumps(data_punch)}</script>
<script type="application/json" id="d-strip">{json.dumps(data_strip)}</script>
<!-- Extra Data -->
{''.join([f'<script type="application/json" id="d-{k}">{json.dumps(v)}</script>' for k,v in extra_models.items()])}

<script>
    function main() {{
        if (typeof THREE === 'undefined') return;

        const container = document.getElementById('viewer3d');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf0f2f5); // Light background for CAD style
        // scene.fog = new THREE.Fog(0xf0f2f5, 50, 500);

        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 10000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(renderer.domElement);

        // Ground Plane (Shadow catcher)
        const planeGeo = new THREE.PlaneGeometry(500, 500);
        const planeMat = new THREE.ShadowMaterial({{ opacity: 0.1 }});
        const plane = new THREE.Mesh(planeGeo, planeMat);
        plane.rotation.x = -Math.PI / 2;
        plane.position.y = -10; // Slightly below
        scene.add(plane);

        // Lighting
        const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.6);
        hemiLight.position.set(0, 200, 0);
        scene.add(hemiLight);

        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(50, 100, 50);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 2048;
        dirLight.shadow.mapSize.height = 2048;
        scene.add(dirLight);

        // Grid
        const grid = new THREE.GridHelper(500, 50, 0xcccccc, 0xe5e5e5);
        // grid.rotation.x = Math.PI/2; // Z-up? ThreeJS is Y-up default.
        // Usually Engineering CAD (FreeCAD) is Z-up. 
        // If we want Z-up view, we rotate the objects or camera.
        // Let's keep Y-up for ThreeJS standard but rotate meshes if needed.
        scene.add(grid);

        const fullBox = new THREE.Box3();
        let hasData = false;

        function addSolid(id, color, name) {{
            try {{
                const el = document.getElementById(id);
                if (!el) return;
                const json = JSON.parse(el.textContent);
                if (json.v.length === 0) return;

                const geo = new THREE.BufferGeometry();
                geo.setAttribute('position', new THREE.Float32BufferAttribute(json.v, 3));
                if (json.i.length > 0) {{
                    geo.setIndex(json.i);
                    geo.computeVertexNormals(); // Crucial for Solid shading
                }}

                // Solid Material
                const mat = new THREE.MeshStandardMaterial({{ 
                    color: color, 
                    metalness: 0.3, 
                    roughness: 0.6,
                    side: THREE.DoubleSide // Handle bad normals
                }});

                const mesh = new THREE.Mesh(geo, mat);
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                
                // Rotation Fix? FreeCAD (Z-up) -> ThreeJS (Y-up)
                // Try rotating X -90
                mesh.rotation.x = -Math.PI / 2;

                scene.add(mesh);

                // Add Edges
                const edges = new THREE.EdgesGeometry(geo, 15); // Threshold angle
                const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({{ color: 0x000000, opacity: 0.2, transparent: true }}));
                line.rotation.x = -Math.PI / 2;
                scene.add(line);

                // Box calc (apply rotation manually or just check vertices)
                // Since we rotated the mesh, box needs update.
                // Recompute box after world matrix update
                mesh.updateMatrixWorld();
                fullBox.expandByObject(mesh);
                hasData = true;
            }} catch(e) {{ console.error(e); }}
        }}

        // Colors
        addSolid("d-frame", 0xb0bec5, "Frame"); // Steel Grey
        addSolid("d-punch", 0x3498db, "Punch"); // Blue
        addSolid("d-strip", 0xf1c40f, "Strip"); // Yellow Gold
        
        // Add extras
        {''.join([f'addSolid("d-{k}", 0x95a5a6, "{k}");' for k in extra_models.keys()])}

        document.getElementById('loading').style.display = 'none';

        // Auto Center
        const target = new THREE.Vector3();
        if(hasData) {{
            fullBox.getCenter(target);
            const size = new THREE.Vector3();
            fullBox.getSize(size);
            const maxDim = Math.max(size.x, size.y, size.z);
            
            // Isometric view
            camera.position.set(
                target.x + maxDim * 1.0,
                target.y + maxDim * 1.0, 
                target.z + maxDim * 1.0
            );
            camera.lookAt(target);
            
            // Adjust grid to be at the bottom of the object
            grid.position.y = fullBox.min.y;
            plane.position.y = fullBox.min.y - 0.1;
            
        }} else {{
            camera.position.set(50,50,50);
            camera.lookAt(0,0,0);
        }}

        // Controls
        let isDragging = false;
        let prevX = 0, prevY = 0;
        const dom = container;
        
        dom.addEventListener('mousedown', e => {{ isDragging = true; prevX = e.clientX; prevY = e.clientY; }});
        window.addEventListener('mouseup', () => isDragging = false);
        dom.addEventListener('mousemove', e => {{
            if(isDragging) {{
                const dx = e.clientX - prevX;
                const dy = e.clientY - prevY;
                prevX = e.clientX; prevY = e.clientY;

                // Orbit
                const offset = camera.position.clone().sub(target);
                let r = offset.length();
                let theta = Math.atan2(offset.x, offset.z);
                let phi = Math.acos(offset.y / r);

                theta -= dx * 0.005;
                phi -= dy * 0.005;
                phi = Math.max(0.01, Math.min(Math.PI - 0.01, phi));

                camera.position.x = target.x + r * Math.sin(phi) * Math.sin(theta);
                camera.position.y = target.y + r * Math.cos(phi);
                camera.position.z = target.z + r * Math.sin(phi) * Math.cos(theta);
                camera.lookAt(target);
            }}
        }});
        
        dom.addEventListener('wheel', e => {{
            e.preventDefault();
            const dir = new THREE.Vector3();
            camera.getWorldDirection(dir);
            camera.position.addScaledVector(dir, -e.deltaY * 0.05);
        }});
        
        window.addEventListener('resize', () => {{
            camera.aspect = dom.clientWidth / dom.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(dom.clientWidth, dom.clientHeight);
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

print(f"Final Report v10 (Solid + Extras) Generated: {REPORT_PATH}")
