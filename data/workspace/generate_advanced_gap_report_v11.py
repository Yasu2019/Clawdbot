
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

create_hist(sim_x, "hist_x_v11.png", "X-Axis Gap", stats_x)
create_hist(sim_y, "hist_y_v11.png", "Y-Axis Gap", stats_y)

def get_b64(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_x = get_b64("hist_x_v11.png")
img_y = get_b64("hist_y_v11.png")

# --- 2. 3D Model Parsing (Robust) ---
def parse_obj(filename):
    path = os.path.join(MODEL_DIR, filename)
    vertices = []
    indices = []
    print(f"Loading {filename}...")
    
    if not os.path.exists(path):
        print(f"  [WARN] File not found: {path}")
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
                poly_verts = []
                for p in parts[1:]:
                    val = p.split('/')[0]
                    if val:
                        poly_verts.append(int(val) - 1)
                for i in range(1, len(poly_verts) - 1):
                    indices.extend([poly_verts[0], poly_verts[i], poly_verts[i+1]])

    print(f"  -> Vertices: {len(vertices)//3}, Indices: {len(indices)}")
    return {"v": vertices, "i": indices}

# Load known new files
data_guide = parse_obj("Guide_Base.obj")
data_frame = parse_obj("Frame_1.obj") 
data_strip = parse_obj("Strip.obj")

# Find Terminals
terminals = {}
for file in os.listdir(MODEL_DIR):
    if file.startswith("Terminal") and file.endswith(".obj"):
        name = os.path.splitext(file)[0]
        terminals[name] = parse_obj(file)

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
    <title>Gap Analysis Report (Assembly)</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #eaeded; margin: 0; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 8px; }}
        .viewer-box {{ width: 100%; height: 750px; background: #e0e0e0; position: relative; overflow: hidden; border-radius: 4px; border: 1px solid #ccc; }}
        #loading {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #333; font-weight: bold; background: rgba(255,255,255,0.8); padding: 10px 20px; border-radius: 5px; }}
        
        .stats-grid {{ display: flex; gap: 20px; margin-top: 30px; }}
        .stat-card {{ flex: 1; padding: 20px; border: 1px solid #eee; text-align: center; background: #fff; border-radius: 8px; }}
        img {{ max-width: 100%; height: auto; border: 1px solid #eee; }}
        
        .legend {{ display: flex; justify-content: center; include-wrap: wrap; gap: 15px; margin-bottom: 10px; font-weight: bold; font-size: 0.9em; }}
        .dot {{ width: 15px; height: 15px; display: inline-block; margin-right: 5px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.2); }}
    </style>
    <script>{three_js_content}</script>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>Tolerance Final Report (v11)</h1>
        <p>Full Assembly Solid View • Auto-Centered</p>
    </div>

    <div class="legend">
        <span><i class="dot" style="background:#546e7a;"></i> Guide Base</span>
        <span><i class="dot" style="background:#bdc3c7;"></i> Frame (Punch Block)</span>
        <span><i class="dot" style="background:#f1c40f;"></i> Strip</span>
        <span><i class="dot" style="background:#d35400;"></i> Terminals</span>
    </div>
    
    <div class="viewer-box" id="viewer3d">
        <div id="loading">Initializing Full Assembly...</div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <h3>X-Axis (Gap 1.5mm)</h3>
            <img src="{img_x}">
        </div>
        <div class="stat-card">
            <h3>Y-Axis (Gap 0.575mm)</h3>
            <img src="{img_y}">
        </div>
    </div>
</div>

<!-- DATA -->
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
        // Fog to give depth
        scene.fog = new THREE.Fog(0xf5f5f5, 100, 500);

        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 10000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        
        // Tone Mapping for realism
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.0;
        
        container.appendChild(renderer.domElement);

        // Ground Plane
        const planeGeo = new THREE.PlaneGeometry(1000, 1000);
        const planeMat = new THREE.ShadowMaterial({{ opacity: 0.15 }});
        const plane = new THREE.Mesh(planeGeo, planeMat);
        plane.rotation.x = -Math.PI / 2;
        plane.position.y = -50; 
        plane.receiveShadow = true;
        scene.add(plane);

        // Lighting (Studio Setup)
        const hemiLight = new THREE.HemisphereLight(0xffffff, 0x555555, 0.7);
        hemiLight.position.set(0, 500, 0);
        scene.add(hemiLight);

        const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
        dirLight.position.set(100, 200, 100);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 4096;
        dirLight.shadow.mapSize.height = 4096;
        dirLight.shadow.camera.near = 0.5;
        dirLight.shadow.camera.far = 1000;
        dirLight.shadow.camera.left = -200;
        dirLight.shadow.camera.right = 200;
        dirLight.shadow.camera.top = 200;
        dirLight.shadow.camera.bottom = -200;
        scene.add(dirLight);

        // Grid
        const grid = new THREE.GridHelper(500, 50, 0xbbbbbb, 0xeeeeee);
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
                    geo.computeVertexNormals();
                }}

                const mat = new THREE.MeshStandardMaterial({{ 
                    color: color, 
                    metalness: 0.4, 
                    roughness: 0.4,
                    side: THREE.DoubleSide
                }});

                const mesh = new THREE.Mesh(geo, mat);
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                mesh.rotation.x = -Math.PI / 2; // Fix Z-up -> Y-up

                scene.add(mesh);

                const edges = new THREE.EdgesGeometry(geo, 20); // Sharp edges
                const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({{ color: 0x333333, opacity: 0.15, transparent: true }}));
                line.rotation.x = -Math.PI / 2;
                scene.add(line);

                mesh.updateMatrixWorld();
                fullBox.expandByObject(mesh);
                hasData = true;
            }} catch(e) {{ console.error(e); }}
        }}

        // Add Parts
        addSolid("d-guide", 0x546e7a, "Guide"); // Blue-Grey
        addSolid("d-frame", 0xbdc3c7, "Frame"); // Bright Silver
        addSolid("d-strip", 0xf1c40f, "Strip"); // Gold
        
        // Terminals
        const termIds = {json.dumps(list(terminals.keys()))};
        termIds.forEach(k => {{
            addSolid("d-" + k, 0xd35400, "Terminal"); // Copper
        }});

        document.getElementById('loading').style.display = 'none';

        // Auto Center
        const target = new THREE.Vector3();
        if(hasData) {{
            fullBox.getCenter(target);
            const size = new THREE.Vector3();
            fullBox.getSize(size);
            const maxDim = Math.max(size.x, size.y, size.z);
            
            camera.position.set(target.x + maxDim, target.y + maxDim, target.z + maxDim * 2.5);
            camera.lookAt(target);
            
            // Adjust ground
            grid.position.y = fullBox.min.y;
            plane.position.y = fullBox.min.y - 0.2;
            
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

print(f"Final Report v11 (Assembly) Generated: {REPORT_PATH}")
