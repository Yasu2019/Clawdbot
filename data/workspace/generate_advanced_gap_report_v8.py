
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
REPORT_PATH = os.path.join(WORKSPACE_DIR, "gap_analysis_report.html") # Overwrite main file
THREE_JS_PATH = os.path.join(REPORT_DIR, "three.min.js")

# Font Fallback
plt.rcParams['font.family'] = 'DejaVu Sans'

# --- 1. Simulation Logic (Production) ---
def run_simulation(nominal_gap, tolerances, n_samples=100000):
    total_var = np.zeros(n_samples)
    for name, tol in tolerances.items():
        sigma = tol / 3.0
        var = np.random.normal(0, sigma, n_samples)
        total_var += var
    return nominal_gap + total_var

tols_x = { "Strip": 0.15, "Punch": 0.05, "Frame": 0.02, "Feed": 0.0115 }
tols_y = { "Strip": 0.15, "Punch": 0.05, "Frame": 0.02 }

sim_x = run_simulation(1.500, tols_x)
sim_y = run_simulation(0.575, tols_y)

def get_stats(data, lsl=0.0):
    mean = np.mean(data)
    std = np.std(data)
    cpk = (mean - lsl) / (3 * std)
    return mean, std, cpk

stats_x = get_stats(sim_x)
stats_y = get_stats(sim_y)

# Graph Generation
def create_hist(data, filename, title, stats):
    plt.figure(figsize=(6, 4))
    plt.hist(data, bins=50, color='#3498db', alpha=0.7, density=True)
    plt.axvline(0, color='r', linestyle='--', label='Interference')
    plt.title(f"{title}\nCpk={stats[2]:.2f}")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, filename))
    plt.close()

create_hist(sim_x, "hist_x_v8.png", "X-Axis Gap", stats_x)
create_hist(sim_y, "hist_y_v8.png", "Y-Axis Gap", stats_y)

def get_b64(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_x = get_b64("hist_x_v8.png")
img_y = get_b64("hist_y_v8.png")

# --- 2. 3D Model Processing (High Res) ---
def obj_to_list(filename, stride=1):
    path = os.path.join(MODEL_DIR, filename)
    vertices = []
    print(f"Loading {filename}...")
    if os.path.exists(path):
        with open(path, "r") as f:
            count = 0
            for line in f:
                if line.startswith("v "):
                    count += 1
                    if count % stride == 0:
                        parts = line.strip().split()
                        try:
                            # Parse safely, replacing NaN with 0
                            val = [float(p) for p in parts[1:4]]
                            if not any(math.isnan(v) for v in val):
                                vertices.extend(val)
                        except (IndexError, ValueError): pass
    print(f"  -> Loaded {len(vertices)//3} points (Stride={stride})")
    return vertices

# Stride reduced for higher quality
v_frame = obj_to_list("frame.obj", stride=2)  # High detail
v_punch = obj_to_list("punch.obj", stride=1)  # Max detail (it's small)
v_strip = obj_to_list("product_1.obj", stride=2) 

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
    <title>Gap Analysis Report (Final)</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f4f9; margin: 0; padding: 20px; color: #333; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; color: #2c3e50; }}
        .header p {{ color: #7f8c8d; }}
        
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 8px; }}
        
        .viewer-box {{ width: 100%; height: 600px; background: #1a1a1a; position: relative; overflow: hidden; border-radius: 4px; }}
        #loading {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; font-size: 1.2em; text-align: center; pointer-events: none; }}
        
        .stats-grid {{ display: flex; gap: 20px; margin-top: 30px; }}
        .stat-card {{ flex: 1; padding: 20px; border: 1px solid #eee; text-align: center; background: #fff; border-radius: 8px; transition: transform 0.2s; }}
        .stat-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .stat-card h3 {{ margin-top: 0; color: #2c3e50; }}
        img {{ max-width: 100%; height: auto; border: 1px solid #eee; }}
        
        .controls-hint {{ text-align: center; color: #666; font-size: 0.9em; margin-top: 10px; padding: 10px; background: #eee; border-radius: 4px; }}
        .legend {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 15px; font-weight: bold; font-size: 0.9em; }}
        .legend span {{ display: inline-flex; align-items: center; gap: 5px; }}
        .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
    </style>
    <!-- EMBEDDED THREE.JS -->
    <script>
    {three_js_content}
    </script>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>Tolerance Gap Analysis Report</h1>
        <p>3D Visualization & Monte Carlo Simulation (N=100,000)</p>
    </div>

    <div class="legend">
        <span><i class="dot" style="background:#aaaaaa;"></i> Frame</span>
        <span><i class="dot" style="background:#3498db;"></i> Punch</span>
        <span><i class="dot" style="background:#f1c40f;"></i> Strip</span>
    </div>
    
    <div class="viewer-box" id="viewer3d">
        <div id="loading">Initializing 3D Engine...</div>
    </div>
    <div class="controls-hint">
        <strong>Controls:</strong> Left Mouse: Rotate | Right Mouse: Pan | Scroll: Zoom
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <h3>X-Axis Clearance</h3>
            <p>Target: 1.500 mm</p>
            <img src="{img_x}">
            <p><strong>Cpk: {stats_x[2]:.2f}</strong></p>
        </div>
        <div class="stat-card">
            <h3>Y-Axis Clearance</h3>
            <p>Target: 0.575 mm</p>
            <img src="{img_y}">
            <p><strong>Cpk: {stats_y[2]:.2f}</strong></p>
        </div>
    </div>
</div>

<!-- EMBEDDED DATA -->
<script type="application/json" id="d-frame">{json.dumps(v_frame)}</script>
<script type="application/json" id="d-punch">{json.dumps(v_punch)}</script>
<script type="application/json" id="d-strip">{json.dumps(v_strip)}</script>

<script>
    function main() {{
        // Safety Check
        if (typeof THREE === 'undefined') {{
            document.getElementById('loading').innerText = "Critical Error: 3D Library failed to load.";
            return;
        }}

        const container = document.getElementById('viewer3d');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x1a1a1a);

        // Camera
        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 10000);
        
        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(renderer.domElement);

        // Helpers
        scene.add(new THREE.AxesHelper(20));
        const grid = new THREE.GridHelper(300, 60, 0x444444, 0x222222);
        grid.rotation.x = Math.PI/2;
        scene.add(grid);

        // Data Loader
        const fullBox = new THREE.Box3();
        let hasData = false;

        function addPoints(id, color, size) {{
            try {{
                const txt = document.getElementById(id).textContent;
                const data = JSON.parse(txt);
                if (data.length === 0) return;

                const geo = new THREE.BufferGeometry();
                geo.setAttribute('position', new THREE.Float32BufferAttribute(data, 3));
                const mat = new THREE.PointsMaterial({{ color: color, size: size, sizeAttenuation: true }});
                const mesh = new THREE.Points(geo, mat);
                scene.add(mesh);

                geo.computeBoundingBox();
                fullBox.expandByObject(mesh);
                hasData = true;
            }} catch(e) {{ console.error(e); }}
        }}

        addPoints("d-frame", 0xaaaaaa, 0.5); // Frame
        addPoints("d-punch", 0x3498db, 1.5); // Punch (Larger dots)
        addPoints("d-strip", 0xf1c40f, 0.8); // Strip

        document.getElementById('loading').style.display = 'none';

        // Auto Center
        const target = new THREE.Vector3();
        if(hasData) {{
            fullBox.getCenter(target);
            const size = new THREE.Vector3();
            fullBox.getSize(size);
            const maxDim = Math.max(size.x, size.y, size.z);
            
            // Standard Isometric-ish view from distance
            camera.position.x = target.x + maxDim;
            camera.position.y = target.y + maxDim * 0.5;
            camera.position.z = target.z + maxDim * 2.5;
            camera.lookAt(target);
        }} else {{
            camera.position.set(50,50,50);
            camera.lookAt(0,0,0);
        }}

        // Controls Logic (Orbit-like)
        let isDragging = false;
        let prevX = 0, prevY = 0;
        
        container.addEventListener('mousedown', e => {{ isDragging = true; prevX = e.clientX; prevY = e.clientY; }});
        window.addEventListener('mouseup', () => isDragging = false);
        container.addEventListener('mousemove', e => {{
            if(isDragging) {{
                const deltaX = e.clientX - prevX;
                const deltaY = e.clientY - prevY;
                prevX = e.clientX; prevY = e.clientY;

                // Spherical rotation around target
                const offset = camera.position.clone().sub(target);
                let r = offset.length();
                let theta = Math.atan2(offset.x, offset.z); // horizontal
                let phi = Math.acos(offset.y / r); // vertical

                theta -= deltaX * 0.005;
                phi -= deltaY * 0.005;
                phi = Math.max(0.01, Math.min(Math.PI - 0.01, phi)); // prevent flip

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

print(f"Final Report v8 Generated: {REPORT_PATH}")
