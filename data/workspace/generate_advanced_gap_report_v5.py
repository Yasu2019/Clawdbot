
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
# Ensure directory exists
if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)

MODEL_DIR = os.path.join(WORKSPACE_DIR, "report_assets", "3d_models")
REPORT_PATH = os.path.join(WORKSPACE_DIR, "gap_analysis_report.html")

# Font Fallback
plt.rcParams['font.family'] = 'DejaVu Sans'

# --- 1. Simulation Logic (Same as v3) ---
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

create_hist(sim_x, "hist_x_v5.png", "X-Axis Gap", stats_x)
create_hist(sim_y, "hist_y_v5.png", "Y-Axis Gap", stats_y)

def get_b64(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_x = get_b64("hist_x_v5.png")
img_y = get_b64("hist_y_v5.png")

# --- 2. 3D Model Processing (Debugged) ---
def obj_to_list(filename, stride=10):
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
                            x = float(parts[1])
                            y = float(parts[2])
                            z = float(parts[3])
                            if math.isnan(x) or math.isnan(y) or math.isnan(z): continue
                            vertices.extend([x, y, z])
                        except (IndexError, ValueError): pass
    print(f"  -> Loaded {len(vertices)//3} points (Stride={stride})")
    return vertices

# Stride 10 for safety/speed
v_frame = obj_to_list("frame.obj", stride=10)
v_punch = obj_to_list("punch.obj", stride=10)
v_strip = obj_to_list("product_1.obj", stride=5)

# --- 3. HTML Generation ---
html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gap Analysis Report v5 (Offline Mode)</title>
    <style>
        body {{ font-family: sans-serif; background: #f0f0f0; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        .viewer-box {{ width: 100%; height: 500px; background: #111; position: relative; overflow: hidden; }}
        #loading {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; font-size: 1.2em; text-align: center; }}
        #error-log {{ position: absolute; bottom: 0; left: 0; width: 100%; background: rgba(200,0,0,0.9); color: white; padding: 10px; font-size: 0.9em; display: none; z-index: 1000; }}
        .stats-grid {{ display: flex; gap: 20px; margin-top: 20px; }}
        .stat-card {{ flex: 1; padding: 10px; border: 1px solid #ddd; text-align: center; }}
        img {{ max-width: 100%; height: auto; }}
        .controls-hint {{ text-align: center; color: #666; font-size: 0.8em; margin-top: 5px; }}
    </style>
    <!-- Try local first, then CDN -->
    <script src="report_assets/three.min.js"></script>
</head>
<body>

<div class="container">
    <h1>Tolerance Gap Analysis Report (v5)</h1>
    <p>Offline Mode Enabled. Data reduction applied for performance.</p>
    
    <div class="viewer-box" id="viewer3d">
        <div id="loading">Initializing...<br><span style="font-size:0.8em; color:#aaa;">(If stuck, check connection or console)</span></div>
        <div id="error-log"></div>
    </div>
    <div class="controls-hint">Left Mouse: Rotate | Right Mouse: Pan | Scroll: Zoom</div>
    
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
<script type="application/json" id="d-frame">{json.dumps(v_frame)}</script>
<script type="application/json" id="d-punch">{json.dumps(v_punch)}</script>
<script type="application/json" id="d-strip">{json.dumps(v_strip)}</script>

<script>
    // Critical Error Handler
    window.onerror = function(msg, url, line) {{
        const el = document.getElementById('error-log');
        el.style.display = 'block';
        el.innerHTML += `<strong>CRITICAL ERROR:</strong> ${{msg}}<br>File: ${{url}}<br>Line: ${{line}}<hr>`;
        document.getElementById('loading').style.display = 'none';
        return false;
    }};

    function main() {{
        // Check Library
        if (typeof THREE === 'undefined') {{
            throw new Error("Three.js library failed to load! Please ensure 'report_assets/three.min.js' exists relative to this HTML file.");
        }}

        function loadData(id) {{
            try {{
                const txt = document.getElementById(id).textContent;
                if(!txt || txt === '[]') console.warn("Empty data for " + id);
                return JSON.parse(txt);
            }} catch(e) {{
                throw new Error("JSON Parse failed for " + id + ": " + e.message);
            }}
        }}

        const vFrame = loadData("d-frame");
        const vPunch = loadData("d-punch");
        const vStrip = loadData("d-strip");
        
        document.getElementById('loading').innerHTML = `Data Parsed.<br>Frame: ${{vFrame.length/3}} pts<br>Building Scene...`;

        const container = document.getElementById('viewer3d');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x111111);

        const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 1000);
        camera.position.set(24, 30, 60); # Elevated view

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(container.clientWidth, container.clientHeight);
        container.appendChild(renderer.domElement);

        // Grid & Helpers
        scene.add(new THREE.AxesHelper(15));
        const grid = new THREE.GridHelper(200, 50, 0x444444, 0x222222);
        grid.rotation.x = Math.PI/2; 
        scene.add(grid);

        // Point Cloud Builder
        function addPoints(vertices, color, size) {{
            if (!vertices || vertices.length === 0) return;
            const geo = new THREE.BufferGeometry();
            geo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
            const mat = new THREE.PointsMaterial({{ color: color, size: size, sizeAttenuation: true }});
            const mesh = new THREE.Points(geo, mat);
            scene.add(mesh);
        }}

        addPoints(vFrame, 0xaaaaaa, 0.3); # Frame (Grey)
        addPoints(vPunch, 0x3498db, 0.5); # Punch (Blue, Thick)
        addPoints(vStrip, 0xf1c40f, 0.4); # Strip (Yellow)
        
        document.getElementById('loading').style.display = 'none';

        // Camera Target (Center of work)
        const target = new THREE.Vector3(24, 20, 0); 
        camera.lookAt(target);

        // Render Loop
        function animate() {{
            requestAnimationFrame(animate);
            renderer.render(scene, camera);
        }}
        animate();
        
        // Mouse Controls
        let isDrag = false;
        let prevX = 0, prevY = 0;
        container.addEventListener('mousedown', e => {{ isDrag = true; prevX = e.clientX; prevY = e.clientY; }});
        window.addEventListener('mouseup', () => isDrag = false);
        container.addEventListener('mousemove', e => {{
            if(isDrag) {{
                const dx = e.clientX - prevX;
                const dy = e.clientY - prevY;
                prevX = e.clientX; prevY = e.clientY;
                
                const offset = camera.position.clone().sub(target);
                const r = offset.length();
                let theta = Math.atan2(offset.x, offset.z);
                let phi = Math.acos(offset.y / r);
                
                theta -= dx * 0.01;
                phi -= dy * 0.01;
                // Clamp phi to avoid flipping
                phi = Math.max(0.1, Math.min(Math.PI-0.1, phi));
                
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
            camera.position.addScaledVector(dir, -e.deltaY * 0.1);
        }});
        
        // Resize Handler
        window.addEventListener('resize', () => {{
            camera.aspect = container.clientWidth / container.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(container.clientWidth, container.clientHeight);
        }});
    }}

    // Delay start slightly to ensure DOM
    setTimeout(main, 100);

</script>
</body>
</html>
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Report Generated: {REPORT_PATH}")
