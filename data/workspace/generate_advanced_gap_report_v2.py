
import numpy as np
import matplotlib.pyplot as plt
import os
import base64
import json
import re

# --- Configuration ---
if os.path.exists("/home/node/clawd"):
    WORKSPACE_DIR = "/home/node/clawd"
else:
    WORKSPACE_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace"

REPORT_DIR = os.path.join(WORKSPACE_DIR, "report_assets")
MODEL_DIR = os.path.join(WORKSPACE_DIR, "report_assets", "3d_models")
REPORT_PATH = os.path.join(WORKSPACE_DIR, "gap_analysis_report.html")

# Set Japanese Font
plt.rcParams['font.family'] = 'DejaVu Sans' # Fallback for Docker

# --- 1. Simulation Logic ---
def run_simulation(nominal_gap, tolerances, n_samples=100000):
    total_var = np.zeros(n_samples)
    print(f"Simulating Gap {nominal_gap}mm with tolerances: {tolerances}")
    
    for name, tol in tolerances.items():
        # Assume 3sigma = tol (Normal Distribution)
        sigma = tol / 3.0
        var = np.random.normal(0, sigma, n_samples)
        total_var += var
        
    sim_gap = nominal_gap - np.abs(total_var) # Worst case logic: Variation REDUCES gap
    # Note: In Monte Carlo, usually we sum signed variations. 
    # But for "interference check", we care about the gap getting SMALLER.
    # Deviation from nominal can be +/-. 
    # Gap = Nominal + (Pos_Dev_Frame - Pos_Dev_Punch). 
    # Let's assume standard RSS accumulation for random variation.
    
    # Correct RSS Logic:
    # Gap_final = Gap_nom + sum(N(0, sigma))
    
    sim_gap = nominal_gap + total_var 
    
    return sim_gap

# Tolerances (User Input + Estimates)
# Strip: +/- 0.15
# Punch: +/- 0.05
# Frame: +/- 0.02
# Feed (X only): +/- 0.011 (3sigma)

tols_x = {
    "Strip (Width)": 0.15,
    "Punch": 0.05,
    "Frame": 0.02,
    "Feed (Mach)": 0.0115 
}

tols_y = {
    "Strip (Width)": 0.15, # Affects Y if width direction
    "Punch": 0.05,
    "Frame": 0.02
    # No feed error in Y
}

sim_x = run_simulation(1.500, tols_x)
sim_y = run_simulation(0.575, tols_y)

# Stats Helper
def get_stats(data, lsl=0.0):
    mean = np.mean(data)
    std = np.std(data)
    cpk = (mean - lsl) / (3 * std)
    fail = (np.sum(data < lsl) / len(data)) * 100
    return mean, std, cpk, fail

stats_x = get_stats(sim_x)
stats_y = get_stats(sim_y)

# --- 2. Graphs ---
def create_hist(data, filename, title, stats):
    plt.figure(figsize=(6, 4))
    plt.hist(data, bins=50, color='#3498db', alpha=0.7, density=True)
    plt.axvline(0, color='r', linestyle='--', label='Interference (0mm)')
    plt.title(f"{title}\nCpk={stats[2]:.2f}")
    plt.xlabel("Gap [mm]")
    plt.tight_layout()
    path = os.path.join(REPORT_DIR, filename)
    plt.savefig(path)
    plt.close()

create_hist(sim_x, "hist_x.png", "X-Axis Gap Distribution", stats_x)
create_hist(sim_y, "hist_y.png", "Y-Axis Gap Distribution", stats_y)

def get_b64(filename):
    with open(os.path.join(REPORT_DIR, filename), "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_x = get_b64("hist_x.png")
img_y = get_b64("hist_y.png")

# --- 3. 3D Model Processing (OBJ -> JSON Vertices) ---
def obj_to_json(filename):
    path = os.path.join(MODEL_DIR, filename)
    vertices = []
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                if line.startswith("v "):
                    parts = line.strip().split()
                    vertices.extend([float(parts[1]), float(parts[2]), float(parts[3])])
    return json.dumps(vertices)

json_frame = obj_to_json("frame.obj")
json_punch = obj_to_json("punch.obj")
json_strip = obj_to_json("product_1.obj")

# --- 4. HTML Generation ---
html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Gap Analysis Report</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; background: #eee; }}
        .header, .footer {{ background: #333; color: white; padding: 10px; text-align: center; }}
        .section {{ background: white; margin: 15px 0; padding: 20px; border-radius: 5px; }}
        .cols {{ display: flex; flex-wrap: wrap; }}
        .col {{ flex: 1; padding: 10px; min-width: 300px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background: #f2f2f2; }}
        #viewer {{ width: 100%; height: 500px; background: #222; cursor: move; }}
        .safe {{ color: green; font-weight: bold; }}
        .warning {{ color: orange; font-weight: bold; }}
    </style>
    <!-- Embedded Three.js (Partial/Minimal or CDN) -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
    <div class="header">
        <h1>Tolerance Gap Analysis Report</h1>
        <p>Punch vs Frame (Scrap)</p>
    </div>

    <div class="section">
        <h2>1. 3D Geometry Verification</h2>
        <div id="viewer"></div>
        <p style="font-size: 0.9em; text-align: center;">Left Click + Drag to Rotate | Wheel to Zoom</p>
    </div>

    <div class="section">
        <h2>2. Simulation Results (Monte Carlo N=100k)</h2>
        <div class="cols">
            <div class="col">
                <h3>X-Axis (Gap 1.5mm)</h3>
                <img src="{img_x}" width="100%">
                <table>
                    <tr><td>Mean Gap</td><td>{stats_x[0]:.4f} mm</td></tr>
                    <tr><td>StdDev (σ)</td><td>{stats_x[1]:.4f} mm</td></tr>
                    <tr><td>Cpk</td><td class="safe">{stats_x[2]:.2f}</td></tr>
                    <tr><td>Fail Rate</td><td>{stats_x[3]:.4f}%</td></tr>
                </table>
            </div>
            <div class="col">
                <h3>Y-Axis (Gap 0.575mm)</h3>
                <img src="{img_y}" width="100%">
                <table>
                    <tr><td>Mean Gap</td><td>{stats_y[0]:.4f} mm</td></tr>
                    <tr><td>StdDev (σ)</td><td>{stats_y[1]:.4f} mm</td></tr>
                    <tr><td>Cpk</td><td class="safe">{stats_y[2]:.2f}</td></tr>
                    <tr><td>Fail Rate</td><td>{stats_y[3]:.4f}%</td></tr>
                </table>
            </div>
        </div>
    </div>

<script>
    // Data Injected from Python
    const v_frame = {json_frame};
    const v_punch = {json_punch};
    const v_strip = {json_strip};

    // Scene Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x222222);
    
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 500, 0.1, 1000);
    // Auto-center camera roughly
    camera.position.set(24, 20, 100); 

    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    const div = document.getElementById('viewer');
    renderer.setSize(div.clientWidth, div.clientHeight);
    div.appendChild(renderer.domElement);

    // Helper to create Point Cloud from Vertices
    function createPoints(vertices, color, size) {{
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
        const material = new THREE.PointsMaterial({{ color: color, size: size }});
        return new THREE.Points(geometry, material);
    }}
    
    // Create Meshes (Wireframes via LineSegments using vertices)
    // Actually Points is safer for raw exported vertices if face indices are missing
    scene.add(createPoints(v_frame, 0x888888, 0.2)); // Gray
    scene.add(createPoints(v_punch, 0x3498db, 0.3)); // Blue
    scene.add(createPoints(v_strip, 0xf1c40f, 0.3)); // Yellow

    // Custom Mouse Controls (Orbit)
    let isDragging = false;
    let previousMousePosition = {{ x: 0, y: 0 }};
    const target = new THREE.Vector3(24, 20, 0); // Focus point

    div.addEventListener('mousedown', function(e) {{
        isDragging = true;
    }});
    div.addEventListener('mousemove', function(e) {{
        if(isDragging) {{
            const deltaMove = {{
                x: e.offsetX - previousMousePosition.x,
                y: e.offsetY - previousMousePosition.y
            }};
            
            // Simple rotation logic (rotate scene object group or camera)
            const angleX = deltaMove.x * 0.01;
            const angleY = deltaMove.y * 0.01;
            
            // Rotate camera around target
            const x = camera.position.x - target.x;
            const z = camera.position.z - target.z;
            
            camera.position.x = x * Math.cos(angleX) - z * Math.sin(angleX) + target.x;
            camera.position.z = x * Math.sin(angleX) + z * Math.cos(angleX) + target.z;
            
            camera.lookAt(target);
        }}
        previousMousePosition = {{ x: e.offsetX, y: e.offsetY }};
    }});
    div.addEventListener('mouseup', function(e) {{ isDragging = false; }});
    div.addEventListener('wheel', function(e) {{
        e.preventDefault();
        camera.position.z += e.deltaY * 0.1;
    }});

    function animate() {{
        requestAnimationFrame(animate);
        renderer.render(scene, camera);
    }}
    animate();
    
    // Resize Handle
    window.addEventListener('resize', function() {{
        const width = div.clientWidth;
        const height = div.clientHeight;
        renderer.setSize(width, height);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
    }});

</script>
</body>
</html>
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Report Generated: {REPORT_PATH}")
