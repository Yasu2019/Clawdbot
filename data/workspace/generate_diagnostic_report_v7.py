
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
REPORT_PATH = os.path.join(WORKSPACE_DIR, "gap_analysis_report_v7_diagnostic.html")
THREE_JS_PATH = os.path.join(REPORT_DIR, "three.min.js")

# --- 1. Simulation Logic (Simplified) ---
sim_x = np.random.normal(1.5, 0.05, 1000)
sim_y = np.random.normal(0.575, 0.05, 1000)

def create_hist(data, filename, title):
    plt.figure(figsize=(4, 3))
    plt.hist(data, bins=30, color='#3498db', alpha=0.7)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, filename))
    plt.close()

create_hist(sim_x, "hist_x_v7.png", "X-Axis Gap")
create_hist(sim_y, "hist_y_v7.png", "Y-Axis Gap")

def get_b64(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_x = get_b64("hist_x_v7.png")
img_y = get_b64("hist_y_v7.png")

# --- 2. 3D Model Processing (Reliable) ---
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
                            val = [float(p) for p in parts[1:4]]
                            if not any(math.isnan(v) for v in val):
                                vertices.extend(val)
                        except: pass
    return vertices

# Use Stride=10 to keep it light
v_frame = obj_to_list("frame.obj", stride=10)
v_punch = obj_to_list("punch.obj", stride=10)
v_strip = obj_to_list("product_1.obj", stride=5)

# --- 3. Embed Three.js ---
three_js_content = ""
if os.path.exists(THREE_JS_PATH):
    with open(THREE_JS_PATH, "r", encoding="utf-8") as f:
        three_js_content = f.read()

# --- 4. Diagnostic HTML ---
html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gap Analysis v7 (Diagnostic)</title>
    <style>
        body {{ font-family: monospace; background: #eee; margin: 0; padding: 20px; }}
        .container {{ display: flex; flex-direction: column; height: 90vh; background: white; border: 2px solid #333; }}
        #viewer-container {{ flex: 1; position: relative; background: #000; overflow: hidden; }}
        #debug-panel {{ 
            height: 150px; 
            background: #222; 
            color: #0f0; 
            padding: 10px; 
            overflow-y: auto; 
            font-family: 'Consolas', monospace; 
            border-top: 2px solid #666;
        }}
        #overlay {{
            position: absolute; top: 10px; left: 10px; 
            background: rgba(0,0,0,0.7); color: white; 
            padding: 10px; pointer-events: none;
        }}
    </style>
    <script>{three_js_content}</script>
</head>
<body>

<h3>v7 Diagnostic Report</h3>
<p>If you see a <strong>Red Spinning Cube</strong>, WebGL is working. If you see points, data is loaded. If screen is black, check logs below.</p>

<div class="container">
    <div id="viewer-container">
        <div id="overlay">Status: Initialization...</div>
    </div>
    <div id="debug-panel">Waiting for JS execution...<br></div>
</div>

<!-- Embedded Data -->
<script type="application/json" id="d-frame">{json.dumps(v_frame)}</script>
<script type="application/json" id="d-punch">{json.dumps(v_punch)}</script>
<script type="application/json" id="d-strip">{json.dumps(v_strip)}</script>

<script>
    const debug = document.getElementById('debug-panel');
    const status = document.getElementById('overlay');
    
    function log(msg) {{
        console.log(msg);
        debug.innerHTML += `> ${{msg}}<br>`;
        debug.scrollTop = debug.scrollHeight;
    }}

    window.onerror = function(msg, url, line) {{
        log(`CRITICAL ERROR: ${{msg}} (Line ${{line}})`);
        status.innerText = "CRASHED";
        status.style.color = "red";
        return false; // let default handler run too
    }};

    function main() {{
        log("Starting Main...");
        
        // 1. Check Library
        if (typeof THREE === 'undefined') {{
            throw new Error("Three.js not loaded.");
        }}
        log("Three.js Version: " + THREE.REVISION);

        // 2. Setup Scene
        const container = document.getElementById('viewer-container');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x202020);
        
        const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 10000);
        
        let renderer;
        try {{
            renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(container.clientWidth, container.clientHeight);
            container.appendChild(renderer.domElement);
            log("WebGL Renderer created successfully.");
        }} catch(e) {{
            throw new Error("WebGL Creation Failed: " + e.message);
        }}

        // 3. Add Diagnostic Objects
        // Red Cube at 0,0,0
        const cubeGeo = new THREE.BoxGeometry(10, 10, 10);
        const cubeMat = new THREE.MeshBasicMaterial({{ color: 0xff0000, wireframe: true }});
        const cube = new THREE.Mesh(cubeGeo, cubeMat);
        scene.add(cube);
        log("Added Reference Red Cube at (0,0,0)");

        // Axes Helper
        scene.add(new THREE.AxesHelper(100));

        // 4. Load Data & Auto-Center
        function loadPoints(id, color, name) {{
            const txt = document.getElementById(id).textContent;
            const data = JSON.parse(txt);
            log(`Loaded ${{name}}: ${{data.length/3}} points.`);
            
            if (data.length === 0) return null;
            
            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(data, 3));
            const material = new THREE.PointsMaterial({{ color: color, size: 0.5 }});
            const points = new THREE.Points(geometry, material);
            scene.add(points);
            return points;
        }}

        const pFrame = loadPoints("d-frame", 0xaaaaaa, "Frame");
        const pPunch = loadPoints("d-punch", 0x3498db, "Punch");
        const pStrip = loadPoints("d-strip", 0xFFFF00, "Strip");

        // 5. Calculate Bounding Box
        const fullBox = new THREE.Box3();
        let pointCount = 0;
        [pFrame, pPunch, pStrip].forEach(p => {{
            if(p) {{
                p.geometry.computeBoundingBox();
                fullBox.expandByObject(p);
                pointCount += p.geometry.attributes.position.count;
            }}
        }});
        
        const center = new THREE.Vector3();
        fullBox.getCenter(center);
        const size = new THREE.Vector3();
        fullBox.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        
        log(`Total Points: ${{pointCount}}`);
        log(`Bounding Box Center: X=${{center.x.toFixed(2)}}, Y=${{center.y.toFixed(2)}}, Z=${{center.z.toFixed(2)}}`);
        log(`Bounding Box Size: ${{size.x.toFixed(2)}} x ${{size.y.toFixed(2)}} x ${{size.z.toFixed(2)}}`);
        
        status.innerText = `Running. Center: (${{center.x.toFixed(0)}}, ${{center.y.toFixed(0)}}). Points: ${{pointCount}}`;

        // 6. Camera Positioning
        if (pointCount > 0) {{
            log("Auto-Centering Camera...");
            camera.position.copy(center);
            camera.position.z += maxDim * 1.5 + 50; // Ensure we are backed out enough
            camera.position.y += maxDim * 0.5;
            camera.lookAt(center);
        }} else {{
            log("No points loaded! Camera looking at (0,0,0)");
            camera.position.set(30,30,30);
            camera.lookAt(0,0,0);
        }}
        
        log(`Final Camera Pos: X=${{camera.position.x.toFixed(2)}}, Z=${{camera.position.z.toFixed(2)}}`);

        // 7. Loop
        function animate() {{
            requestAnimationFrame(animate);
            cube.rotation.x += 0.01;
            cube.rotation.y += 0.01;
            renderer.render(scene, camera);
        }}
        animate();
        
        // Validation Check
        setTimeout(() => {{
            if (renderer.info.render.calls === 0) log("WARNING: Render calls is 0. Loop might not be running.");
            else log("Render Loop Active. Frames rendering.");
        }}, 2000);
    }}

    setTimeout(main, 500);

</script>
</body>
</html>
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Generated Diagnostic Report: {REPORT_PATH}")
