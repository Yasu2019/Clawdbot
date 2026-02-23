import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';

/**
 * Kinematics Hub App Logic
 * Inherited from v58 Progressive Die Simulation
 */

const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
const hud = document.getElementById('hud');
const help = document.getElementById('help');
const info = document.getElementById('info');
const loadingOverlay = document.getElementById('loading-overlay');

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0a12);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 2000);
camera.position.set(150, 120, 250);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(80, 30, 0);

scene.add(new THREE.AmbientLight(0xffffff, 0.4));
const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
dirLight.position.set(100, 200, 100);
scene.add(dirLight);

const grid = new THREE.GridHelper(800, 80, 0x444488, 0x222244);
grid.position.y = -1;
scene.add(grid);

// Constants & Parameters
const pitch = 120;
const station1X = pitch;
const station2X = 0;
const baseH = 15;
const dieWidth = 70;
const dieDepth = 12;
const dieTop = baseH + dieDepth;
const materialThickness = 0.8;
const visualThickness = 0.8;
const materialY = dieTop + visualThickness / 2;
const speed = 40;
const sheetWidth = 50;
const sheetLength = 280;
const productLength = pitch + 24;

// Simulation State
const ST = { FEED: 0, CLAMP: 1, CUT: 2, BEND: 3, HOLD: 4, LIFT: 5, EJECT: 6 };
const STN = ['給材 (FEED)', 'クランプ (CLAMP)', '切断 (CUT)', '曲げ (BEND)', '保持 (HOLD)', '上昇 (LIFT)', '排出 (EJECT)'];
let state = ST.FEED;
let stateT = 0;
let tSim = 0;
let cycleCount = 0;
let play = true;
let hasCut = false;
let punchContact = false;

// Geometry Groups
const topPlateGroup = new THREE.Group();
const vPunchGroup = new THREE.Group();
const stripperGroup = new THREE.Group();
const bladeGroup = new THREE.Group();
scene.add(topPlateGroup, vPunchGroup, stripperGroup, bladeGroup);

// --- Static Die Setup ---
const dieMat = new THREE.MeshStandardMaterial({ color: 0x445566, metalness: 0.6, roughness: 0.35 });
const baseDie = new THREE.Mesh(new THREE.BoxGeometry(pitch + 200, baseH, dieWidth + 20), dieMat);
baseDie.position.set(pitch / 2 + 20, baseH / 2, 0);
scene.add(baseDie);

// --- Moving Parts Implementation ---
function createMachine() {
    // Stripper implementation
    const strMat = new THREE.MeshStandardMaterial({ color: 0xff3333, metalness: 0.5, roughness: 0.3 });
    const leftStripper = new THREE.Mesh(new THREE.BoxGeometry(38, 6, dieWidth), strMat);
    leftStripper.position.set(station1X - 22, 0, 0);
    stripperGroup.add(leftStripper);

    const rightStripper = new THREE.Mesh(new THREE.BoxGeometry(65, 6, dieWidth), strMat);
    rightStripper.position.set(station1X + 35, 0, 0);
    stripperGroup.add(rightStripper);
    stripperGroup.position.y = 60;

    // V-Punch implementation
    const punchMat = new THREE.MeshStandardMaterial({ color: 0x778888, metalness: 0.7, roughness: 0.3 });
    const punchBody = new THREE.Mesh(new THREE.BoxGeometry(32, 12, dieWidth - 6), punchMat);
    punchBody.position.set(station2X, 70, 0);
    vPunchGroup.add(punchBody);
}
createMachine();

// --- Material & Product Engine (PBD) ---
const uncutMesh = new THREE.Mesh(
    new THREE.BoxGeometry(sheetLength, visualThickness, sheetWidth),
    new THREE.MeshStandardMaterial({ color: 0x88bb44, metalness: 0.4, roughness: 0.5 })
);
scene.add(uncutMesh);

// PBD Data
const NX = 30, NZ = 15;
const N = NX * NZ;
const segX = productLength / (NX - 1);
const segZ = sheetWidth / (NZ - 1);

const topPos = new Float32Array(N * 3);
const botPos = new Float32Array(N * 3);
const velocity = new Float32Array(N * 3);
const targetY = new Float32Array(N);
const constraints = [];

const productGeom = new THREE.BufferGeometry();
const positions = new Float32Array(N * 2 * 3);
const colors = new Float32Array(N * 2 * 3);
productGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
productGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

// Indexing for solid mesh
const indices = [];
for (let ix = 0; ix < NX - 1; ix++) {
    for (let iz = 0; iz < NZ - 1; iz++) {
        const a = ix * NZ + iz, b = a + 1, c = (ix + 1) * NZ + iz, d = c + 1;
        indices.push(a, c, b, b, c, d);
        indices.push(a + N, b + N, c + N, b + N, d + N, c + N);
    }
}
productGeom.setIndex(indices);

const productMesh = new THREE.Mesh(productGeom, new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide, metalness: 0.5, roughness: 0.4 }));
productMesh.visible = false;
scene.add(productMesh);

// --- Moving Parts Advanced ---
let bladeMesh = null;
const bladeMat = new THREE.MeshStandardMaterial({ color: 0xccddee, metalness: 0.9, roughness: 0.1, emissive: 0x445566, side: THREE.DoubleSide });

function createBladeMesh() {
    if (bladeMesh) { bladeGroup.remove(bladeMesh); bladeMesh.geometry.dispose(); }
    const segs = 20, verts = [], inds = [], bladeThickness = 3, bladeHeight = 30;
    for (let iz = 0; iz <= segs; iz++) {
        const z = (iz / segs - 0.5) * sheetWidth;
        const x = station1X; // Default straight
        verts.push(x - bladeThickness / 2, bladeHeight / 2, z, x - bladeThickness / 2, -bladeHeight / 2, z);
        verts.push(x + bladeThickness / 2, bladeHeight / 2, z, x + bladeThickness / 2, -bladeHeight / 2, z);
    }
    for (let iz = 0; iz < segs; iz++) {
        const base = iz * 4;
        inds.push(base, base + 4, base + 1, base + 1, base + 4, base + 5);
        // ... (other faces)
    }
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
    geom.setIndex(inds);
    geom.computeVertexNormals();
    bladeMesh = new THREE.Mesh(geom, bladeMat);
    bladeGroup.add(bladeMesh);
    bladeGroup.position.set(0, 50, 0);
}
createBladeMesh();

// Raycasting for Contact
const raycaster = new THREE.Raycaster();
const cutLineX = new Float32Array(50);
for (let i = 0; i < cutLineX.length; i++) cutLineX[i] = station1X;

function detectBladeContactLine() {
    bladeGroup.updateMatrixWorld(true);
    const bladeWorldY = bladeGroup.position.y;
    const numSamples = cutLineX.length;
    for (let iz = 0; iz < numSamples; iz++) {
        const z = (iz / (numSamples - 1) - 0.5) * sheetWidth;
        const origin = new THREE.Vector3(station1X - 100, bladeWorldY, z);
        const direction = new THREE.Vector3(1, 0, 0);
        raycaster.set(origin, direction);
        const intersects = raycaster.intersectObject(bladeMesh, false);
        if (intersects.length > 0) cutLineX[iz] = intersects[0].point.x;
    }
}

// PBD Initialization
function initProduct() {
    for (let ix = 0; ix < NX; ix++) {
        for (let iz = 0; iz < NZ; iz++) {
            const i = ix * NZ + iz;
            const z = (iz - (NZ - 1) / 2) * segZ;
            const x = station1X - productLength + (ix / (NX - 1)) * productLength;
            topPos[i * 3] = x;
            topPos[i * 3 + 1] = materialY + visualThickness / 2;
            topPos[i * 3 + 2] = z;
            botPos[i * 3] = x;
            botPos[i * 3 + 1] = materialY - visualThickness / 2;
            botPos[i * 3 + 2] = z;
            targetY[i] = topPos[i * 3 + 1];
        }
    }
}

// Simulation Engine
function simulateProduct(dt) {
    const punchY = 70 + vPunchGroup.position.y - 12; // Adjusted tip height
    for (let i = 0; i < N; i++) {
        const idx = i * 3;
        const x = topPos[idx];
        let y = topPos[idx + 1];

        // Punch contact
        if (y > punchY && Math.abs(x - station2X) < 15) {
            topPos[idx + 1] = punchY;
            if (punchY < targetY[i]) targetY[i] = punchY;
        }

        // Die contact
        const dieY = (Math.abs(x - station2X) < 12) ? baseH : dieTop;
        if (topPos[idx + 1] < dieY + visualThickness) {
            topPos[idx + 1] = dieY + visualThickness;
            if (topPos[idx + 1] < targetY[i]) targetY[i] = topPos[idx + 1];
        }
    }

    // Smooth deformation sync
    for (let i = 0; i < N; i++) {
        const idx = i * 3;
        topPos[idx + 1] = targetY[i];
        botPos[idx + 1] = targetY[i] - visualThickness;
        botPos[idx] = topPos[idx];
        botPos[idx + 2] = topPos[idx + 2];
    }
}

function updateProductMesh() {
    const pos = productGeom.attributes.position;
    const col = productGeom.attributes.color;
    for (let i = 0; i < N; i++) {
        pos.setXYZ(i, topPos[i * 3], topPos[i * 3 + 1], topPos[i * 3 + 2]);
        pos.setXYZ(i + N, botPos[i * 3], botPos[i * 3 + 1], botPos[i * 3 + 2]);

        const strain = clamp((materialY - targetY[i]) / 10, 0, 1);
        col.setXYZ(i, 0.9, 0.7 - strain * 0.4, 0.2);
        col.setXYZ(i + N, 0.7, 0.5 - strain * 0.4, 0.1);
    }
    pos.needsUpdate = true;
    col.needsUpdate = true;
    productGeom.computeVertexNormals();
}

// Main logic functions
function setState(s) { state = s; stateT = 0; }

function step(dt) {
    stateT += dt;
    tSim += dt;

    if (state === ST.FEED) {
        uncutMesh.position.x -= speed * dt;
        if (uncutMesh.position.x < station1X + sheetLength / 2) setState(ST.CLAMP);
    }

    if (state === ST.CLAMP) {
        stripperGroup.position.y -= speed * 2 * dt;
        if (stripperGroup.position.y < materialY + 10) setState(ST.CUT);
    }

    if (state === ST.CUT) {
        bladeGroup.position.y -= speed * 2 * dt;
        if (!hasCut && bladeGroup.position.y - 15 < materialY) {
            hasCut = true;
            uncutMesh.visible = false;
            initProduct();
            productMesh.visible = true;
        }
        if (stateT > 0.6) setState(ST.BEND);
    }

    if (state === ST.BEND) {
        vPunchGroup.position.y -= speed * 1.2 * dt;
        simulateProduct(dt);
        updateProductMesh();
        if (70 + vPunchGroup.position.y < baseH + 20) setState(ST.HOLD);
    }

    if (state === ST.HOLD) {
        simulateProduct(dt);
        updateProductMesh();
        if (stateT > 0.4) setState(ST.LIFT);
    }

    if (state === ST.LIFT) {
        vPunchGroup.position.y += speed * 2 * dt;
        stripperGroup.position.y += speed * 2 * dt;
        bladeGroup.position.y += speed * 2 * dt;
        updateProductMesh();
        if (vPunchGroup.position.y >= 0) setState(ST.EJECT);
    }

    if (state === ST.EJECT) {
        productMesh.position.x -= speed * 3 * dt;
        if (stateT > 1.2) {
            cycleCount++;
            resetSim();
        }
    }
}

function resetSim() {
    uncutMesh.position.x = station1X + sheetLength / 2 + 100;
    uncutMesh.visible = true;
    productMesh.visible = false;
    productMesh.position.x = 0;
    stripperGroup.position.y = 60;
    vPunchGroup.position.y = 0;
    bladeGroup.position.y = 50;
    hasCut = false;
    setState(ST.FEED);
}

// Loop
function animate() {
    requestAnimationFrame(animate);
    const dt = 1 / 60;
    if (play) step(dt);

    controls.update();
    renderer.render(scene, camera);

    hud.innerText = `[${STN[state]}] Cycle: ${cycleCount} | Time: ${tSim.toFixed(1)}s`;
}

// UI Setup
window.addEventListener('load', () => {
    loadingOverlay.style.opacity = '0';
    setTimeout(() => loadingOverlay.remove(), 500);
    animate();
});

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

document.getElementById('btn-play').addEventListener('click', () => {
    play = !play;
    document.getElementById('btn-play').innerText = play ? '⏸' : '▶';
});

document.getElementById('btn-reset').addEventListener('click', () => {
    cycleCount = 0;
    tSim = 0;
    resetSim();
});
