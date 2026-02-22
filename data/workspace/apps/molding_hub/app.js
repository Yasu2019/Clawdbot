// Three.js State
let scene, camera, renderer, controls;
let productMesh = null;
let coolingMesh = null;
let raycaster = new THREE.Raycaster();
let mouse = new THREE.Vector2();

// App State
let gates = []; // Array of {x,y,z, mesh}
let mode = 'view'; // 'view' or 'gate'

// Initialize on load
init3D();
setupEventListeners();

function init3D() {
    const container = document.getElementById('canvas-container-3d');

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0d1117);

    // Grid Helper
    const grid = new THREE.GridHelper(200, 40, 0x2A3140, 0x1A202C);
    scene.add(grid);

    // Axes
    const axes = new THREE.AxesHelper(50);
    scene.add(axes);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight1.position.set(100, 200, 100);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x2A85FF, 0.4);
    dirLight2.position.set(-100, -200, -100);
    scene.add(dirLight2);

    // Camera
    camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 1, 1000);
    camera.position.set(100, 100, 100);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    // Controls
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    // Raycaster Event
    renderer.domElement.addEventListener('pointerdown', onPointerDown);

    // Window Resize
    window.addEventListener('resize', onWindowResize);

    // Render Loop
    animate();
}

function onWindowResize() {
    const container = document.getElementById('canvas-container-3d');
    if (!container) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

function resetView(type) {
    if (type === 'iso') camera.position.set(100, 100, 100);
    if (type === 'top') camera.position.set(0, 150, 0);
    if (type === 'front') camera.position.set(0, 0, 150);
    camera.lookAt(0, 0, 0);
    controls.target.set(0, 0, 0);
}

function loadSTL(file, type) {
    const reader = new FileReader();
    reader.onload = function (e) {
        const loader = new THREE.STLLoader();
        const geometry = loader.parse(e.target.result);
        geometry.center();
        geometry.computeVertexNormals();

        // Remove previous
        if (type === 'product' && productMesh) scene.remove(productMesh);
        if (type === 'cooling' && coolingMesh) scene.remove(coolingMesh);

        let material;
        if (type === 'product') {
            material = new THREE.MeshStandardMaterial({
                color: 0x94A3B8, // Light gray
                roughness: 0.5,
                metalness: 0.1,
                transparent: true,
                opacity: 0.8
            });
            productMesh = new THREE.Mesh(geometry, material);
            scene.add(productMesh);
            showToast("Product Model Loaded");
        } else {
            material = new THREE.MeshStandardMaterial({
                color: 0x2A85FF, // Blue pipe
                roughness: 0.2,
                metalness: 0.8
            });
            coolingMesh = new THREE.Mesh(geometry, material);
            scene.add(coolingMesh);
            showToast("Cooling System Loaded");
        }
    };
    reader.readAsArrayBuffer(file);
}

function onPointerDown(event) {
    if (mode !== 'gate' || !productMesh) return;

    const container = document.getElementById('canvas-container-3d');
    const rect = renderer.domElement.getBoundingClientRect();

    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObject(productMesh);

    if (intersects.length > 0) {
        const point = intersects[0].point;
        addGatePoint(point);
    }
}

function addGatePoint(pos) {
    const geometry = new THREE.ConeGeometry(2, 6, 16);
    geometry.translate(0, 3, 0); // shift pivot to tip
    geometry.rotateX(Math.PI / 2); // Point towards the surface

    const material = new THREE.MeshBasicMaterial({ color: 0xEF4444 });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(pos);

    // Normal vector simplified assuming hitting mostly Z-up or general surface
    // Real implementation would align to face normal

    scene.add(mesh);
    gates.push({ x: pos.x, y: pos.y, z: pos.z, mesh: mesh });
    updateGateList();
    showToast(`Gate ${gates.length} added`);
}

function clearGates() {
    gates.forEach(g => scene.remove(g.mesh));
    gates = [];
    updateGateList();
    showToast("Gates cleared");
}

function updateGateList() {
    const list = document.getElementById('gate-list');
    const count = document.getElementById('gate-count');

    count.textContent = gates.length;
    list.innerHTML = '';

    if (gates.length === 0) {
        list.innerHTML = '<li class="empty-state">No gates defined. Use the crosshair tool.</li>';
        return;
    }

    gates.forEach((g, idx) => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span><i class="fa-solid fa-map-pin text-danger"></i> Gate ${idx + 1}</span>
            <span class="text-xs text-muted">(${g.x.toFixed(1)}, ${g.y.toFixed(1)}, ${g.z.toFixed(1)})</span>
        `;
        list.appendChild(li);
    });
}

// ----------------------------------------------------
// UI Logic
// ----------------------------------------------------

function setupEventListeners() {
    // Buttons
    document.getElementById('btn-view').addEventListener('click', e => {
        mode = 'view';
        controls.enabled = true;
        document.getElementById('btn-view').classList.add('active');
        document.getElementById('btn-gate').classList.remove('active');
        renderer.domElement.style.cursor = 'grab';
    });

    document.getElementById('btn-gate').addEventListener('click', e => {
        mode = 'gate';
        controls.enabled = false;
        document.getElementById('btn-gate').classList.add('active');
        document.getElementById('btn-view').classList.remove('active');
        renderer.domElement.style.cursor = 'crosshair';
    });

    document.getElementById('btn-clear-gates').addEventListener('click', clearGates);

    // File Uploads
    document.getElementById('upload-product').addEventListener('change', e => {
        if (e.target.files[0]) loadSTL(e.target.files[0], 'product');
    });

    document.getElementById('upload-cooling').addEventListener('change', e => {
        if (e.target.files[0]) loadSTL(e.target.files[0], 'cooling');
    });

    // Simulation triggers
    document.getElementById('btn-run-sim').addEventListener('click', runSingleSimulation);
    document.getElementById('btn-run-doe').addEventListener('click', runDOE);
}

function runSingleSimulation() {
    if (gates.length === 0) {
        showToast("Please add at least 1 gate before running.");
        return;
    }

    const overlay = document.getElementById('loading-overlay');
    overlay.classList.remove('hidden');
    overlay.querySelector('p').textContent = "Meshing & Solving with OpenFOAM/Elmer...";

    // Mock simulation delay
    setTimeout(() => {
        overlay.classList.add('hidden');
        showToast("Simulation Complete! Check results directory.");
    }, 2000);
}

function runDOE() {
    if (gates.length === 0) {
        showToast("Please add at least 1 gate before running DOE.");
        return;
    }

    const overlay = document.getElementById('loading-overlay');
    overlay.classList.remove('hidden');
    overlay.querySelector('p').textContent = "Running R-Language L9 Orthogonal Array Optimization...";

    // Mock DOE execution
    setTimeout(() => {
        overlay.classList.add('hidden');
        showResults();
        renderDOEChart();
        showToast("DOE Optimization Complete!");
    }, 3000);
}

function showResults() {
    document.getElementById('section-setup').classList.add('hidden');
    document.getElementById('section-results').classList.remove('hidden');
}

function showSetup() {
    document.getElementById('section-results').classList.add('hidden');
    document.getElementById('section-setup').classList.remove('hidden');
}

function renderDOEChart() {
    const ctx = document.getElementById('doeChart').getContext('2d');

    // Mock L9 data
    const labels = ['Run 1', 'Run 2', 'Run 3', 'Run 4', 'Run 5', 'Run 6', 'Run 7', 'Run 8', 'Run 9'];
    const warpageData = [0.12, 0.10, 0.09, 0.08, 0.07, 0.06, 0.055, 0.052, 0.08];
    const fillTimeData = [5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 1.5, 2.0, 1.0];

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Warpage (mm)',
                    data: warpageData,
                    borderColor: '#10B981',
                    yAxisID: 'y',
                    tension: 0.4
                },
                {
                    label: 'Fill Time (s)',
                    data: fillTimeData,
                    borderColor: '#2A85FF',
                    yAxisID: 'y1',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: { type: 'linear', display: true, position: 'left', title: { display: true, text: 'Warpage (mm)' } },
                y1: { type: 'linear', display: true, position: 'right', title: { display: true, text: 'Fill Time (s)' } }
            }
        }
    });
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// ----------------------------------------------------
// Testing Logic
// ----------------------------------------------------
function loadSampleModels() {
    // Basic rectangle plate
    const productGeom = new THREE.BoxGeometry(40, 5, 20);
    productGeom.translate(0, 2.5, 0);
    if (productMesh) scene.remove(productMesh);
    const pMat = new THREE.MeshStandardMaterial({ color: 0x94A3B8, roughness: 0.5, transparent: true, opacity: 0.8 });
    productMesh = new THREE.Mesh(productGeom, pMat);
    scene.add(productMesh);

    // U-shape cooling pipe logic simulated with simple pipes
    const coolingGeom = new THREE.CylinderGeometry(1.5, 1.5, 50, 16);
    coolingGeom.translate(0, -3, 0);
    coolingGeom.rotateZ(Math.PI / 2);
    if (coolingMesh) scene.remove(coolingMesh);
    const cMat = new THREE.MeshStandardMaterial({ color: 0x2A85FF, roughness: 0.2, metalness: 0.8 });
    coolingMesh = new THREE.Mesh(coolingGeom, cMat);
    scene.add(coolingMesh);

    showToast("Sample Models Loaded - Try Add Gate Tool!");
}
window.loadSampleModels = loadSampleModels;
