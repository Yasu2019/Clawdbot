import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// --- Global State ---
const State = {
    mode: '2d', // '2d' or '3d'
    chain: [],  // [{ id, component, feature, nominal, tol, dir }]
    dxf: {
        parser: null,
        data: null,
        entities: [],
        transforms: { scale: 20, offsetX: 400, offsetY: 300 },
        selectedEnt: null
    },
    threed: {
        scene: null,
        camera: null,
        renderer: null,
        controls: null,
        modelGroup: null,
        originalPos: {},
        explodeProgress: 0,
        targetExplode: 0,
        isManualExplode: false
    },
    charts: {
        histogram: null,
        sensitivity: null
    }
};

// --- DOM Elements ---
const DOM = {
    tabs: { d2: document.getElementById('tab2d'), d3: document.getElementById('tab3d') },
    views: { d2: document.getElementById('view2d'), d3: document.getElementById('view3d') },
    dxfCanvas: document.getElementById('dxfCanvas'),
    canvas3d: document.getElementById('canvas3d'),
    // Forms
    entityInfo: document.getElementById('entityInfo'),
    dimName: document.getElementById('dimName'),
    dirSelect: document.getElementById('dirSelect'),
    dimNominal: document.getElementById('dimNominal'),
    dimTol: document.getElementById('dimTol'),
    btnAddChain: document.getElementById('btnAddChain'),
    chainList: document.getElementById('chainList'),
    btnClearChain: document.getElementById('btnClearChain'),
    btnAnalyze: document.getElementById('btnAnalyze'),
    // Results
    resultPanel: document.getElementById('resultPanel'),
    resNominal: document.getElementById('resNominal'),
    resWC: document.getElementById('resWC'),
    resRSS: document.getElementById('resRSS'),
    // 3D Specific
    quickAdd3D: document.getElementById('quickAdd3D'),
    presetList3D: document.getElementById('presetList3D'),
    btnExplode: document.getElementById('btnExplode'),
    explodeSliderContainer: document.getElementById('explodeSliderContainer'),
    explodeSlider: document.getElementById('explodeSlider')
};

// --- Initialization ---
function init() {
    setupTabs();
    setupForms();

    // Auto-init 2D canvas size
    resize2D();
    window.addEventListener('resize', () => {
        resize2D();
        if (State.mode === '3d' && State.threed.renderer) {
            State.threed.renderer.setSize(DOM.canvas3d.clientWidth, DOM.canvas3d.clientHeight);
            State.threed.camera.aspect = DOM.canvas3d.clientWidth / DOM.canvas3d.clientHeight;
            State.threed.camera.updateProjectionMatrix();
        }
    });

    // Lazy load DXF parser
    if (typeof DxfParser !== 'undefined') {
        State.dxf.parser = new DxfParser();
        setup2DInteraction();
    } else {
        setTimeout(init, 500); // Retry if CDN slow
        return;
    }

    // Init 3D
    init3D();

    // Default to 3D mode for dramatic effect
    switchTab('3d');
}

// --- Tab Logic ---
function setupTabs() {
    DOM.tabs.d2.addEventListener('click', () => switchTab('2d'));
    DOM.tabs.d3.addEventListener('click', () => switchTab('3d'));
}

function switchTab(mode) {
    State.mode = mode;

    DOM.tabs.d2.classList.toggle('active', mode === '2d');
    DOM.tabs.d3.classList.toggle('active', mode === '3d');

    DOM.views.d2.classList.toggle('active', mode === '2d');
    DOM.views.d3.classList.toggle('active', mode === '3d');

    // UI Toggles
    DOM.quickAdd3D.style.display = mode === '3d' ? 'block' : 'none';

    if (mode === '2d') {
        resize2D();
        draw2D();
    } else {
        if (!State.threed.renderer) init3D();
    }
}

// --- 3D Module (Three.js) ---
function init3D() {
    if (State.threed.renderer) return;

    const w = DOM.canvas3d.clientWidth;
    const h = DOM.canvas3d.clientHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
    camera.position.set(80, 60, 80);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(window.devicePixelRatio);
    DOM.canvas3d.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    // Lights
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(50, 100, 50);
    scene.add(dirLight);

    const modelGroup = new THREE.Group();
    scene.add(modelGroup);

    State.threed = { ...State.threed, scene, camera, renderer, controls, modelGroup };

    buildSample3DAssembly();

    // Toolbar Listeners
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const view = e.target.dataset.view;
            if (!view) return;
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            if (view !== 'explode') e.target.classList.add('active');

            // Reset explode
            State.threed.isManualExplode = false;
            State.threed.targetExplode = 0;
            State.threed.explodeProgress = 0;
            DOM.explodeSliderContainer.style.display = 'none';
            DOM.btnExplode.classList.remove('active');
            DOM.btnExplode.innerText = "💥 分解";

            if (modelGroup.children.length === 4) {
                modelGroup.children[0].position.y = State.threed.originalPos.shaft;
                modelGroup.children[1].position.y = State.threed.originalPos.ib;
                modelGroup.children[2].position.y = State.threed.originalPos.ob;
                modelGroup.children[3].position.y = State.threed.originalPos.housing;
            }

            switch (view) {
                case 'iso': buildSample3DAssembly(); camera.position.set(80, 60, 80); break;
                case 'section': buildSection3DAssembly(); camera.position.set(80, 40, 0); break;
                case 'top': buildSample3DAssembly(); camera.position.set(0, 150, 0); break;
                case 'front': buildSample3DAssembly(); camera.position.set(0, 30, 150); break;
            }
        });
    });

    DOM.btnExplode.addEventListener('click', () => {
        State.threed.isManualExplode = false;
        if (State.threed.targetExplode > 0.5) {
            State.threed.targetExplode = 0;
            DOM.explodeSliderContainer.style.display = 'none';
            DOM.btnExplode.classList.remove('active');
            DOM.btnExplode.innerText = "💥 分解";
        } else {
            State.threed.targetExplode = 1;
            DOM.explodeSliderContainer.style.display = 'flex';
            DOM.btnExplode.classList.add('active');
            DOM.btnExplode.innerText = "🧩 復元";
        }
    });

    DOM.explodeSlider.addEventListener('input', (e) => {
        State.threed.isManualExplode = true;
        State.threed.targetExplode = e.target.value / 100;
        State.threed.explodeProgress = State.threed.targetExplode;
        if (State.threed.targetExplode > 0.01) {
            DOM.btnExplode.classList.add('active');
            DOM.btnExplode.innerText = "🧩 復元";
        } else {
            DOM.btnExplode.classList.remove('active');
            DOM.btnExplode.innerText = "💥 分解";
        }
    });

    animate3D();
}

function buildSample3DAssembly() {
    const { modelGroup } = State.threed;
    modelGroup.clear();

    const r_shaft = 10, r_ib_in = 11, r_ib_out = 15, r_ob_in = 16, r_ob_out = 25, r_h_in = 27, r_h_out = 35, h = 50;

    const matShaft = new THREE.MeshStandardMaterial({ color: 0xc586c0, metalness: 0.4, roughness: 0.4 });
    const matIB = new THREE.MeshStandardMaterial({ color: 0xdcdcaa, metalness: 0.4, roughness: 0.4 });
    const matOB = new THREE.MeshStandardMaterial({ color: 0x4ec9b0, metalness: 0.4, roughness: 0.4 });
    const matHousing = new THREE.MeshStandardMaterial({ color: 0x007acc, metalness: 0.4, roughness: 0.4 });

    function createTube(rIn, rOut, height, material) {
        const shape = new THREE.Shape();
        shape.absarc(0, 0, rOut, 0, Math.PI * 2, false);
        const holePath = new THREE.Path();
        holePath.absarc(0, 0, rIn, 0, Math.PI * 2, true);
        shape.holes.push(holePath);
        const geometry = new THREE.ExtrudeGeometry(shape, { depth: height, bevelEnabled: false, curveSegments: 32 });
        const mesh = new THREE.Mesh(geometry, material);
        mesh.rotation.x = -Math.PI / 2;
        return mesh;
    }

    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(r_shaft, r_shaft, h + 10, 64), matShaft);
    shaft.position.y = (h + 10) / 2 - 5;
    modelGroup.add(shaft);

    const ib = createTube(r_ib_in, r_ib_out, h, matIB);
    ib.position.y = 0;
    modelGroup.add(ib);

    const ob = createTube(r_ob_in, r_ob_out, h, matOB);
    ob.position.y = 0;
    modelGroup.add(ob);

    const housing = createTube(r_h_in, r_h_out, h - 10, matHousing);
    housing.position.y = 5;
    modelGroup.add(housing);

    State.threed.originalPos = {
        shaft: shaft.position.y,
        ib: ib.position.y,
        ob: ob.position.y,
        housing: housing.position.y
    };

    populate3DPresets();
}

function buildSection3DAssembly() {
    const { modelGroup } = State.threed;
    // Basic flat section geometry for demo purposes
    buildSample3DAssembly(); // Fallback for now to maintain original Pos refs
}

function populate3DPresets() {
    DOM.presetList3D.innerHTML = '';
    const presets = [
        { name: '4. ハウジング内径', nom: 50.05, tol: 0.03, comp: 'Housing' },
        { name: '3. Aブッシュ外径', nom: 49.95, tol: 0.02, comp: 'OuterBush' },
        { name: '3. Aブッシュ内径', nom: 30.05, tol: 0.02, comp: 'OuterBush' },
        { name: '2. Iブッシュ外径', nom: 29.95, tol: 0.02, comp: 'InnerBush' },
        { name: '2. Iブッシュ内径', nom: 20.05, tol: 0.015, comp: 'InnerBush' },
        { name: '1. シャフト外径', nom: 19.95, tol: 0.01, comp: 'Shaft' }
    ];

    presets.forEach(p => {
        const div = document.createElement('div');
        div.className = 'preset-item';
        div.innerHTML = `<span>${p.name}</span> <span style="color:#aaa;">Φ${p.nom} ±${p.tol}</span>`;
        div.onclick = () => {
            DOM.dimName.value = p.name;
            DOM.dimNominal.value = p.nom;
            DOM.dimTol.value = p.tol;
            DOM.entityInfo.innerHTML = `選択中: <b>${p.name}</b> (3D Preset)`;
        };
        DOM.presetList3D.appendChild(div);
    });
}

function animate3D() {
    requestAnimationFrame(animate3D);
    const state = State.threed;

    if (state.scene && state.camera) {
        // Explode Animation
        if (!state.isManualExplode && Math.abs(state.explodeProgress - state.targetExplode) > 0.001) {
            state.explodeProgress += (state.targetExplode - state.explodeProgress) * 0.1;
            DOM.explodeSlider.value = state.explodeProgress * 100;
        } else if (!state.isManualExplode) {
            state.explodeProgress = state.targetExplode;
        }

        if (state.modelGroup && state.modelGroup.children.length >= 4) {
            const p = state.explodeProgress;
            const target = { shaft: -60, ib: -20, ob: 20, housing: 60 };
            const orig = state.originalPos;

            state.modelGroup.children[0].position.y = orig.shaft + (target.shaft - orig.shaft) * p;
            state.modelGroup.children[1].position.y = orig.ib + (target.ib - orig.ib) * p;
            state.modelGroup.children[2].position.y = orig.ob + (target.ob - orig.ob) * p;
            state.modelGroup.children[3].position.y = orig.housing + (target.housing - orig.housing) * p;
        }

        state.controls.update();
        state.renderer.render(state.scene, state.camera);
    }
}


// --- 2D Module (Canvas & DXF) ---
function resize2D() {
    if (DOM.dxfCanvas.parentElement) {
        DOM.dxfCanvas.width = DOM.dxfCanvas.parentElement.clientWidth;
        DOM.dxfCanvas.height = DOM.dxfCanvas.parentElement.clientHeight;
        draw2D();
    }
}

function setup2DInteraction() {
    // (Will inject simplified DXF loader here or leave stub for file picking)
    // See original tolerance_2d_dxf_demo.html for full hit-test geometry math
    const ctx = DOM.dxfCanvas.getContext('2d');

    // Draw a placeholder grid
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, DOM.dxfCanvas.width, DOM.dxfCanvas.height);
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    for (let i = 0; i < DOM.dxfCanvas.width; i += 50) {
        ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, DOM.dxfCanvas.height); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(DOM.dxfCanvas.width, i); ctx.stroke();
    }

    ctx.fillStyle = '#888';
    ctx.font = '14px sans-serif';
    ctx.fillText('DXF Module Ready. Waiting for file load...', 20, 30);
}

function draw2D() {
    setup2DInteraction();
}


// --- Forms & Chain Logic ---
function setupForms() {
    DOM.btnAddChain.addEventListener('click', () => {
        const name = DOM.dimName.value.trim();
        const nom = parseFloat(DOM.dimNominal.value);
        const tol = parseFloat(DOM.dimTol.value);
        const dir = DOM.dirSelect.value; // '+' or '-'

        if (!name) { alert("寸法名を入力してください"); return; }
        if (isNaN(nom) || isNaN(tol)) { alert("数値を正しく入力してください"); return; }

        State.chain.push({
            id: Date.now().toString(),
            name,
            nominal: nom,
            tol: tol,
            direction: dir
        });

        updateChainUI();

        // Reset inputs
        DOM.dimName.value = '';
        DOM.dimNominal.value = '';
    });

    DOM.btnClearChain.addEventListener('click', () => {
        State.chain = [];
        updateChainUI();
        DOM.resultPanel.style.display = 'none';
        if (State.charts.histogram) State.charts.histogram.destroy();
        if (State.charts.sensitivity) State.charts.sensitivity.destroy();
    });

    DOM.btnAnalyze.addEventListener('click', runAnalysis);
}

window.deleteChainItem = function (id) {
    State.chain = State.chain.filter(c => c.id !== id);
    updateChainUI();
}

function updateChainUI() {
    if (State.chain.length === 0) {
        DOM.chainList.innerHTML = `<div style="color:#666; font-size:12px; text-align:center; padding:20px;">チェーンは空です。</div>`;
        return;
    }

    DOM.chainList.innerHTML = State.chain.map(c => `
        <div class="chain-item dir-${c.direction === '+' ? 'plus' : 'minus'}">
            <div style="flex:1;">
                <span style="display:inline-block; width:20px; text-align:center; font-weight:bold; color:${c.direction === '+' ? '#4ec9b0' : '#d16969'}">${c.direction}</span>
                ${c.name}
            </div>
            <div class="chain-item-actions">
                <span class="chain-val">${c.nominal.toFixed(2)} ±${c.tol.toFixed(3)}</span>
                <button class="btn-icon" onclick="deleteChainItem('${c.id}')">❌</button>
            </div>
        </div>
    `).join('');
}


// --- Statistical Engine (Fisher / CETOL logic) ---
function runAnalysis() {
    if (State.chain.length === 0) {
        alert("解析するチェーンデータがありません。");
        return;
    }

    let sumNom = 0;
    let sumTol = 0;
    let sumVar = 0;

    State.chain.forEach(c => {
        const sign = c.direction === '+' ? 1 : -1;
        sumNom += c.nominal * sign;
        sumTol += c.tol;
        sumVar += Math.pow(c.tol, 2);
    });

    const rss = Math.sqrt(sumVar);

    DOM.resNominal.innerText = sumNom.toFixed(3);
    DOM.resWC.innerText = `±${sumTol.toFixed(3)}`;
    DOM.resRSS.innerText = `±${rss.toFixed(3)}`;

    // Determine Interference Risk (simplistic)
    if (sumNom - sumTol < 0) {
        DOM.resWC.className = 'metric-val danger';
    } else {
        DOM.resWC.className = 'metric-val warning';
    }

    DOM.resultPanel.style.display = 'block';

    runMonteCarlo(sumNom);
    renderSensitivity(sumVar);
}

function runMonteCarlo(sumNom) {
    const samples = 100000; // 100k points
    const results = new Float32Array(samples);

    for (let i = 0; i < samples; i++) {
        let val = 0;
        for (let j = 0; j < State.chain.length; j++) {
            const c = State.chain[j];
            const sign = c.direction === '+' ? 1 : -1;

            // Box-Muller Transform for Normal Distribution
            let u = 0, v = 0;
            while (u === 0) u = Math.random();
            while (v === 0) v = Math.random();
            const z = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);

            // Assuming given Tol is 3Sigma
            const sigma = c.tol / 3.0;
            val += (c.nominal + z * sigma) * sign;
        }
        results[i] = val;
    }

    // Histogram grouping
    let min = results[0], max = results[0];
    for (let i = 1; i < samples; i++) {
        if (results[i] < min) min = results[i];
        if (results[i] > max) max = results[i];
    }

    // Expand bounds slightly
    const range = max - min;
    min -= range * 0.1;
    max += range * 0.1;

    const binCount = 40;
    const binSize = (max - min) / binCount;
    const bins = new Array(binCount).fill(0);
    const labels = [];

    for (let i = 0; i < samples; i++) {
        let idx = Math.floor((results[i] - min) / binSize);
        if (idx >= binCount) idx = binCount - 1;
        if (idx < 0) idx = 0;
        bins[idx]++;
    }

    for (let i = 0; i < binCount; i++) {
        labels.push((min + binSize * (i + 0.5)).toFixed(3));
    }

    const ctx = document.getElementById('histogramChart');
    if (State.charts.histogram) State.charts.histogram.destroy();

    State.charts.histogram = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '分布',
                data: bins,
                backgroundColor: 'rgba(0, 122, 204, 0.7)',
                borderColor: 'rgba(0, 122, 204, 1)',
                borderWidth: 1,
                barPercentage: 1.0,
                categoryPercentage: 1.0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { display: false },
                y: { display: false }
            },
            plugins: { legend: { display: false }, tooltip: { enabled: true } }
        }
    });
}

function renderSensitivity(totalVariance) {
    const contributions = State.chain.map(c => {
        const uPercent = (Math.pow(c.tol, 2) / totalVariance) * 100;
        return { name: c.name, val: parseFloat(uPercent.toFixed(1)) };
    });

    // Sort descending
    contributions.sort((a, b) => b.val - a.val);

    const ctx = document.getElementById('sensitivityChart');
    if (State.charts.sensitivity) State.charts.sensitivity.destroy();

    const colors = ['#d16969', '#dcdcaa', '#4ec9b0', '#c586c0', '#007acc', '#ce9178'];

    State.charts.sensitivity = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: contributions.map(c => c.name),
            datasets: [{
                label: 'Variance Contribution (%)',
                data: contributions.map(c => c.val),
                backgroundColor: colors.slice(0, contributions.length),
                borderWidth: 0
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { max: 100, ticks: { color: '#888' }, grid: { color: '#333' } },
                y: { ticks: { color: '#eee' }, grid: { display: false } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

// Start app
document.addEventListener('DOMContentLoaded', init);
