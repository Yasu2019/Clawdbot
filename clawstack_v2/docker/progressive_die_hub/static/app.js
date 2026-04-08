/* Progressive Die Hub — フロントエンドロジック */
'use strict';

const API = '';   // 同一オリジン

let state = {
  jobId:    null,
  geom:     null,
  layout:   null,
  fem:      null,
  calc:     null,
  filename: null,
};

// ── ユーティリティ ────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const show = id => $(id).classList.remove('hidden');
const hide = id => $(id).classList.add('hidden');

function msg(containerId, type, text) {
  const el = $(containerId);
  el.innerHTML = `<div class="msg msg-${type}">${text}</div>`;
}

function setLoading(btnId, loading, label) {
  const btn = $(btnId);
  if (!btn) return;
  btn.disabled = loading;
  btn.innerHTML = loading
    ? `<span class="spinner"></span>${label || '処理中...'}`
    : (btn.dataset.label || label || 'OK');
}

async function apiPost(url, formData) {
  const res = await fetch(API + url, { method: 'POST', body: formData });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || 'API エラー');
  return json;
}

// ── タブ切替 ──────────────────────────────────────────────────────────────────
function switchTab(n) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.step-btn').forEach(el => el.classList.remove('active'));
  $(`tab-${n}`).classList.add('active');
  $(`step-${n}`).classList.add('active');
}

window.gotoStep = switchTab;

// ── ステップ1: ファイルアップロード ──────────────────────────────────────────
function initUpload() {
  const zone  = $('upload-zone');
  const input = $('file-input');

  zone.addEventListener('click',      () => input.click());
  zone.addEventListener('dragover',   e => { e.preventDefault(); zone.classList.add('drag'); });
  zone.addEventListener('dragleave',  () => zone.classList.remove('drag'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
  });
  input.addEventListener('change', () => {
    if (input.files.length) handleFile(input.files[0]);
  });
}

async function handleFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['dxf', 'stp', 'step'].includes(ext)) {
    msg('upload-msg', 'err', `未対応形式: .${ext}<br>DXF または STEP ファイルをアップロードしてください`);
    return;
  }

  msg('upload-msg', 'info',
    `<span class="spinner"></span>${file.name} を解析中...`);
  $('upload-zone').querySelector('.icon').textContent = '⚙️';

  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await apiPost('/api/upload', fd);
    state.jobId    = res.job_id;
    state.geom     = res.geom;
    state.filename = file.name;
    $('step-1').classList.add('done');
    renderGeomResult(res.geom, file.name);
    msg('upload-msg', 'ok',
      `✅ 解析完了: ${file.name} — 次のステップへ進んでください`);
    $('upload-zone').querySelector('.icon').textContent = '✅';
  } catch (e) {
    msg('upload-msg', 'err', `❌ ${e.message}`);
    $('upload-zone').querySelector('.icon').textContent = '📂';
  }
}

function renderGeomResult(geom, filename) {
  const dims = geom.dimensions;
  $('geom-info').innerHTML = `
    <div class="kv-grid">
      <div class="kv-card"><div class="label">ファイル</div>
        <div class="value" style="font-size:.9em">${filename}</div></div>
      <div class="kv-card"><div class="label">外形幅</div>
        <div class="value">${dims.width.toFixed(2)} mm</div></div>
      <div class="kv-card"><div class="label">外形高さ</div>
        <div class="value">${dims.height.toFixed(2)} mm</div></div>
      <div class="kv-card"><div class="label">穴数</div>
        <div class="value">${geom.holes.length}</div></div>
      <div class="kv-card"><div class="label">曲げ線</div>
        <div class="value">${geom.bends.length}</div></div>
      <div class="kv-card"><div class="label">ファイル種別</div>
        <div class="value">${geom.type.toUpperCase()}</div></div>
    </div>
    <div style="margin-top:10px">
      <span style="color:var(--muted);font-size:.82em">レイヤー: </span>
      ${geom.layers.map(l => `<span class="layer-tag">${l}</span>`).join('')}
    </div>
    ${geom.holes.length ? `
    <div style="margin-top:8px;font-size:.85em;color:var(--muted)">
      穴: ${geom.holes.map(h => `φ${(h.r*2).toFixed(2)}`).join(', ')}
    </div>` : ''}
    ${geom.bends.length ? `
    <div style="margin-top:4px;font-size:.85em;color:#4ecdc4">
      曲げ線: ${geom.bends.length} 箇所検出（角度は次ステップで設定）
    </div>` : ''}
  `;
  show('geom-result');
}

// ── ステップ2: 材料・パラメータ設定 ──────────────────────────────────────────
async function loadMaterials() {
  try {
    const res = await fetch(API + '/api/materials');
    const mats = await res.json();
    const sel  = $('mat-select');
    sel.innerHTML = '';
    Object.entries(mats).forEach(([key, m]) => {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = m.name;
      sel.appendChild(opt);
    });
    sel.dispatchEvent(new Event('change'));
  } catch (e) {
    console.warn('材料読み込み失敗:', e);
  }
}

function initMaterialSelect() {
  $('mat-select').addEventListener('change', async function() {
    const res  = await fetch(API + '/api/materials');
    const mats = await res.json();
    const m    = mats[this.value];
    if (!m) return;
    $('mat-E').textContent    = `E = ${m.E.toLocaleString()} MPa`;
    $('mat-sy').textContent   = `σy = ${m.yield_stress} MPa`;
    $('mat-uts').textContent  = `σu = ${m.uts} MPa`;
    $('mat-kf').textContent   = `K = ${m.k_factor}`;
  });
}

// ── ステップ3: ストリップレイアウト ──────────────────────────────────────────
async function generateLayout() {
  if (!state.jobId) {
    msg('layout-msg', 'warn', '先にファイルをアップロードしてください');
    return;
  }
  setLoading('btn-layout', true, 'ストリップ生成中...');

  const fd = new FormData();
  fd.append('job_id',       state.jobId);
  fd.append('material',     $('mat-select').value);
  fd.append('thickness',    $('thickness').value);
  fd.append('bend_radius',  $('bend-radius').value);
  fd.append('bend_angle',   $('bend-angle').value);
  fd.append('strip_margin', $('strip-margin').value);

  try {
    const res = await apiPost('/api/strip-layout', fd);
    state.layout = res;
    renderLayout(res);
    $('step-3').classList.add('done');
    msg('layout-msg', 'ok', `✅ ストリップレイアウト生成完了 — ${res.summary.station_count} 工程`);
  } catch(e) {
    msg('layout-msg', 'err', `❌ ${e.message}`);
  } finally {
    $('btn-layout').dataset.label = 'ストリップレイアウト生成';
    setLoading('btn-layout', false);
  }
}

function renderLayout(data) {
  // SVG 表示
  $('svg-container').innerHTML = data.svg;

  // サマリー KV
  const s = data.summary;
  $('layout-summary').innerHTML = `
    <div class="kv-grid">
      <div class="kv-card"><div class="label">工程数</div>
        <div class="value">${s.station_count}</div></div>
      <div class="kv-card"><div class="label">送りピッチ</div>
        <div class="value">${s.pitch_mm} mm</div></div>
      <div class="kv-card"><div class="label">ストリップ幅</div>
        <div class="value">${s.strip_width_mm} mm</div></div>
      <div class="kv-card"><div class="label">総打ち抜き力</div>
        <div class="value">${s.total_force_kN} kN</div></div>
      <div class="kv-card"><div class="label">必要プレス容量</div>
        <div class="value ${s.press_capacity_ton > 100 ? 'warn' : 'ok'}">${s.press_capacity_ton} ton</div></div>
    </div>
  `;

  // 工程テーブル
  const opColor = {
    pilot_hole: '#FFE66D', notch: '#FF6B6B',
    hole_punch: '#FFD700', bend:  '#4ECDC4', cutoff: '#66bb6a'
  };
  $('station-table').innerHTML = `
    <table>
      <tr><th>No.</th><th>工程名</th><th>打ち抜き力</th><th>詳細</th></tr>
      ${data.stations.map(st => `
        <tr>
          <td>${st.no}</td>
          <td><span style="color:${opColor[st.operation]||'#eee'}">${st.name}</span></td>
          <td>${st.punch_force} kN</td>
          <td>${st.description}</td>
        </tr>
      `).join('')}
    </table>
  `;
  show('layout-result');
}

// ── ステップ4: FEM 解析 ────────────────────────────────────────────────────
async function generateFem() {
  if (!state.jobId || !state.layout) {
    msg('fem-msg', 'warn', '先にストリップレイアウトを生成してください');
    return;
  }
  setLoading('btn-fem', true, 'FEM デッキ生成中...');

  const fd = new FormData();
  fd.append('job_id', state.jobId);

  try {
    const res = await apiPost('/api/generate-fem', fd);
    state.fem  = res;
    renderFemResult(res);
    $('step-4').classList.add('done');
    msg('fem-msg', 'ok', '✅ FEM 入力デッキ生成完了');
  } catch(e) {
    msg('fem-msg', 'err', `❌ ${e.message}`);
  } finally {
    $('btn-fem').dataset.label = 'FEM 入力デッキ生成';
    setLoading('btn-fem', false);
  }
}

function renderFemResult(data) {
  // OpenRadioss
  const b = data.blanking;
  const v = data.bending;
  $('radioss-info').innerHTML = `
    <div class="kv-grid">
      <div class="kv-card"><div class="label">打ち抜き 要素数</div>
        <div class="value">${b.element_count}</div></div>
      <div class="kv-card"><div class="label">打ち抜き力</div>
        <div class="value">${b.punch_force_kN} kN</div></div>
      <div class="kv-card"><div class="label">クリアランス</div>
        <div class="value">${b.clearance_mm} mm</div></div>
      <div class="kv-card"><div class="label">曲げ 要素数</div>
        <div class="value">${v.element_count}</div></div>
      <div class="kv-card"><div class="label">スプリングバック</div>
        <div class="value warn">+${v.springback_deg}°</div></div>
      <div class="kv-card"><div class="label">補正角度</div>
        <div class="value">${v.corrected_angle}°</div></div>
    </div>
  `;

  // CalculiX
  const p = data.punch;
  const d = data.die;
  const sfClass = sf => sf >= 2.0 ? 'ok' : 'warn';
  $('calculix-info').innerHTML = `
    <div class="kv-grid">
      <div class="kv-card ${sfClass(p.sf_compression)}">
        <div class="label">パンチ 圧縮 SF</div>
        <div class="value">${p.sf_compression}</div></div>
      <div class="kv-card ${sfClass(p.sf_buckling)}">
        <div class="label">パンチ 座屈 SF</div>
        <div class="value">${p.sf_buckling}</div></div>
      <div class="kv-card ${sfClass(p.sf_compression)}">
        <div class="label">圧縮応力</div>
        <div class="value">${p.sigma_comp_MPa} MPa</div></div>
      <div class="kv-card ${sfClass(d.sf)}">
        <div class="label">ダイ フープ SF</div>
        <div class="value">${d.sf}</div></div>
    </div>
    <div style="margin-top:8px">
      <span class="sf-badge ${p.status==='OK'?'sf-ok':'sf-warn'}">パンチ: ${p.status}</span>
      &nbsp;
      <span class="sf-badge ${d.status==='OK'?'sf-ok':'sf-warn'}">ダイ: ${d.status}</span>
    </div>
  `;

  // ファイルリスト
  $('fem-files').innerHTML = `
    <ul class="file-list">
      ${data.files.map(f => `
        <li>
          <span class="fname">📄 ${f}</span>
          <a href="/api/download/${state.jobId}/${f}" download
             class="btn btn-ghost btn-sm">⬇ DL</a>
        </li>
      `).join('')}
    </ul>
  `;

  show('fem-result');
}

async function runRadioss() {
  if (!state.jobId || !state.fem) {
    msg('fem-msg', 'warn', 'まず FEM デッキを生成してください');
    return;
  }
  setLoading('btn-run-radioss', true, 'OpenRadioss 実行中...');
  const fd = new FormData();
  fd.append('job_id', state.jobId);
  try {
    const res = await apiPost('/api/run-radioss', fd);
    let html = '<div style="margin-top:10px">';
    for (const [label, r] of Object.entries(res.results)) {
      html += `<div class="msg ${r.success?'msg-ok':'msg-warn'}">
        ${label}: ${r.success ? '✅ 完了' : '⚠ エラー'}
        <pre style="margin-top:6px;font-size:.78em">${r.stdout.slice(-800)}</pre>
      </div>`;
    }
    html += '</div>';
    $('radioss-run-result').innerHTML = html;
    show('radioss-run-result');
  } catch(e) {
    msg('fem-msg', 'err', `❌ ${e.message}`);
  } finally {
    setLoading('btn-run-radioss', false, 'OpenRadioss 実行');
  }
}

async function runCalculix() {
  if (!state.jobId || !state.fem) {
    msg('fem-msg', 'warn', 'まず FEM デッキを生成してください');
    return;
  }
  setLoading('btn-run-ccx', true, 'CalculiX 実行中...');
  const fd = new FormData();
  fd.append('job_id', state.jobId);
  try {
    const res = await apiPost('/api/run-calculix', fd);
    let html = '<div style="margin-top:10px">';
    for (const [label, r] of Object.entries(res.results)) {
      html += `<div class="msg ${r.success?'msg-ok':'msg-warn'}">
        ${label}: ${r.success ? '✅ 完了' : '⚠ エラー'}
        <pre style="margin-top:6px;font-size:.78em">${r.stdout.slice(-600)}</pre>
      </div>`;
    }
    html += '</div>';
    $('ccx-run-result').innerHTML = html;
    show('ccx-run-result');
  } catch(e) {
    msg('fem-msg', 'err', `❌ ${e.message}`);
  } finally {
    setLoading('btn-run-ccx', false, 'CalculiX 実行');
  }
}

// ── ステップ5: 報告書 ─────────────────────────────────────────────────────────
async function generateReport() {
  if (!state.jobId) {
    msg('report-msg', 'warn', 'ジョブがありません');
    return;
  }
  setLoading('btn-report', true, '報告書生成中...');
  try {
    const iframe = $('report-frame');
    iframe.src = `${API}/api/report/${state.jobId}`;
    $('step-5').classList.add('done');
    msg('report-msg', 'ok', '✅ 報告書生成完了');
    show('report-preview');
    $('btn-dl-report').href = `/api/download/${state.jobId}/report.html`;
    show('btn-dl-report');
  } catch(e) {
    msg('report-msg', 'err', `❌ ${e.message}`);
  } finally {
    setLoading('btn-report', false, '報告書生成');
  }
}

// ── 初期化 ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initUpload();
  loadMaterials();
  initMaterialSelect();

  $('btn-layout').dataset.label   = 'ストリップレイアウト生成';
  $('btn-fem').dataset.label      = 'FEM 入力デッキ生成';
  $('btn-report').dataset.label   = '報告書生成';

  // ステップ1で「次へ」
  $('btn-to-step2').addEventListener('click', () => switchTab(2));
  $('btn-to-step3').addEventListener('click', () => switchTab(3));
  $('btn-layout').addEventListener('click', generateLayout);
  $('btn-to-step4').addEventListener('click', () => switchTab(4));
  $('btn-fem').addEventListener('click', generateFem);
  $('btn-run-radioss').addEventListener('click', runRadioss);
  $('btn-run-ccx').addEventListener('click', runCalculix);
  $('btn-report').addEventListener('click', generateReport);

  switchTab(1);
});
