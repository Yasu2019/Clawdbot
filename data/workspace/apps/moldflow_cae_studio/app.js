/**
 * Moldflow CAE Studio - client logic
 */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

const API_DEFAULT = "http://127.0.0.1:8776";
const LOCAL_GOLDEN_SPEC = new URL("../../cae_te_workspace/samples/moldflow/golden_plate_case.json", import.meta.url).href;
const LOCAL_CAE_LOG = new URL("../../cae_te_workspace/results/cae_te_log.json", import.meta.url).href;
const LOCAL_SAMPLE_STL = new URL("../../cae_te_workspace/samples/moldflow/cavity_preview.stl", import.meta.url).href;
const LOCAL_SOLVER_LANDSCAPE = new URL("../../moldflow_solver_landscape.json", import.meta.url).href;
const LOCAL_MATURITY = new URL("../growth_dashboard/commercial_benchmark_maturity_latest.json", import.meta.url).href;

const ANALYSIS_DEFS = [
  { id: "warpage", label: "Warpage", color: 0xff6b35, category: "resin_fill_cool" },
  { id: "sink", label: "Sink", color: 0xa855f7, category: "resin_fill_cool" },
  { id: "shrinkage", label: "Shrinkage", color: 0x22c55e, category: "resin_fill_cool" },
  { id: "weld_line", label: "Weld line", color: 0xfacc15, category: "resin_fill_vof" },
  { id: "short_shot", label: "Short shot", color: 0x3b82f6, category: "resin_fill_vof" },
  { id: "flash", label: "Flash", color: 0x06b6d4, category: "resin_fill_pack" },
  { id: "fill", label: "Fill %", color: 0x60a5fa, category: "resin_fill_vof" },
  { id: "air_trap", label: "Air trap", color: 0xef4444, category: "resin_fill_vof" },
];

const state = {
  apiBase: API_DEFAULT,
  bbox: { length: 100, width: 10, height: 2, xmin: 0, ymin: 0, zmin: 0 },
  stepPath: "",
  gates: { inlet1: false, inlet2: true, inlet3: false },
  scene: null,
  camera: null,
  renderer: null,
  controls: null,
  host: null,
  overlayGroup: null,
  baseMesh: null,
  baseGeometry: null,
  goldenSpec: null,
  goldenRecord: null,
  learnedParams: null,
  solverLandscape: null,
};

function $(id) { return document.getElementById(id); }
function setText(id, value) { const el = $(id); if (el) el.textContent = value; }
function setStatus(msg, kind = "warn") {
  const el = $("statusBar");
  if (!el) return;
  el.className = `pill ${kind}`;
  el.innerHTML = `<strong>${kind.toUpperCase()}</strong> ${msg}`;
}
function fmt(v, d = 2) { return Number.isFinite(Number(v)) ? Number(v).toFixed(d) : "--"; }

function buildGateSpec() {
  return {
    version: 1,
    description: "Moldflow CAE Studio export",
    bbox_mm: { length: state.bbox.length, width: state.bbox.width, height: state.bbox.height },
    gates: ["inlet1", "inlet2", "inlet3"].map((patch) => ({
      id: `gate_${patch}`,
      patch,
      role: "injection",
      enabled: !!state.gates[patch],
    })),
    vents: [{ patch: "outlet", role: "outlet" }],
    walls: [{ patch: "walls", role: "mold_wall" }],
  };
}

function readProcessParams() {
  const params = {
    design_mode: $("designMode")?.value || "hybrid",
    inlet_velocity: parseFloat($("inletVelocity").value) || 1,
    pack_pressure_MPa: parseFloat($("packPressure").value) || 0,
    T_melt: parseFloat($("tMelt").value) || 513,
    T_mold: parseFloat($("tMold").value) || 323,
    T_eject: parseFloat($("tEject").value) || 353,
    mesh_mode: $("meshMode").value,
    mesh_size_mm: parseFloat($("meshSize").value) || 3,
    polymer_nu: parseFloat($("polymerNu").value) || 0.01,
    thermal_shrink_alpha: parseFloat($("shrinkAlpha").value) || 1.5e-4,
    physics_category: $("physicsCategory").value,
    viscosity_model: $("viscosityModel")?.value || "wlf",
  };
  const optionalNumbers = {
    clamp_force_kN: "clampForce",
    projected_area_mm2: "projectedArea",
    nominal_wall_mm: "nominalWall",
    assumed_fill_fraction_pct: "assumedFillPct",
    pack_inlet_velocity: "packInletVelocity",
    power_law_nu0: "powerLawNu0",
    power_law_k: "powerLawK",
    power_law_n: "powerLawN",
    shear_rate_1_s: "shearRate",
  };
  for (const [key, id] of Object.entries(optionalNumbers)) {
    const el = $(id);
    if (!el) continue;
    const value = parseFloat(el.value);
    if (Number.isFinite(value) && value > 0) params[key] = value;
  }
  if (params.physics_category === "resin_fill_cool") {
    params.bounded_alpha = true;
    params.closed_cavity = false;
    params.viscosity_model = "const";
  }
  return params;
}

function readAnalysisConfig() {
  const out = {};
  for (const def of ANALYSIS_DEFS) {
    const cb = $(`an_${def.id}`);
    const coef = $(`coef_${def.id}`);
    out[def.id] = {
      enabled: cb ? cb.checked : false,
      coefficient: coef ? parseFloat(coef.value) || 0 : 0,
      category: def.category,
      color: def.color,
      label: def.label,
    };
  }
  return out;
}

function renderLegend() {
  const host = $("legendList");
  if (!host) return;
  const cfg = readAnalysisConfig();
  host.innerHTML = "";
  for (const def of ANALYSIS_DEFS) {
    if (!cfg[def.id].enabled) continue;
    const li = document.createElement("li");
    li.innerHTML = `<span class="swatch" style="background:#${def.color.toString(16).padStart(6, "0")}; width:12px; height:12px; border-radius:3px;"></span>${def.label} x${cfg[def.id].coefficient.toFixed(2)}`;
    host.appendChild(li);
  }
  if (!host.children.length) host.innerHTML = "<li class='muted'>Enable one or more overlays.</li>";
}

function renderAnalysisPanel() {
  const host = $("analysisList");
  host.innerHTML = "";
  for (const def of ANALYSIS_DEFS) {
    const row = document.createElement("div");
    row.className = "analysis-card";
    row.innerHTML = `
      <div class="analysis-title">
        <label class="chip" style="margin:0;">
          <input type="checkbox" id="an_${def.id}" />
          <span style="display:inline-flex; align-items:center; gap:6px;">
            <span class="swatch" style="background:#${def.color.toString(16).padStart(6, "0")}; width:12px; height:12px; border-radius:3px;"></span>
            <strong>${def.label}</strong>
          </span>
        </label>
        <span class="pill">cat: ${def.category}</span>
      </div>
      <div class="coef-wrap">
        <input type="range" id="coef_${def.id}" min="0" max="3" step="0.05" value="1" />
        <span class="coef-value" id="coefval_${def.id}">1.00</span>
      </div>`;
    host.appendChild(row);
    row.querySelector(`#coef_${def.id}`).addEventListener("input", (ev) => {
      row.querySelector(`#coefval_${def.id}`).textContent = parseFloat(ev.target.value).toFixed(2);
      updateOverlays();
    });
    row.querySelector(`#an_${def.id}`).addEventListener("change", updateOverlays);
  }
  renderLegend();
}

function disposeObject(obj) {
  if (!obj) return;
  obj.traverse((node) => {
    if (node.geometry) node.geometry.dispose();
    if (node.material) {
      const mats = Array.isArray(node.material) ? node.material : [node.material];
      mats.forEach((m) => m && m.dispose && m.dispose());
    }
  });
}

function cloneBaseMaterial(opts = {}) {
  return new THREE.MeshPhongMaterial({
    color: 0x94a3b8,
    transparent: true,
    opacity: 0.28,
    side: THREE.DoubleSide,
    depthWrite: false,
    ...opts,
  });
}

function cloneMeshFromBase(material) {
  if (!state.baseGeometry) return null;
  return new THREE.Mesh(state.baseGeometry.clone(), material);
}

function updateOverlays() {
  if (!state.scene || !state.baseGeometry) return;
  if (state.overlayGroup) {
    state.scene.remove(state.overlayGroup);
    disposeObject(state.overlayGroup);
  }
  state.overlayGroup = new THREE.Group();
  state.scene.add(state.overlayGroup);
  const cfg = readAnalysisConfig();
  const lx = state.bbox.length || 1;
  const ly = state.bbox.width || 1;
  const lz = state.bbox.height || 1;
  const cx = lx * 0.5;
  const cy = ly * 0.5;
  const cz = lz * 0.5;

  if (cfg.warpage.enabled && cfg.warpage.coefficient > 0) {
    const amp = 0.08 * cfg.warpage.coefficient * lz;
    const geom = state.baseGeometry.clone();
    const pos = geom.attributes.position;
    for (let i = 0; i < pos.count; i += 1) {
      const x = pos.getX(i);
      const y = pos.getY(i);
      const z = pos.getZ(i);
      const u = (x - cx) / lx;
      const v = (y - cy) / ly;
      pos.setZ(i, z + amp * (u * u + v * v));
    }
    geom.computeVertexNormals();
    state.overlayGroup.add(new THREE.Mesh(geom, new THREE.MeshPhongMaterial({ color: 0xff6b35, transparent: true, opacity: 0.55, side: THREE.DoubleSide })));
  }
  if (cfg.shrinkage.enabled && cfg.shrinkage.coefficient > 0) {
    const mesh = cloneMeshFromBase(new THREE.MeshPhongMaterial({ color: 0x22c55e, transparent: true, opacity: 0.4 }));
    if (mesh) {
      const s = 1 - 0.015 * cfg.shrinkage.coefficient;
      mesh.scale.set(s, s, s);
      state.overlayGroup.add(mesh);
    }
  }
  if (cfg.sink.enabled && cfg.sink.coefficient > 0) {
    const geom = state.baseGeometry.clone();
    const pos = geom.attributes.position;
    const depth = 0.12 * cfg.sink.coefficient * lz;
    for (let i = 0; i < pos.count; i += 1) {
      const x = pos.getX(i);
      const y = pos.getY(i);
      const z = pos.getZ(i);
      const dx = (x - cx) / Math.max(lx * 0.2, 1);
      const dy = (y - 0) / Math.max(ly * 0.15, 1);
      const d = Math.exp(-(dx * dx + dy * dy));
      if (y < ly * 0.2) pos.setZ(i, z - depth * d);
    }
    geom.computeVertexNormals();
    state.overlayGroup.add(new THREE.Mesh(geom, new THREE.MeshPhongMaterial({ color: 0xa855f7, transparent: true, opacity: 0.6, side: THREE.DoubleSide })));
  }
  if (cfg.short_shot.enabled && cfg.short_shot.coefficient > 0) {
    const fill = Math.min(0.95, 0.35 + 0.2 * cfg.short_shot.coefficient);
    const geom = state.baseGeometry.clone();
    const pos = geom.attributes.position;
    for (let i = 0; i < pos.count; i += 1) {
      if (pos.getX(i) > lx * fill) pos.setX(i, lx * fill * 0.98);
    }
    geom.computeVertexNormals();
    state.overlayGroup.add(new THREE.Mesh(geom, new THREE.MeshPhongMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.5 })));
  }
  if (cfg.flash.enabled && cfg.flash.coefficient > 0) {
    const geom = state.baseGeometry.clone();
    const pos = geom.attributes.position;
    const ext = 0.04 * cfg.flash.coefficient * Math.min(lx, ly, lz);
    for (let i = 0; i < pos.count; i += 1) {
      const x = pos.getX(i);
      const y = pos.getY(i);
      if (x > lx * 0.92) pos.setX(i, x + ext);
      if (y > ly * 0.92) pos.setY(i, y + ext);
    }
    geom.computeVertexNormals();
    state.overlayGroup.add(new THREE.Mesh(geom, new THREE.MeshPhongMaterial({ color: 0x06b6d4, transparent: true, opacity: 0.45 })));
  }
  if (cfg.weld_line.enabled && cfg.weld_line.coefficient > 0) {
    const pts = [];
    for (let i = 0; i <= 12; i += 1) {
      const t = i / 12;
      pts.push(new THREE.Vector3(lx * t, cy, cz));
      pts.push(new THREE.Vector3(cx, ly * t, cz));
    }
    state.overlayGroup.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: 0xfacc15, transparent: true, opacity: 0.5 + 0.3 * cfg.weld_line.coefficient })));
  }
  if (cfg.air_trap.enabled && cfg.air_trap.coefficient > 0) {
    const sph = new THREE.Mesh(new THREE.SphereGeometry(Math.min(lx, ly, lz) * 0.12 * cfg.air_trap.coefficient, 16, 16), new THREE.MeshPhongMaterial({ color: 0xef4444, transparent: true, opacity: 0.65 }));
    sph.position.set(lx * 0.75, ly * 0.6, cz);
    state.overlayGroup.add(sph);
  }
  renderLegend();
}

function fitCamera() {
  if (!state.baseMesh || !state.camera || !state.controls) return;
  const box = new THREE.Box3().setFromObject(state.baseMesh);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z, 1);
  state.camera.position.set(center.x + maxDim * 1.4, center.y + maxDim * 1.1, center.z + maxDim * 1.3);
  state.controls.target.copy(center);
  state.controls.update();
}

async function loadStl(url) {
  const loader = new STLLoader();
  return new Promise((resolve, reject) => loader.load(url, resolve, undefined, reject));
}

async function tryFetchJson(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function fetchJsonWithFallback(apiUrl, fallbackUrl) {
  try {
    return await tryFetchJson(apiUrl);
  } catch (apiErr) {
    try {
      return await tryFetchJson(fallbackUrl);
    } catch (fallbackErr) {
      throw new Error(`${apiErr.message}; fallback failed: ${fallbackErr.message}`);
    }
  }
}

function collectGoldenResults(trials, variantNames) {
  const out = {};
  for (const name of variantNames) out[name] = [];
  for (const trial of trials || []) {
    const gc = trial?.params?.golden_case;
    if (!Object.prototype.hasOwnProperty.call(out, gc)) continue;
    const defects = trial?.defects_detected || {};
    const fillTime = Number(defects.fill_time_s);
    const fillPct = Number(defects.fill_fraction_pct);
    if (!Number.isFinite(fillTime) || !Number.isFinite(fillPct)) continue;
    out[gc].push({
      trial_id: trial.id ?? null,
      timestamp: trial.timestamp ?? null,
      fill_time_s: fillTime,
      fill_pct: fillPct,
      verdict: trial.verdict ?? null,
      mass_balance_err_pct: defects.mass_balance_err_pct === undefined || defects.mass_balance_err_pct === null ? null : Number(defects.mass_balance_err_pct),
    });
  }
  return out;
}

function spreadPct(values) {
  if (!values || values.length < 2) return null;
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  if (!(lo > 0)) return null;
  return Math.round(((hi - lo) / lo) * 1000) / 10;
}

function evaluateGolden(results, spec) {
  const exp = spec?.expectations || {};
  const [fillLo, fillHi] = exp.fill_pct_range || [90.0, 110.0];
  const reproTol = Number(exp.reproducibility_tol_pct ?? 10.0);
  const scal = exp.scaling || {};
  const ratioExp = Number(scal.ratio_expected ?? 1.25);
  const ratioTol = Number(scal.tol_pct ?? 15.0);
  const checks = [];
  const perVariant = {};

  for (const [name, rows] of Object.entries(results || {})) {
    const valid = rows.filter((r) => r.fill_pct >= fillLo && r.fill_pct <= fillHi);
    const invalid = rows.length - valid.length;
    const times = valid.map((r) => r.fill_time_s);
    const spread = spreadPct(times.slice(-5));
    perVariant[name] = {
      n_total: rows.length,
      n_valid: valid.length,
      n_fill_out_of_range: invalid,
      fill_time_last: times.length ? times[times.length - 1] : null,
      fill_time_mean_recent: times.length ? Math.round((times.slice(-5).reduce((a, b) => a + b, 0) / Math.min(5, times.length)) * 100000) / 100000 : null,
      repro_spread_pct: spread,
      mass_balance_err_last: valid.length ? valid[valid.length - 1].mass_balance_err_pct : null,
    };
    if (rows.length) {
      checks.push({
        check: "E1_fill_physical",
        variant: name,
        ok: invalid === 0,
        note: invalid === 0 ? `All ${rows.length} rows are within ${fillLo}-${fillHi}%` : `${invalid}/${rows.length} rows outside ${fillLo}-${fillHi}%`,
      });
    }
    if (spread !== null) {
      checks.push({
        check: "E2_reproducibility",
        variant: name,
        ok: spread <= reproTol,
        note: `Recent spread ${spread}% (limit ${reproTol}%)`,
      });
    }
  }

  const names = Object.keys(results || {});
  let ratio = null;
  if (names.length >= 2) {
    const a = perVariant[names[0]]?.fill_time_mean_recent;
    const b = perVariant[names[1]]?.fill_time_mean_recent;
    if (Number.isFinite(a) && Number.isFinite(b) && a > 0) {
      ratio = Math.round((b / a) * 10000) / 10000;
      const errPct = Math.round((Math.abs(ratio - ratioExp) / ratioExp) * 1000) / 10;
      checks.push({
        check: "E3_velocity_scaling",
        ok: errPct <= ratioTol,
        note: `t ratio ${ratio} vs ${ratioExp} (error ${errPct}%)`,
      });
    }
  }

  const nResults = Object.values(results || {}).reduce((acc, rows) => acc + rows.length, 0);
  const allOk = checks.length ? checks.every((c) => c.ok) : null;
  return {
    checked_at: new Date().toISOString(),
    golden: spec?.name ?? null,
    n_results: nResults,
    per_variant: perVariant,
    scaling_ratio: ratio,
    checks,
    verdict: nResults === 0 ? "NO_DATA" : allOk ? "PASS" : allOk === null ? "PENDING" : "FAIL",
  };
}

function renderGoldenPanel() {
  const spec = state.goldenSpec;
  const record = state.goldenRecord;
  if (!spec || !record) return;
  const verdict = record.verdict || "PENDING";
  const verdictClass = verdict === "PASS" ? "pass" : verdict === "FAIL" ? "fail" : "pending";
  const verdictLabel = verdict === "PASS" ? "PASS" : verdict === "FAIL" ? "FAIL" : verdict === "NO_DATA" ? "NO DATA" : "PENDING";
  $("goldenVerdict").className = `verdict ${verdictClass}`;
  $("goldenVerdict").textContent = verdictLabel;
  setText("goldenMeta", `${spec.name || "golden_plate_case"} | checked ${new Date(record.checked_at).toLocaleString()}`);
  setText("goldenCount", `${record.n_results} results`);
  const fillRange = spec.expectations?.fill_pct_range || [90, 110];
  const ratio = spec.expectations?.scaling?.ratio_expected ?? 1.25;
  const ratioTol = spec.expectations?.scaling?.tol_pct ?? 15;
  const reproTol = spec.expectations?.reproducibility_tol_pct ?? 10;
  const statValues = [`${fillRange[0]}-${fillRange[1]}%`, `<= ${reproTol}%`, `${ratio} +/- ${ratioTol}%`, spec.schedule?.inject_every_n_cycles ? `every ${spec.schedule.inject_every_n_cycles} cycles` : "--"];
  $("goldenStats").querySelectorAll(".stat .v").forEach((el, idx) => { el.textContent = statValues[idx] || "--"; });

  const checksHost = $("goldenChecks");
  checksHost.innerHTML = "";
  for (const check of record.checks || []) {
    const card = document.createElement("div");
    card.className = "check-card";
    card.innerHTML = `<div style="display:flex; justify-content:space-between; gap:10px; align-items:center;"><strong>${check.check}${check.variant ? ` [${check.variant}]` : ""}</strong><span class="status-tag ${check.ok ? "status-ok" : "status-fail"}">${check.ok ? "OK" : "NG"}</span></div><div class="note">${check.note}</div>`;
    checksHost.appendChild(card);
  }
  if (!(record.checks || []).length) checksHost.innerHTML = "<div class='check-card'><div class='note'>No checks available.</div></div>";

  const variantsHost = $("variantCards");
  variantsHost.innerHTML = "";
  for (const [name, data] of Object.entries(record.per_variant || {})) {
    const card = document.createElement("div");
    card.className = "variant-card";
    card.innerHTML = `<div style="display:flex; justify-content:space-between; gap:10px; align-items:center;"><strong>${name}</strong><span class="pill">${data.n_valid}/${data.n_total} valid</span></div><table class="table"><tr><th>Fill out</th><td>${data.n_fill_out_of_range}</td></tr><tr><th>Last fill</th><td>${fmt(data.fill_time_last, 5)}</td></tr><tr><th>Recent mean</th><td>${fmt(data.fill_time_mean_recent, 5)}</td></tr><tr><th>Spread</th><td>${fmt(data.repro_spread_pct, 1)}%</td></tr><tr><th>Mass err</th><td>${fmt(data.mass_balance_err_last, 3)}%</td></tr></table>`;
    variantsHost.appendChild(card);
  }
  if (!(Object.keys(record.per_variant || {}).length)) variantsHost.innerHTML = "<div class='variant-card'><div class='note'>No variant rows found.</div></div>";
}

function repairHelpCopy() {
  const copy = [
    ["Scene / API", "STEPをアップロードして、ゲート、材料、成形条件を同じ画面で調整します。APIが停止している場合でも、サンプルSTLで表示確認を継続できます。"],
    ["Gates", "下端側の入口面をクリックするとゲートを切り替えられます。Center / Dual / Triple のプリセットも使えます。"],
    ["Export", "`Export Job` で gate_spec と process パラメータを `data/cae_te_workspace/jobs/moldflow_studio/` に書き出します。"],
  ];
  document.querySelectorAll(".section").forEach((section) => {
    const title = section.querySelector("h2")?.textContent?.trim();
    const replacement = copy.find(([name]) => name === title)?.[1];
    const note = section.querySelector(".note");
    if (replacement && note) note.textContent = replacement;
  });
}

function applyClearHelpCopy() {
  const copy = [
    ["Scene / API", "Upload a STEP file, then tune gates, material, and molding conditions in one cockpit. If the API is offline, the sample STL keeps the viewer usable."],
    ["Gates", "Click the lower inlet edge to toggle gates. Use 1 gate, 2 gates, or 3 gates presets when you want a fast setup."],
    ["Export", "Export Job writes gate_spec and process parameters under data/cae_te_workspace/jobs/moldflow_studio/."],
  ];
  document.querySelectorAll(".section").forEach((section) => {
    const title = section.querySelector("h2")?.textContent?.trim();
    const replacement = copy.find(([name]) => name === title)?.[1];
    const note = section.querySelector(".note");
    if (replacement && note) note.textContent = replacement;
  });
}

function ensureAccuracyInputs() {
  if ($("accuracyInputBlock")) return;
  const categoryEl = $("physicsCategory");
  if (!categoryEl) return;
  const block = document.createElement("div");
  block.id = "accuracyInputBlock";
  block.innerHTML = `
    <label class="field">OpenFOAM viscosity model</label>
    <select id="viscosityModel">
      <option value="wlf">WLF / Cross-WLF proxy (thermo)</option>
      <option value="const">Constant nu (baseline)</option>
      <option value="powerLaw">Power-law non-Newtonian</option>
      <option value="CrossPowerLaw">CrossPowerLaw candidate</option>
      <option value="BirdCarreau">Bird-Carreau candidate</option>
    </select>
    <p class="note">OpenFOAM has non-Newtonian rheology models; CrossPowerLaw is not the same as Moldflow Cross-WLF.</p>
    <div class="grid-2">
      <div>
        <label class="field">Clamp force kN</label>
        <input type="number" id="clampForce" value="800" step="10" />
      </div>
      <div>
        <label class="field">Projected area mm2</label>
        <input type="number" id="projectedArea" value="" placeholder="auto length x width" step="10" />
      </div>
    </div>
    <div class="grid-2">
      <div>
        <label class="field">Nominal wall mm</label>
        <input type="number" id="nominalWall" value="2" step="0.1" />
      </div>
      <div>
        <label class="field">Assumed fill %</label>
        <input type="number" id="assumedFillPct" value="95" min="0" max="110" step="1" />
      </div>
    </div>
    <div class="grid-2">
      <div>
        <label class="field">Power-law nu0</label>
        <input type="number" id="powerLawNu0" value="0.01" step="0.001" />
      </div>
      <div>
        <label class="field">Power-law k</label>
        <input type="number" id="powerLawK" value="0.001" step="0.0001" />
      </div>
    </div>
    <div class="grid-2">
      <div>
        <label class="field">Power-law n</label>
        <input type="number" id="powerLawN" value="0.6" min="0.1" max="1.2" step="0.01" />
      </div>
      <div>
        <label class="field">Shear rate 1/s</label>
        <input type="number" id="shearRate" value="1000" min="1" step="100" />
      </div>
    </div>
    <div>
      <label class="field">Pack inlet velocity</label>
      <input type="number" id="packInletVelocity" value="0.05" min="0.001" step="0.005" />
    </div>`;
  categoryEl.insertAdjacentElement("afterend", block);
}

function ensureLearningPanel() {
  if ($("learningPanel")) return;
  const exportSection = [...document.querySelectorAll(".section")]
    .find((section) => section.querySelector("h2")?.textContent?.trim() === "Export");
  if (!exportSection) return;
  const panel = document.createElement("div");
  panel.className = "section";
  panel.id = "learningPanel";
  panel.innerHTML = `
    <h2>Fable5 Fusion</h2>
    <div class="golden-banner">
      <div>
        <div class="verdict pending" id="learnedVerdict">NOT LOADED</div>
        <div class="note" id="learnedSummary">Load resin-fill suggestions from Fable5 acceptance sampling.</div>
      </div>
      <div class="pill" id="learnedPool">pool --</div>
    </div>
    <pre id="learnedOut">{}</pre>
    <div class="tool-row" style="margin-top:10px;">
      <button type="button" class="btn" id="btnLoadLearned">Load Learned Params</button>
      <button type="button" class="btn good" id="btnApplyLearned">Apply Learned Params</button>
    </div>`;
  exportSection.parentNode.insertBefore(panel, exportSection);
}

function ensureSolverLandscapePanel() {
  if ($("solverLandscapePanel")) return;
  const exportSection = [...document.querySelectorAll(".section")]
    .find((section) => section.querySelector("h2")?.textContent?.trim() === "Export");
  if (!exportSection) return;
  const panel = document.createElement("div");
  panel.className = "section";
  panel.id = "solverLandscapePanel";
  panel.innerHTML = `
    <h2>Solver Benchmark</h2>
    <div class="golden-banner">
      <div>
        <div class="verdict pending" id="solverVerdict">NOT LOADED</div>
        <div class="note" id="solverSummary">Load commercial/OSS solver landscape and benchmark targets.</div>
      </div>
      <div class="pill" id="solverCount">0 solvers</div>
    </div>
    <div id="solverList"></div>
    <div id="solverBacklog" class="note"></div>
    <div class="tool-row" style="margin-top:10px;">
      <button type="button" class="btn" id="btnLoadSolverLandscape">Load Solver Map</button>
      <button type="button" class="btn good" id="btnApplySafeThermal">Apply Safe Thermal Proxy</button>
    </div>`;
  exportSection.parentNode.insertBefore(panel, exportSection);
}

function ensureReadinessPanel() {
  if ($("readinessPanel")) return;
  const exportSection = [...document.querySelectorAll(".section")]
    .find((section) => section.querySelector("h2")?.textContent?.trim() === "Export");
  if (!exportSection) return;
  const panel = document.createElement("div");
  panel.className = "section";
  panel.id = "readinessPanel";
  panel.innerHTML = `
    <h2>Run Readiness</h2>
    <div class="golden-banner">
      <div>
        <div class="verdict pending" id="readinessVerdict">Checking...</div>
        <div class="note" id="readinessSummary">Preflight checks before exporting an OpenFOAM job.</div>
      </div>
      <div class="pill" id="readinessScore">-- / 100</div>
    </div>
    <div id="readinessChecks"></div>
    <div class="tool-row" style="margin-top:10px;">
      <button type="button" class="btn" id="btnRefreshReadiness">Refresh Readiness</button>
      <button type="button" class="btn" id="btnCopyTrialCommand">Copy Trial Command</button>
    </div>`;
  exportSection.parentNode.insertBefore(panel, exportSection);
  $("btnRefreshReadiness").addEventListener("click", updateReadinessPanel);
  $("btnCopyTrialCommand").addEventListener("click", copyTrialCommand);
}

function renderSolverLandscape(data) {
  ensureSolverLandscapePanel();
  state.solverLandscape = data;
  const solvers = data?.solvers || [];
  const internal = data?.current_internal_proxy || {};
  $("solverVerdict").className = `verdict ${solvers.length ? "pass" : "pending"}`;
  $("solverVerdict").textContent = solvers.length ? "BENCHMARKS" : "NO DATA";
  $("solverCount").textContent = `${solvers.length} solvers`;
  $("solverSummary").textContent = internal.latest_verified_proxy_run
    ? `Internal proxy: ${internal.latest_verified_proxy_run.trial_id} | alpha_max=${internal.latest_verified_proxy_run.alpha_max}, T=${internal.latest_verified_proxy_run.T_min_K}-${internal.latest_verified_proxy_run.T_max_K} K`
    : "Commercial solvers exist; OpenFOAM remains our internal proxy foundation.";
  const host = $("solverList");
  host.innerHTML = solvers.map((solver) => {
    const cls = solver.access_class === "direct_free" ? "status-ok" : "status-fail";
    const tag = solver.access_class === "direct_free" ? "FREE" : "BENCH";
    return `
      <div class="check-card">
        <div style="display:flex; justify-content:space-between; gap:10px; align-items:center;">
          <strong>${solver.name}</strong>
          <span class="status-tag ${cls}">${tag}</span>
        </div>
        <div class="note">${solver.kind} | ${solver.access_class} | ${solver.how_we_use_it || ""}</div>
      </div>`;
  }).join("");
  const backlog = data?.implementation_backlog || [];
  $("solverBacklog").textContent = backlog.length
    ? `Next: ${backlog.slice(0, 3).map((item) => item.id).join(", ")}`
    : "";
}

async function loadSolverLandscape() {
  const data = await fetchJsonWithFallback(`${state.apiBase}/api/solver-landscape`, LOCAL_SOLVER_LANDSCAPE);
  renderSolverLandscape(data);
  setStatus("Solver benchmark map loaded", "ok");
}

function ensureMaturityPanel() {
  if ($("maturityPanel")) return;
  const exportSection = [...document.querySelectorAll(".section")]
    .find((section) => section.querySelector("h2")?.textContent?.trim() === "Export");
  if (!exportSection) return;
  const panel = document.createElement("div");
  panel.className = "section";
  panel.id = "maturityPanel";
  panel.innerHTML = `
    <h2>Maturity & Golden Trend</h2>
    <div class="golden-banner">
      <div>
        <div class="verdict pending" id="maturityVerdict">NOT LOADED</div>
        <div class="note" id="maturitySummary">L0-L10 maturity (commercial_benchmark_maturity) + golden case error trend.</div>
      </div>
      <div class="pill" id="maturityAge">--</div>
    </div>
    <div id="maturityBars"></div>
    <div id="goldenTrend" class="note" style="margin-top:8px;"></div>
    <div class="tool-row" style="margin-top:10px;">
      <button type="button" class="btn" id="btnLoadMaturity">Reload Maturity</button>
    </div>`;
  exportSection.parentNode.insertBefore(panel, exportSection);
  $("btnLoadMaturity").addEventListener("click", () => loadMaturity().catch((err) => setStatus(String(err), "warn")));
}

function normalizeMaturity(data) {
  if (!data) return null;
  if (data.product !== undefined || data.available !== undefined) return data;
  const product = (data.matrix || []).find((row) => String(row.product_id || "").toUpperCase().includes("MOLDFLOW")) || null;
  let ageH = null;
  if (data.assessed_at) {
    const t = Date.parse(data.assessed_at);
    if (Number.isFinite(t)) ageH = (Date.now() - t) / 3600000;
  }
  return { available: !!product, product, assessed_at: data.assessed_at, age_hours: ageH, stale: ageH != null && ageH > 26, source: "local snapshot" };
}

function maturitySpark(values) {
  if (!values || values.length < 2) return "";
  const w = 220, h = 30;
  const max = Math.max(...values, 1e-9);
  const y = (v) => h - 2 - (v / max) * (h - 6);
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${y(v).toFixed(1)}`).join(" ");
  return `<svg width="${w}" height="${h}" style="vertical-align:middle"><polyline points="${pts}" fill="none" stroke="var(--accent)" stroke-width="1.5"/></svg>`;
}

function renderMaturity(data) {
  ensureMaturityPanel();
  const norm = normalizeMaturity(data);
  const product = norm?.product;
  if (!$("maturityVerdict")) return;
  $("maturityVerdict").className = `verdict ${product ? "pass" : "pending"}`;
  $("maturityVerdict").textContent = product ? (product.product_label || product.product_id) : "NO DATA";
  $("maturityAge").textContent = norm?.age_hours != null
    ? `assessed ${fmt(norm.age_hours, 1)}h ago${norm.stale ? " (STALE>26h)" : ""}`
    : "--";
  $("maturitySummary").textContent = product ? `source: ${norm.source}` : (norm?.note || "maturity snapshot not found");
  $("maturityBars").innerHTML = (product?.categories || []).map((cat) => {
    const pct = Math.min(100, Math.max(0, Number(cat.progress_pct) || 0));
    return `
      <div class="check-card">
        <div style="display:flex; justify-content:space-between; gap:10px; align-items:center;">
          <strong>${cat.label || cat.id}</strong>
          <span class="pill">${cat.current_label || "--"}${cat.current_stage ? " | " + cat.current_stage : ""}</span>
        </div>
        <div style="height:6px; border-radius:4px; background:rgba(148,163,184,.2); margin-top:6px;">
          <div style="height:6px; border-radius:4px; width:${pct}%; background:var(--accent-2);"></div>
        </div>
        <div class="note">${fmt(pct, 0)}% | ${cat.l10_target || ""}</div>
      </div>`;
  }).join("");
}

function renderGoldenTrend(data) {
  const host = $("goldenTrend");
  if (!host) return;
  const records = data?.records || [];
  if (!records.length) {
    host.textContent = data?.note || "golden error log: 0 records";
    return;
  }
  const values = records.map((r) => {
    const flat = r.max_err_pct ?? r.err_pct ?? r.error_pct;
    if (Number.isFinite(Number(flat))) return Number(flat);
    const pv = r.per_variant || {};
    const errs = Object.values(pv).map((v) => Number(v?.err_pct ?? v?.max_err_pct)).filter(Number.isFinite);
    return errs.length ? Math.max(...errs) : NaN;
  }).filter(Number.isFinite);
  host.innerHTML = values.length
    ? `Golden error trend (${values.length} pts, last=${fmt(values[values.length - 1], 2)}%): ${maturitySpark(values)}`
    : `Golden records: ${records.length} (numeric error field not found)`;
}

async function loadMaturity() {
  const data = await fetchJsonWithFallback(`${state.apiBase}/api/maturity`, LOCAL_MATURITY);
  renderMaturity(data);
  try {
    renderGoldenTrend(await tryFetchJson(`${state.apiBase}/api/golden-error-trend?limit=60`));
  } catch (err) {
    const host = $("goldenTrend");
    if (host) host.textContent = `golden trend: API not reachable (${err.message})`;
  }
}

function ensureGateAdvisorPanel() {
  if ($("gateAdvisorPanel")) return;
  const exportSection = [...document.querySelectorAll(".section")]
    .find((section) => section.querySelector("h2")?.textContent?.trim() === "Export");
  if (!exportSection) return;
  const panel = document.createElement("div");
  panel.className = "section";
  panel.id = "gateAdvisorPanel";
  panel.innerHTML = `
    <h2>Gate Advisor</h2>
    <div class="golden-banner">
      <div>
        <div class="verdict pending" id="gateAdvisorVerdict">NOT RUN</div>
        <div class="note" id="gateAdvisorNote">平板近似の決定論スクリーニング(7候補)。Moldflow BGA相当ではない — 最終判断は人間。</div>
      </div>
      <div class="pill" id="gateAdvisorBest">--</div>
    </div>
    <div id="gateAdvisorList"></div>
    <div class="tool-row" style="margin-top:10px;">
      <button type="button" class="btn" id="btnAdviseGates">Advise Gates</button>
    </div>`;
  exportSection.parentNode.insertBefore(panel, exportSection);
  $("btnAdviseGates").addEventListener("click", () => adviseGates().catch((err) => setStatus(String(err), "warn")));
}

function applyAdvisedGates(gates) {
  for (const patch of ["inlet1", "inlet2", "inlet3"]) state.gates[patch] = gates.includes(patch);
  syncGateUi();
  updateOverlays();
  updateReadinessPanel();
  setStatus(`Gate advisor applied: ${gates.join(" + ")}`, "ok");
}

function renderGateAdvice(data) {
  ensureGateAdvisorPanel();
  const cands = data?.candidates || [];
  $("gateAdvisorVerdict").className = `verdict ${cands.length ? "pass" : "pending"}`;
  $("gateAdvisorVerdict").textContent = cands.length ? "RANKED" : "NO DATA";
  $("gateAdvisorBest").textContent = data?.best ? `best: ${data.best.join("+")}` : "--";
  $("gateAdvisorNote").textContent = (data?.assumptions || []).join(" / ") || "";
  $("gateAdvisorList").innerHTML = cands.map((c, idx) => {
    const riskTag = c.short_shot_risk
      ? '<span class="status-tag status-fail">SHORT SHOT RISK</span>'
      : '<span class="status-tag status-ok">FILL OK</span>';
    return `
      <div class="check-card">
        <div style="display:flex; justify-content:space-between; gap:10px; align-items:center;">
          <strong>#${idx + 1} ${c.gates.join(" + ")}</strong>
          <span>${riskTag} <span class="pill">score ${fmt(c.score, 1)}</span></span>
        </div>
        <div class="note">maxL ${fmt(c.max_flow_length_mm, 1)}mm | L/t ${fmt(c.flow_ratio_Lt, 1)}/${fmt(c.flow_ratio_limit, 0)} (margin ${fmt(c.fill_margin_pct, 1)}%) | weld ${c.weld_count}${c.weld_lines.length ? " @x=" + c.weld_lines.map((w) => fmt(w.x_mm, 0)).join(",") : ""} | balance cv ${fmt(c.balance_cv, 2)}</div>
        <div class="tool-row" style="margin-top:6px;">
          <button type="button" class="btn" data-gates="${c.gates.join(",")}">Apply</button>
        </div>
      </div>`;
  }).join("");
  $("gateAdvisorList").querySelectorAll("button[data-gates]").forEach((btn) => {
    btn.addEventListener("click", () => applyAdvisedGates(btn.dataset.gates.split(",")));
  });
}

async function adviseGates() {
  const res = await fetch(`${state.apiBase}/api/gate-advice`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      bbox_mm: { length: state.bbox.length, width: state.bbox.width, height: state.bbox.height },
      material_id: $("materialPreset")?.value || null,
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  renderGateAdvice(await res.json());
  setStatus("Gate advice ranked (deterministic screening)", "ok");
}

function applySafeThermalProxyDefaults() {
  const defaults = state.solverLandscape?.current_internal_proxy?.safe_demo_defaults || {
    bounded_alpha: true,
    viscosity_model: "const",
    closed_cavity: false,
  };
  const physics = $("physicsCategory");
  if (physics) physics.value = "resin_fill_cool";
  const viscosity = $("viscosityModel");
  if (viscosity && defaults.viscosity_model) viscosity.value = defaults.viscosity_model;
  updateReadinessPanel();
  setStatus("Safe thermal proxy defaults applied (cool + const viscosity + bounded alpha)", "ok");
}

function selectedGateCount() {
  return Object.values(state.gates).filter(Boolean).length;
}

function readinessRows() {
  const process = readProcessParams();
  const gateCount = selectedGateCount();
  const goldenVerdict = state.goldenRecord?.verdict || "UNKNOWN";
  const stats = $("defectPreviewStats")?.querySelectorAll(".stat .v") || [];
  const sinkRisk = Number(stats[0]?.textContent);
  const flashRisk = Number(stats[1]?.textContent);
  return [
    { label: "API endpoint", ok: state.apiBase.startsWith("http"), note: state.apiBase },
    { label: "3D preview", ok: !!state.baseGeometry, note: state.baseGeometry ? "STL loaded" : "Load mesh first" },
    { label: "Gate selection", ok: gateCount > 0, note: `${gateCount} active gate(s)` },
    { label: "BBox", ok: state.bbox.length > 0 && state.bbox.width > 0 && state.bbox.height > 0, note: `${fmt(state.bbox.length, 1)} x ${fmt(state.bbox.width, 1)} x ${fmt(state.bbox.height, 1)} mm` },
    { label: "Process values", ok: process.inlet_velocity > 0 && process.polymer_nu > 0 && process.T_melt > process.T_mold, note: `U=${fmt(process.inlet_velocity, 2)}, nu=${fmt(process.polymer_nu, 4)}, dT=${fmt(process.T_melt - process.T_mold, 0)} K, rheology=${process.viscosity_model}` },
    { label: "Thermal proxy guard", ok: process.physics_category !== "resin_fill_cool" || (process.bounded_alpha === true && process.closed_cavity === false && process.viscosity_model === "const"), note: process.physics_category === "resin_fill_cool" ? `bounded_alpha=${process.bounded_alpha}, closed_cavity=${process.closed_cavity}, rheology=${process.viscosity_model}` : "Not a cooling run" },
    { label: "Golden case", ok: ["PASS", "NO_DATA", "PENDING"].includes(goldenVerdict), warn: goldenVerdict !== "PASS", note: goldenVerdict },
    { label: "Defect KPI", ok: !Number.isFinite(flashRisk) || flashRisk < 0.8, warn: Number.isFinite(flashRisk) && (flashRisk >= 0.5 || sinkRisk >= 0.5), note: Number.isFinite(flashRisk) ? `sink=${fmt(sinkRisk, 3)}, flash=${fmt(flashRisk, 3)}` : "Preview KPI not run yet" },
  ];
}

function updateReadinessPanel() {
  ensureReadinessPanel();
  const host = $("readinessChecks");
  if (!host) return;
  const rows = readinessRows();
  const hardPass = rows.filter((row) => row.ok).length;
  const warnCount = rows.filter((row) => row.warn).length;
  const score = Math.max(0, Math.round((hardPass / rows.length) * 100) - warnCount * 8);
  const verdict = score >= 85 && warnCount === 0 ? "READY" : score >= 70 ? "REVIEW" : "BLOCKED";
  $("readinessVerdict").className = `verdict ${verdict === "READY" ? "pass" : verdict === "BLOCKED" ? "fail" : "pending"}`;
  $("readinessVerdict").textContent = verdict;
  $("readinessScore").textContent = `${score} / 100`;
  setText("readinessSummary", verdict === "READY" ? "Job export looks safe." : "Review warnings before running production-scale trials.");
  host.innerHTML = rows.map((row) => {
    const cls = row.ok && !row.warn ? "status-ok" : "status-fail";
    const tag = row.ok && !row.warn ? "OK" : row.ok ? "WARN" : "NG";
    return `<div class="check-card"><div style="display:flex; justify-content:space-between; gap:10px; align-items:center;"><strong>${row.label}</strong><span class="status-tag ${cls}">${tag}</span></div><div class="note">${row.note}</div></div>`;
  }).join("");
}

function trialCommandText() {
  const process = readProcessParams();
  const category = process.physics_category || "resin_fill_cad";
  const jobId = $("jobId").value.trim() || "studio_manual_trial";
  const params = {
    gate_spec_path: `data/cae_te_workspace/samples/moldflow/gate_spec_${jobId}.json`,
    step_path: state.stepPath || "",
  };
  return `python scripts/cae_te_remote_trial.py --category ${category} --trial-id ${jobId} --params-json '${JSON.stringify(params)}'`;
}

async function copyTrialCommand() {
  const text = trialCommandText();
  try {
    await navigator.clipboard.writeText(text);
    setStatus("Trial command copied", "ok");
  } catch {
    $("jobOut").textContent = text;
    setStatus("Clipboard blocked; command written to Export box", "warn");
  }
}

function applyParamsToInputs(params = {}) {
  const mapping = {
    inlet_velocity: "inletVelocity",
    pack_pressure_MPa: "packPressure",
    polymer_nu: "polymerNu",
    pack_inlet_velocity: "packInletVelocity",
    viscosity_model: "viscosityModel",
    power_law_nu0: "powerLawNu0",
    power_law_k: "powerLawK",
    power_law_n: "powerLawN",
    shear_rate_1_s: "shearRate",
  };
  for (const [key, id] of Object.entries(mapping)) {
    const el = $(id);
    if (!el || params[key] === undefined || params[key] === null) continue;
    el.value = params[key];
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }
  updateReadinessPanel();
}

async function loadLearnedParams({ apply = false } = {}) {
  const res = await fetch(`${state.apiBase}/api/learned-params`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "learned params failed");
  state.learnedParams = data;
  const params = data.suggested_params || {};
  $("learnedOut").textContent = JSON.stringify(data, null, 2);
  $("learnedVerdict").className = `verdict ${data.good_pool > 0 ? "pass" : "pending"}`;
  $("learnedVerdict").textContent = data.sampling?.mode ? data.sampling.mode.toUpperCase() : "READY";
  $("learnedPool").textContent = `pool ${data.good_pool ?? 0}`;
  const goldenNote = data.golden_due ? ` Golden due: ${data.golden_variant || "scheduled"}.` : "";
  $("learnedSummary").textContent = `Suggested ${Object.keys(params).length} params for cycle ${data.cycle_n}.${goldenNote}`;
  if (apply) applyParamsToInputs(params);
  setStatus(`Learned params ${apply ? "applied" : "loaded"} (${data.sampling?.mode || "ready"})`, "ok");
}

function resolvePatchFromHit(point) {
  const lx = state.bbox.length;
  const ly = state.bbox.width;
  if (point.y > ly * 0.15) return null;
  if (point.x < lx * 0.33) return "inlet1";
  if (point.x > lx * 0.67) return "inlet3";
  return "inlet2";
}

function syncGateUi() {
  for (const patch of ["inlet1", "inlet2", "inlet3"]) {
    const el = $(`gate_${patch}`);
    if (el) el.checked = !!state.gates[patch];
  }
}

function applyMaterialPresetFromApi() {
  fetch(`${state.apiBase}/api/materials`)
    .then((r) => r.json())
    .then((data) => {
      const p = data.presets?.[$("materialPreset").value];
      if (!p) return;
      $("polymerNu").value = p.polymer_nu;
      $("tMelt").value = p.T_melt_K;
      $("tMold").value = p.T_mold_K;
      $("shrinkAlpha").value = p.thermal_shrink_alpha;
    })
    .catch(() => {});
}

function loadMaterials() { fetch(`${state.apiBase}/api/materials`).then((r) => r.json()).then((data) => { const sel = $("materialPreset"); for (const [key, preset] of Object.entries(data.presets || {})) { if ([...sel.options].some((opt) => opt.value === key)) continue; const opt = document.createElement("option"); opt.value = key; opt.textContent = preset.name || key; sel.appendChild(opt); } }).catch(() => {}); }

async function refreshMesh() {
  let stlUrl = `${state.apiBase}/api/preview.stl`;
  if (state.stepPath) stlUrl += `?step=${encodeURIComponent(state.stepPath)}`;
  try {
    const res = await fetch(`${state.apiBase}/health`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (state.stepPath) {
      await fetch(`${state.apiBase}/api/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step_path: state.stepPath }),
      });
    }
    setStatus("API connected", "ok");
  } catch {
    stlUrl = LOCAL_SAMPLE_STL;
    setStatus("API offline, using sample STL", "warn");
  }

  const geom = await loadStl(stlUrl);
  geom.center();
  geom.computeVertexNormals();
  state.baseGeometry = geom;
  if (state.baseMesh) {
    state.scene.remove(state.baseMesh);
    disposeObject(state.baseMesh);
  }
  const group = new THREE.Group();
  group.add(new THREE.Mesh(geom, cloneBaseMaterial()));
  group.add(new THREE.LineSegments(new THREE.EdgesGeometry(geom, 12), new THREE.LineBasicMaterial({ color: 0x7c8ca5, transparent: true, opacity: 0.45 })));
  state.scene.add(group);
  state.baseMesh = group;
  fitCamera();
  updateOverlays();
  updateReadinessPanel();
}

async function uploadStep(file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${state.apiBase}/api/upload-step`, { method: "POST", body: fd });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "upload failed");
  state.stepPath = data.step_path || "";
  state.bbox = data.bbox_mm || state.bbox;
  $("stepPath").value = state.stepPath;
  $("bboxInfo").textContent = `${fmt(state.bbox.length, 1)} x ${fmt(state.bbox.width, 1)} x ${fmt(state.bbox.height, 1)} mm`;
  await refreshMesh();
  setStatus(`STEP uploaded: ${file.name}`, "ok");
}

async function previewDefectKpis() {
  const process = readProcessParams();
  const body = {
    step_path: state.stepPath,
    process,
    defects: {
      fill_fraction_pct: process.assumed_fill_fraction_pct || (state.goldenRecord?.n_results ? 95.0 : 90.0),
    },
    kpis: {
      cad_bbox_length_mm: state.bbox.length,
      cad_bbox_width_mm: state.bbox.width,
      cad_bbox_height_mm: state.bbox.height,
      projected_area_mm2: process.projected_area_mm2 || undefined,
    },
  };
  const res = await fetch(`${state.apiBase}/api/defect-preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "defect preview failed");
  const p = data.preview || {};
  const values = [
    fmt(p.sink_mark_risk, 3),
    p.flash_risk_label === "UNKNOWN" ? "--" : fmt(p.flash_risk, 3),
    p.flash_risk_label || "--",
    `${fmt(p.clamp_force_required_kN, 2)} kN`,
  ];
  $("defectPreviewStats").querySelectorAll(".stat .v").forEach((el, idx) => {
    el.textContent = values[idx] || "--";
  });
  updateReadinessPanel();
  const flashWarn = p.flash_risk_label === "UNKNOWN" || p.flash_risk >= 0.5;
  setStatus(`Preview sink=${values[0]} flash=${values[1]}`, flashWarn ? "warn" : "ok");
}

async function exportJob() {
  const analysis = readAnalysisConfig();
  const process = readProcessParams();
  const enabledCats = [...new Set(Object.values(analysis).filter((a) => a.enabled).map((a) => a.category))];
  const category = enabledCats[0] || process.physics_category || "resin_fill_cad";
  const jobId = $("jobId").value.trim() || `studio_${Date.now()}`;
  const body = {
    job_id: jobId,
    category,
    step_path: state.stepPath,
    gate_spec: buildGateSpec(),
    process,
    material: { preset: $("materialPreset").value, polymer_nu: process.polymer_nu, viscosity_model: process.viscosity_model, T_melt: process.T_melt, T_mold: process.T_mold },
    analysis,
    openfoam_params: { ...process, gate_spec_path: "", step_path: state.stepPath },
  };
  const res = await fetch(`${state.apiBase}/api/export-job`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "export failed");
  $("jobOut").textContent = JSON.stringify(data, null, 2);
  updateReadinessPanel();
  setStatus(`Job exported: ${data.job_id}`, "ok");
}

async function refreshGoldenCase() {
  try {
    const spec = await fetchJsonWithFallback(`${state.apiBase}/api/golden-case`, LOCAL_GOLDEN_SPEC).catch(() => null);
    const specDoc = spec?.spec || spec;
    state.goldenSpec = specDoc;
    if (spec?.record) {
      state.goldenRecord = spec.record;
    } else {
      const logDoc = await fetchJsonWithFallback(`${state.apiBase}/api/golden-log`, LOCAL_CAE_LOG).catch(() => null);
      const trials = Array.isArray(logDoc?.trials) ? logDoc.trials : [];
      const variantNames = Object.keys(specDoc?.variants || {});
      state.goldenRecord = evaluateGolden(collectGoldenResults(trials, variantNames), specDoc);
    }
    renderGoldenPanel();
    updateReadinessPanel();
    setStatus(`Golden case ${state.goldenRecord.verdict}`, state.goldenRecord.verdict === "PASS" ? "ok" : "warn");
  } catch (err) {
    state.goldenSpec = null;
    state.goldenRecord = null;
    $("goldenVerdict").className = "verdict fail";
    $("goldenVerdict").textContent = "LOAD FAIL";
    setText("goldenMeta", String(err));
    $("goldenChecks").innerHTML = "";
    $("variantCards").innerHTML = "";
    setStatus("Golden case load failed", "warn");
  }
}

function initScene() {
  state.host = $("canvasHost");
  state.scene = new THREE.Scene();
  state.scene.background = new THREE.Color(0x09111e);
  state.camera = new THREE.PerspectiveCamera(48, 1, 0.01, 5000);
  state.renderer = new THREE.WebGLRenderer({ antialias: true });
  state.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  state.renderer.shadowMap.enabled = true;
  state.host.appendChild(state.renderer.domElement);
  state.controls = new OrbitControls(state.camera, state.renderer.domElement);
  state.controls.enableDamping = true;
  state.scene.add(new THREE.HemisphereLight(0xffffff, 0x1e293b, 1.05));
  const dir = new THREE.DirectionalLight(0xffffff, 0.9);
  dir.position.set(120, 160, 80);
  state.scene.add(dir);
  state.overlayGroup = new THREE.Group();
  state.scene.add(state.overlayGroup);
  state.renderer.domElement.addEventListener("pointerdown", (ev) => {
    const rect = state.renderer.domElement.getBoundingClientRect();
    const pointer = new THREE.Vector2(((ev.clientX - rect.left) / rect.width) * 2 - 1, -((ev.clientY - rect.top) / rect.height) * 2 + 1);
    const ray = new THREE.Raycaster();
    ray.setFromCamera(pointer, state.camera);
    const hits = ray.intersectObject(state.baseMesh, true);
    if (!hits.length) return;
    const patch = resolvePatchFromHit(hits[0].point);
    if (!patch) { setStatus("Click the lower edge to toggle a gate", "warn"); return; }
    state.gates[patch] = !state.gates[patch];
    syncGateUi();
    updateOverlays();
    setStatus(`${patch} -> ${state.gates[patch] ? "ON" : "OFF"}`, "ok");
  });
  window.addEventListener("resize", onResize);
  onResize();
  animate();
}

function onResize() {
  if (!state.host || !state.camera || !state.renderer) return;
  const w = Math.max(state.host.clientWidth, 1);
  const h = Math.max(state.host.clientHeight, 1);
  state.camera.aspect = w / h;
  state.camera.updateProjectionMatrix();
  state.renderer.setSize(w, h, false);
}

function animate() {
  requestAnimationFrame(animate);
  if (state.controls) state.controls.update();
  if (state.renderer && state.scene && state.camera) state.renderer.render(state.scene, state.camera);
}

function initApp() {
  repairHelpCopy();
  applyClearHelpCopy();
  ensureAccuracyInputs();
  ensureLearningPanel();
  ensureSolverLandscapePanel();
  ensureReadinessPanel();
  renderAnalysisPanel();
  initScene();
  syncGateUi();
  loadMaterials();
  refreshGoldenCase().catch(() => {});
  $("apiBase").value = state.apiBase;
  $("apiBase").addEventListener("change", (e) => { state.apiBase = e.target.value.trim() || API_DEFAULT; setStatus(`API base set to ${state.apiBase}`, "warn"); loadMaterials(); });
  for (const id of ["polymerNu", "shrinkAlpha", "tMelt", "tMold", "tEject", "inletVelocity", "packPressure", "meshMode", "meshSize", "physicsCategory", "jobId", "viscosityModel", "clampForce", "projectedArea", "nominalWall", "assumedFillPct", "packInletVelocity", "powerLawNu0", "powerLawK", "powerLawN", "shearRate"]) {
    const el = $(id);
    if (!el) continue;
    el.addEventListener("input", updateReadinessPanel);
    el.addEventListener("change", updateReadinessPanel);
  }
  $("btnUpload").addEventListener("click", () => $("stepFile").click());
  $("stepFile").addEventListener("change", (e) => { const file = e.target.files?.[0]; if (file) uploadStep(file).catch((err) => setStatus(String(err), "warn")); });
  $("btnReload").addEventListener("click", () => refreshMesh().catch((err) => setStatus(String(err), "warn")));
  $("btnResetCam").addEventListener("click", fitCamera);
  $("btnLoadSample").addEventListener("click", () => { state.stepPath = ""; $("stepPath").value = ""; $("bboxInfo").textContent = "--"; refreshMesh().catch((err) => setStatus(String(err), "warn")); });
  $("materialPreset").addEventListener("change", applyMaterialPresetFromApi);
  $("btnPreviewDefects").addEventListener("click", () => previewDefectKpis().catch((err) => setStatus(String(err), "warn")));
  $("btnExportJob").addEventListener("click", () => exportJob().catch((err) => setStatus(String(err), "warn")));
  $("btnLoadLearned").addEventListener("click", () => loadLearnedParams().catch((err) => setStatus(String(err), "warn")));
  $("btnApplyLearned").addEventListener("click", () => loadLearnedParams({ apply: true }).catch((err) => setStatus(String(err), "warn")));
  $("btnLoadSolverLandscape").addEventListener("click", () => loadSolverLandscape().catch((err) => setStatus(String(err), "warn")));
  $("btnApplySafeThermal").addEventListener("click", applySafeThermalProxyDefaults);
  $("btnDownloadGate").addEventListener("click", () => { const blob = new Blob([JSON.stringify(buildGateSpec(), null, 2)], { type: "application/json" }); const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "gate_spec.json"; a.click(); URL.revokeObjectURL(a.href); });
  $("btnRefreshGolden").addEventListener("click", () => refreshGoldenCase().catch((err) => setStatus(String(err), "warn")));
  for (const patch of ["inlet1", "inlet2", "inlet3"]) {
    $(`gate_${patch}`).addEventListener("change", (ev) => {
      state.gates[patch] = !!ev.target.checked;
      updateOverlays();
      updateReadinessPanel();
    });
  }
  $("btnPresetCenter").addEventListener("click", () => { state.gates = { inlet1: false, inlet2: true, inlet3: false }; syncGateUi(); updateOverlays(); updateReadinessPanel(); });
  $("btnPresetDual").addEventListener("click", () => { state.gates = { inlet1: true, inlet2: false, inlet3: true }; syncGateUi(); updateOverlays(); updateReadinessPanel(); });
  $("btnPresetTriple").addEventListener("click", () => { state.gates = { inlet1: true, inlet2: true, inlet3: true }; syncGateUi(); updateOverlays(); updateReadinessPanel(); });
  refreshMesh()
    .then(() => {
      $("bboxInfo").textContent = `${fmt(state.bbox.length, 1)} x ${fmt(state.bbox.width, 1)} x ${fmt(state.bbox.height, 1)} mm`;
      $("stepPath").value = state.stepPath || "";
      setStatus("Ready", "ok");
    })
    .catch((err) => setStatus(String(err), "warn"));
  loadSolverLandscape().catch(() => {});
  loadMaturity().catch(() => {});
  // --- HOT RUNNER EQUIPMENT CHANGE LISTENERS ---
  const updateHotrunnerStatus = () => {
    const brand = $("hotrunnerBrand")?.options[$("hotrunnerBrand").selectedIndex]?.text || "Mold-Masters";
    const act = $("actuationType")?.options[$("actuationType").selectedIndex]?.text || "Electric Servo";
    if ($("hotrunnerStatus")) {
      $("hotrunnerStatus").textContent = `設備: ${brand.split(' ')[0]} | 駆動: ${act.split(' ')[0]}`;
    }
  };
  $("hotrunnerBrand")?.addEventListener("change", updateHotrunnerStatus);
  $("actuationType")?.addEventListener("change", updateHotrunnerStatus);
  updateHotrunnerStatus();

  // --- NEXT-GEN MOLDFLOW SUPERIORITY AI EVENT LISTENERS ---
  const runSurrogate = async () => {
    const pack = parseFloat($("sliderPackPressure")?.value || 80);
    const mold = parseFloat($("sliderMoldTemp")?.value || 65);
    $("valSurrPack").textContent = pack;
    $("valSurrMold").textContent = mold;
    try {
      const res = await fetch(`${state.apiBase}/api/surrogate_predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ packing_pressure_mpa: pack, mold_temp_c: mold })
      });
      if (res.ok) {
        const d = await res.json();
        $("surrLatency").textContent = `${d.latency_ms} ms`;
        $("surrWarp").textContent = `${d.predicted_max_warpage_mm} mm`;
      }
    } catch (e) {}
  };

  $("sliderPackPressure")?.addEventListener("input", runSurrogate);
  $("sliderMoldTemp")?.addEventListener("input", runSurrogate);

  $("btnAiOptimize")?.addEventListener("click", async () => {
    setStatus("AI 全自動ゲート＆水路最適化を実行中...", "warn");
    try {
      const res = await fetch(`${state.apiBase}/api/ai_optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ material: $("materialPreset")?.value || "PBT-GF30", target_warpage_mm: 0.20 })
      });
      const d = await res.json();
      $("aiOptResult").textContent = `✅ AI最適ゲート: G1=[${d.gate_1_xyz}], G2=[${d.gate_2_xyz}]\n水路径: ${d.conformal_channel_dia_mm}mm, 予測反り: ${d.predicted_warpage_mm}mm, サイクル: ${d.predicted_cycle_time_sec}s`;
      setStatus("AI 最適レイアウト計算完了！", "ok");
    } catch (e) { setStatus(String(e), "warn"); }
  });

  $("btnFiberAnalysis")?.addEventListener("click", async () => {
    try {
      const res = await fetch(`${state.apiBase}/api/fiber_void_analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fiber_content_pct: 30.0 })
      });
      const d = await res.json();
      $("fiberResult").textContent = `配向テンソル: Flow=${d.orientation_tensor_main_diag[0]}, Trans=${d.orientation_tensor_main_diag[1]}\n弾性率: 流動 ${d.tensile_modulus_parallel_gpa} GPa, 直角 ${d.tensile_modulus_transverse_gpa} GPa\nボイド最大径: ${d.predicted_micro_void_max_diameter_um} μm (リスク: ${d.void_formation_risk_score})`;
      setStatus("繊維配向・ミクロボイド解析完了", "ok");
    } catch (e) { setStatus(String(e), "warn"); }
  });

  $("btnEcoCost")?.addEventListener("click", async () => {
    try {
      const res = await fetch(`${state.apiBase}/api/eco_cost_estimate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cycle_time_sec: 14.5, is_conformal_cooling: true })
      });
      const d = await res.json();
      $("ecoResult").textContent = `🌱 電力: ${d.power_kwh_per_part} kWh/個, CO₂: ${d.co2_kg_per_part} kg/個 (年間 ${d.annual_100k_parts_co2_tons}トン)\n💰 金型加工費: ¥${d.total_tooling_cost_jpy.toLocaleString()} (3D水路: -${d.cycle_time_reduction_pct}%)`;
      setStatus("CO₂ ＆ 金型コスト試算完了", "ok");
    } catch (e) { setStatus(String(e), "warn"); }
  });

  $("btnRunAiCommand")?.addEventListener("click", async () => {
    const text = $("aiCommandInput")?.value || "PBT-GF30で反り0.2mm以下の保圧条件を計算";
    setStatus("AI 1コマンド全自動解析中...", "warn");
    try {
      const res = await fetch(`${state.apiBase}/api/one_command_agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command_text: text })
      });
      const d = await res.json();
      $("aiCommandOut").textContent = `🤖 指示: ${d.user_command}\n[解明ステータス]: ${d.agent_status}\n[最適結果]: 予測反り ${d.optimization_result.predicted_warpage_mm}mm (目標以下達成!)\n[CO₂年間]: ${d.eco_cost_analysis.annual_100k_parts_co2_tons}トン CO₂削減`;
      setStatus("1コマンド全自動解析完結！", "ok");
    } catch (e) { setStatus(String(e), "warn"); }
  });

  $("btnInsertAnalysis")?.addEventListener("click", async () => {
    const mat = $("insertMaterial")?.value || "Brass_C3604";
    const preheat = parseFloat($("insertPreheatTemp")?.value || 80);
    setStatus("インサート成形 異種材料熱応力解析中...", "warn");
    try {
      const res = await fetch(`${state.apiBase}/api/insert_molding_analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ insert_material: mat, insert_preheat_temp_c: preheat })
      });
      const d = await res.json();
      $("insertResult").textContent = `🍱 金具: ${d.insert_material} (予熱 ${d.insert_preheat_temp_c}°C)\n線膨張差歪み: ${d.thermal_mismatch_strain_pct}%\n界面ミーゼス応力: ${d.interfacial_residual_stress_mpa} MPa\n界面剥離リスクスコア: ${d.debonding_delamination_risk_score} [判定: ${d.status}]\nインサート熱偏肉反り量: ${d.predicted_insert_warpage_offset_mm} mm`;
      setStatus("インサート異種材料解析完了！", "ok");
    } catch (e) { setStatus(String(e), "warn"); }
  });

  $("btnPinStrengthAnalysis")?.addEventListener("click", async () => {
    const dia = parseFloat($("pinDiameter")?.value || 2.0);
    const len = parseFloat($("pinLength")?.value || 15.0);
    const mat = $("pinMaterial")?.value || "SKD61_Hardened";
    const dp = parseFloat($("pinDiffPressure")?.value || 45.0);
    setStatus("インサートピン 流動片圧・強度破損計算中...", "warn");
    try {
      const res = await fetch(`${state.apiBase}/api/insert_pin_strength_analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin_diameter_mm: dia, pin_length_mm: len, pin_material: mat, differential_pressure_mpa: dp })
      });
      const d = await res.json();
      $("pinResult").textContent = `📌 ピン仕様: d=${d.pin_diameter_mm}mm, L=${d.pin_length_mm}mm (${d.pin_material})\n流体力: ${d.resin_drag_force_n} N (片圧 ΔP=${d.differential_pressure_mpa} MPa)\n最大曲げ応力: ${d.max_bending_stress_mpa} MPa (許容: ${d.yield_strength_limit_mpa} MPa)\n先端撓み量: ${d.pin_deflection_mm} mm\n安全率 SF: ${d.safety_factor} [判定: ${d.strength_verdict_japanese}]`;
      setStatus(`ピン強度計算完了 (${d.strength_verdict})`, "ok");
    } catch (e) { setStatus(String(e), "warn"); }
  });

  $("btnMoldBaseSizing")?.addEventListener("click", async () => {
    const len = state.bbox.length || 100.0;
    const wid = state.bbox.width || 60.0;
    const hei = state.bbox.height || 30.0;
    const shots = parseInt($("annualShots")?.value || 100000);
    setStatus("上型・下型 最適プレートサイズ ＆ 最適鋼材選定中...", "warn");
    try {
      const res = await fetch(`${state.apiBase}/api/mold_base_recommendation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ part_length_mm: len, part_width_mm: wid, part_height_mm: hei, annual_production_shots: shots })
      });
      const d = await res.json();
      $("moldBaseResult").textContent = `🏭 推奨金型鋼材: ${d.steel_name} (${d.steel_hardness_hrc} HRC) [${d.suitability_note}]\n📐 上型(キャビ)プレート外形: ${d.upper_plate_size_mm[0]} x ${d.upper_plate_size_mm[1]} x ${d.upper_plate_size_mm[2]} mm (重量 ${d.upper_plate_weight_kg} kg)\n📐 下型(コア)プレート外形: ${d.lower_plate_size_mm[0]} x ${d.lower_plate_size_mm[1]} x ${d.lower_plate_size_mm[2]} mm (重量 ${d.lower_plate_weight_kg} kg)\n🧱 最小必要側壁肉厚: ${d.min_wall_thickness_mm} mm, 底肉厚: ${d.min_bottom_thickness_mm} mm\n⚖️ 金型総重量: ${d.total_mold_weight_kg} kg (概算材料費: ¥${d.estimated_steel_cost_jpy.toLocaleString()})\n💥 型締め撓み: ${d.mold_clamping_deflection_um} μm [バリ判定: ${d.flash_prevention_status}]`;
      setStatus(`金型プレート最適選定完了 (${d.recommended_steel_grade})`, "ok");
    } catch (e) { setStatus(String(e), "warn"); }
  });

  $("btnAiRecommendPl")?.addEventListener("click", async () => {
    const hei = state.bbox.height || 30.0;
    const userZVal = $("userPlZ")?.value ? parseFloat($("userPlZ").value) : null;
    setStatus("AI 最適パーティングライン (PL面) 解析中...", "warn");
    try {
      const res = await fetch(`${state.apiBase}/api/parting_line_recommendation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ part_height_mm: hei, user_pl_z_mm: userZVal })
      });
      const d = await res.json();
      const pl = d.selected_pl;
      $("plResult").textContent = `✂️ PL分割方式: ${d.selection_mode === "USER_MANUAL_CUSTOM" ? "ユーザーカスタム指定" : "AI 自動最適推奨"}\n📍 PL面 Z高さ: ${pl.pl_z_level_mm} mm (${pl.pl_type})\n📐 アンダーカット面積: ${pl.undercut_area_cm2} cm²\n⚙️ 必要スライドコア数: ${pl.slide_cores_needed} 個\n⭐ AI 総合スコア: ${pl.ai_score} / 1.0 (抜き勾配判定: ${d.draft_angle_pass ? "合格" : "再設計必要"})`;
      setStatus(`PL分割面計算完了 (Z=${pl.pl_z_level_mm}mm)`, "ok");
    } catch (e) { setStatus(String(e), "warn"); }
  });

  $("btnMicroDefectsAnalysis")?.addEventListener("click", async () => {
    const clamp = parseFloat($("clampForceKn")?.value || 800);
    const restime = parseFloat($("residenceTimeSec")?.value || 180);
    const moist = parseFloat($("moisturePct")?.value || 0.04);
    const area = parseFloat($("projectedAreaCm2")?.value || 120);
    const pack = parseFloat($("packPressure")?.value || 85.0);
    const tmelt = parseFloat($("tMelt")?.value || 513) - 273.15;
    setStatus("Moldflow超越 微視的成形不良物理解析中...", "warn");
    try {
      const res = await fetch(`${state.apiBase}/api/advanced_defects_analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cavity_pressure_mpa: pack > 0 ? pack : 85.0,
          clamping_force_kn: clamp,
          projected_area_cm2: area,
          melt_temp_c: tmelt > 0 ? tmelt : 260.0,
          residence_time_sec: restime,
          moisture_content_pct: moist
        })
      });
      const d = await res.json();
      $("microDefectResult").textContent = `💥 物理バリ長: ${d.physical_flash_length_um} μm (合わせ面隙間: ${d.physical_mold_gap_um} μm) [判定: ${d.flash_status}]\n🫧 内部ミクロボイド球径: ${d.internal_void_diameter_um} μm [判定: ${d.internal_void_status}]\n✨ シルバー銀条インデックス: ${d.silver_streak_index} (発生分解ガス: ${d.total_gas_concentration_pct} vol%) [判定: ${d.silver_streak_status}]\n🔥 エアトラップ最高到達ガス温度: ${d.adiabatic_air_trap_temp_c} °C [焼け判定: ${d.burn_mark_status}]`;
      setStatus("微視的不良解析完了！", "ok");
    } catch (e) { setStatus(String(e), "warn"); }
  });

  $("btnPurgingAnalysis")?.addEventListener("click", async () => {
    const purgeGrade = $("purgingGrade")?.value || "Glass_Filled_Purge";
    const ppm = parseFloat($("targetPpm")?.value || 50.0);
    const screw = parseFloat($("screwDiameter")?.value || 45.0);
    setStatus("パージダイナミクス ＆ 捨てショット数計算中...", "warn");
    try {
      const res = await fetch(`${state.apiBase}/api/purging_contamination_analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ purging_grade: purgeGrade, target_quality_ppm: ppm, screw_diameter_mm: screw })
      });
      const d = await res.json();
      $("purgingResult").textContent = `🧹 洗浄パージグレード: ${d.purging_grade}\n🎯 目標コンタミ許容限界: ${d.target_quality_ppm} PPM\n🎯 最小最適『必要捨てショット数』: ${d.optimal_required_purge_shots} ショット\n⚖️ 総パージ廃棄樹脂量: ${d.total_waste_weight_kg} kg (廃棄材料コスト: ¥${d.total_waste_cost_jpy.toLocaleString()})\n✨ 達成到達異物濃度: ${d.final_achieved_contamination_ppm} PPM [判定: ${d.purging_verdict}]`;
      setStatus(`パージ捨てショット計算完了 (${d.optimal_required_purge_shots}shots)`, "ok");
    } catch (e) { setStatus(String(e), "warn"); }
  });
}

initApp();
