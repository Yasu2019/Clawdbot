
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

# Font for Graphs
plt.rcParams['font.family'] = 'DejaVu Sans'

# --- 1. Simulation Logic (Same as v2) ---
def run_simulation(nominal_gap, tolerances, n_samples=100000):
    total_var = np.zeros(n_samples)
    for name, tol in tolerances.items():
        sigma = tol / 3.0
        var = np.random.normal(0, sigma, n_samples)
        total_var += var
    # Gap = Nominal + Sum(Variations)
    return nominal_gap + total_var

tols_x = { "Strip": 0.15, "Punch": 0.05, "Frame": 0.02, "Feed": 0.0115 }
tols_y = { "Strip": 0.15, "Punch": 0.05, "Frame": 0.02 }

sim_x = run_simulation(1.500, tols_x)
sim_y = run_simulation(0.575, tols_y)

def get_stats(data, lsl=0.0):
    mean = np.mean(data)
    std = np.std(data)
    cpk = (mean - lsl) / (3 * std)
    fail = (np.sum(data < lsl) / len(data)) * 100
    return mean, std, cpk, fail

stats_x = get_stats(sim_x)
stats_y = get_stats(sim_y)

# Graph Generation
def create_hist(data, filename, title, stats):
    plt.figure(figsize=(6, 4))
    plt.hist(data, bins=50, color='#3498db', alpha=0.7, density=True)
    plt.axvline(0, color='r', linestyle='--', label='Interference')
    plt.title(f"{title}\nCpk={stats[2]:.2f}")
    plt.xlabel("Gap [mm]")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, filename))
    plt.close()

create_hist(sim_x, "hist_x_v3.png", "X-Axis Gap", stats_x)
create_hist(sim_y, "hist_y_v3.png", "Y-Axis Gap", stats_y)

def get_b64(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_x = get_b64("hist_x_v3.png")
img_y = get_b64("hist_y_v3.png")

# --- 2. 3D Model Processing (Downsampling) ---
def obj_to_list(filename, stride=10):
    path = os.path.join(MODEL_DIR, filename)
    vertices = []
    if os.path.exists(path):
        with open(path, "r") as f:
            count = 0
            for line in f:
                if line.startswith("v "):
                    count += 1
                    if count % stride == 0:
                        parts = line.strip().split()
                        try:
                            vertices.extend([float(parts[1]), float(parts[2]), float(parts[3])])
                        except IndexError: pass
    return vertices

# Stride 5 to reduce size but keep detail
v_frame = obj_to_list("frame.obj", stride=5)
v_punch = obj_to_list("punch.obj", stride=5)
v_strip = obj_to_list("product_1.obj", stride=2)

# --- 3. HTML Generation ---
html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gap Analysis Report v3</title>
    <style>
        body {{ font-family: sans-serif; margin: 0; padding: 20px; background: #f0f0f0; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1, h2, h3 {{ color: #333; }}
        .header {{ text-align: center; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .viewer-box {{ width: 100%; height: 500px; background: #000; position: relative; }}
        .stats-grid {{ display: flex; flex-wrap: wrap; gap: 20px; margin-top: 20px; }}
        .stat-card {{ flex: 1; min-width: 300px; border: 1px solid #ccc; padding: 15px; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #eee; padding: 8px; text-align: center; }}
        .safe {{ color: #27ae60; font-weight: bold; }}
        #loading {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>Tolerance Gap Analysis Report (v3)</h1>
        <p>Interactive 3D Visualization & Multi-Axis Simulation</p>
    </div>

    <div class="viewer-box" id="viewer3d">
        <div id="loading">Loading 3D Model...</div>
    </div>
    <p style="text-align:center; font-size:0.9em; color:#666;">Controls: Left Drag to Rotate | Right Drag to Pan | Scroll to Zoom</p>

    <div class="stats-grid">
        <div class="stat-card">
            <h3>X-Axis Analysis</h3>
            <p><strong>Design Gap: 1.500 mm</strong></p>
            <img src="{img_x}" width="100%">
            <table>
                <tr><td>Mean Gap</td><td>{stats_x[0]:.4f} mm</td></tr>
                <tr><td>StdDev (σ)</td><td>{stats_x[1]:.4f} mm</td></tr>
                <tr><td>Cpk</td><td class="safe">{stats_x[2]:.2f}</td></tr>
            </table>
        </div>
        <div class="stat-card">
            <h3>Y-Axis Analysis</h3>
            <p><strong>Design Gap: 0.575 mm</strong></p>
            <img src="{img_y}" width="100%">
            <table>
                <tr><td>Mean Gap</td><td>{stats_y[0]:.4f} mm</td></tr>
                <tr><td>StdDev (σ)</td><td>{stats_y[1]:.4f} mm</td></tr>
                <tr><td>Cpk</td><td class="safe">{stats_y[2]:.2f}</td></tr>
            </table>
        </div>
    </div>
</div>

<!-- DATA EMBEDDING START -->
<script type="application/json" id="data-frame">{json.dumps(v_frame)}</script>
<script type="application/json" id="data-punch">{json.dumps(v_punch)}</script>
<script type="application/json" id="data-strip">{json.dumps(v_strip)}</script>
<!-- DATA EMBEDDING END -->

<script>
    // Safe Data Loading
    function loadData(id) {{
        try {{
            return JSON.parse(document.getElementById(id).textContent);
        }} catch(e) {{
            console.error("Failed to load vertex data for " + id, e);
            return [];
        }}
    }}

    const vFrame = loadData("data-frame");
    const vPunch = loadData("data-punch");
    const vStrip = loadData("data-strip");

    // Three.js Scene
    const container = document.getElementById('viewer3d');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x222222);

    // Camera
    const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(24, 20, 100); 

    // Renderer
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    // Helpers
    const axesHelper = new THREE.AxesHelper(10);
    scene.add(axesHelper);
    const gridHelper = new THREE.GridHelper(100, 100, 0x444444, 0x333333);
    gridHelper.rotation.x = Math.PI / 2; # Rotate to match Z-up logic often used in CAD
    scene.add(gridHelper);

    // Geometry Builder
    function createPointCloud(vertices, color) {{
        if (!vertices || vertices.length === 0) return null;
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
        const material = new THREE.PointsMaterial({{ color: color, size: 0.1, sizeAttenuation: true }});
        return new THREE.Points(geometry, material);
    }}

    const pFrame = createPointCloud(vFrame, 0x999999);
    const pPunch = createPointCloud(vPunch, 0x3498db);
    const pStrip = createPointCloud(vStrip, 0xf1c40f);

    if (pFrame) scene.add(pFrame);
    if (pPunch) scene.add(pPunch);
    if (pStrip) scene.add(pStrip);

    document.getElementById('loading').style.display = 'none';

    // Controls
    let isDragging = false;
    let isPanning = false;
    let prevPos = {{ x: 0, y: 0 }};
    const target = new THREE.Vector3(24, 20, 0); # Approximate Center

    container.addEventListener('mousedown', e => {{
        prevPos = {{ x: e.offsetX, y: e.offsetY }};
        if (e.button === 0) isDragging = true;
        if (e.button === 2) isPanning = true;
    }});

    window.addEventListener('mouseup', () => {{
        isDragging = false;
        isPanning = false;
    }});

    container.addEventListener('contextmenu', e => e.preventDefault());

    container.addEventListener('mousemove', e => {{
        const deltaX = e.offsetX - prevPos.x;
        const deltaY = e.offsetY - prevPos.y;
        prevPos = {{ x: e.offsetX, y: e.offsetY }};

        if (isDragging) {{
            # Orbit Logic
            const offset = camera.position.clone().sub(target);
            const r = offset.length();
            
            # Simple spherical rotation
            let theta = Math.atan2(offset.x, offset.z);
            let phi = Math.acos(offset.y / r);

            theta -= deltaX * 0.01;
            phi -= deltaY * 0.01;
            phi = Math.max(0.1, Math.min(Math.PI - 0.1, phi)); # Clamp pitch

            camera.position.x = target.x + r * Math.sin(phi) * Math.sin(theta);
            camera.position.y = target.y + r * Math.cos(phi);
            camera.position.z = target.z + r * Math.sin(phi) * Math.cos(theta);
            camera.lookAt(target);
        }}
        
        if (isPanning) {{
            # Pan Logic
            # TODO: Improve Pan
        }}
    }});

    container.addEventListener('wheel', e => {{
        e.preventDefault();
        const lookDir = new THREE.Vector3();
        camera.getWorldDirection(lookDir);
        camera.position.addScaledVector(lookDir, -e.deltaY * 0.05);
    }});

    function animate() {{
        requestAnimationFrame(animate);
        renderer.render(scene, camera);
    }}
    animate();

    # Resize
    window.addEventListener('resize', () => {{
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }});

</script>
</body>
</html>
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Report Generated: {REPORT_PATH}")
