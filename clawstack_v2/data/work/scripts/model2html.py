#!/usr/bin/env python3
"""
model2html.py - Convert 3D Model (STEP/STL/OBJ) to a downloadable HTML viewer.

The output is a self-contained HTML file with Plotly bundled inline, so users
can open it locally by double-clicking. The viewer includes display mode,
outline, lighting, and color controls tuned for mesh-based STEP/STL previews.
"""
from __future__ import annotations

import argparse
import html
import json
import tempfile
from pathlib import Path

import numpy as np

AUTO_SIMPLIFY_FACE_THRESHOLD = 180_000
AUTO_SIMPLIFY_TARGET_FACES = 120_000
AUTO_SIMPLIFY_HARD_CAP = 150_000
TARGET_HTML_SIZE_KB = 5000
TARGET_HTML_BYTES = TARGET_HTML_SIZE_KB * 1024
PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


HTML_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>3D Viewer</title>
  <style>
    :root {
      --bg-page: #d7e1ea;
      --bg-panel: rgba(248, 251, 253, 0.92);
      --bg-card: rgba(255, 255, 255, 0.78);
      --line: rgba(20, 44, 60, 0.12);
      --ink: #163042;
      --muted: #5b7383;
      --accent: #0f7b9a;
      --shadow: 0 18px 42px rgba(22, 48, 66, 0.16);
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; height: 100%; }
    body {
      font-family: "Segoe UI", "Hiragino Sans", "Yu Gothic UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(15, 123, 154, 0.18), transparent 25%),
        radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.10), transparent 28%),
        linear-gradient(160deg, #e7edf3, var(--bg-page));
    }
    .app {
      display: grid;
      grid-template-columns: minmax(290px, 350px) 1fr;
      gap: 18px;
      min-height: 100%;
      padding: 18px;
    }
    .panel {
      display: flex;
      flex-direction: column;
      gap: 14px;
      background: var(--bg-panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
      padding: 18px;
    }
    .title {
      font-size: 18px;
      font-weight: 800;
      word-break: break-all;
    }
    .meta {
      font-size: 12px;
      line-height: 1.65;
      color: var(--muted);
    }
    .group {
      background: var(--bg-card);
      border: 1px solid rgba(20, 44, 60, 0.08);
      border-radius: 16px;
      padding: 14px;
    }
    .group h2 {
      margin: 0 0 12px;
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .field {
      display: grid;
      gap: 6px;
      margin-bottom: 12px;
    }
    .field:last-child { margin-bottom: 0; }
    .field label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 13px;
      font-weight: 600;
    }
    .value {
      min-width: 48px;
      text-align: right;
      font-variant-numeric: tabular-nums;
      color: var(--muted);
      font-weight: 500;
    }
    select, input[type="range"], input[type="color"], button {
      width: 100%;
    }
    select, button {
      min-height: 38px;
      padding: 0 12px;
      border-radius: 12px;
      border: 1px solid rgba(20, 44, 60, 0.14);
      background: white;
      color: var(--ink);
      font: inherit;
    }
    input[type="range"] {
      accent-color: var(--accent);
    }
    input[type="color"] {
      height: 38px;
      padding: 4px;
      border-radius: 12px;
      border: 1px solid rgba(20, 44, 60, 0.14);
      background: white;
    }
    button {
      cursor: pointer;
      font-weight: 700;
    }
    .viewer {
      position: relative;
      min-width: 0;
      min-height: calc(100vh - 36px);
      border-radius: 28px;
      overflow: hidden;
      box-shadow: var(--shadow);
      border: 1px solid rgba(20, 44, 60, 0.12);
      background: rgba(255, 255, 255, 0.5);
    }
    #plot {
      width: 100%;
      height: 100%;
    }
    .badge {
      position: absolute;
      left: 18px;
      bottom: 18px;
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.84);
      border: 1px solid rgba(20, 44, 60, 0.10);
      font-size: 12px;
      color: var(--muted);
      pointer-events: none;
      backdrop-filter: blur(8px);
    }
    .status {
      position: absolute;
      top: 18px;
      right: 18px;
      max-width: min(420px, calc(100% - 36px));
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(255, 248, 248, 0.94);
      border: 1px solid rgba(148, 27, 37, 0.16);
      color: #7f1d1d;
      font-size: 13px;
      display: none;
      white-space: pre-wrap;
    }
    @media (max-width: 920px) {
      .app {
        grid-template-columns: 1fr;
      }
      .viewer {
        min-height: 68vh;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="panel">
      <div>
        <div class="title">__MODEL_NAME__</div>
        <div class="meta">
          ダブルクリックで開ける 3D HTML です。<br />
          左ドラッグ: 回転 / ホイール: 拡大縮小 / Shift + 左ドラッグ: 平行移動
        </div>
        <div class="meta" id="meshInfo">__MESH_INFO__</div>
      </div>

      <section class="group">
        <h2>Display</h2>
        <div class="field">
          <label for="displayMode">表示モード</label>
          <select id="displayMode">
            <option value="solid-outline">Solid + Outline</option>
            <option value="solid">Solid</option>
            <option value="outline">Outline</option>
          </select>
        </div>
        <div class="field">
          <label for="axisScaleMode">寸法スケール</label>
          <select id="axisScaleMode">
            <option value="off">Off</option>
            <option value="on">On</option>
          </select>
        </div>
        <div class="field">
          <label for="fitView">視点</label>
          <button id="fitView" type="button">Fit View</button>
        </div>
      </section>

      <section class="group">
        <h2>Axis Scale</h2>
        <div class="field">
          <label for="xScale">X倍率 <span class="value" id="xScaleValue"></span></label>
          <input id="xScale" type="range" min="0.10" max="5.00" step="0.01" value="1.00" />
        </div>
        <div class="field">
          <label for="yScale">Y倍率 <span class="value" id="yScaleValue"></span></label>
          <input id="yScale" type="range" min="0.10" max="5.00" step="0.01" value="1.00" />
        </div>
        <div class="field">
          <label for="zScale">Z倍率 <span class="value" id="zScaleValue"></span></label>
          <input id="zScale" type="range" min="0.10" max="5.00" step="0.01" value="1.00" />
        </div>
      </section>

      <section class="group">
        <h2>Appearance</h2>
        <div class="field">
          <label for="heightColorMode">高低差カラー</label>
          <select id="heightColorMode">
            <option value="off">Off</option>
            <option value="on">On</option>
          </select>
        </div>
        <div class="field">
          <label for="bodyColor">本体色</label>
          <input id="bodyColor" type="color" value="#7f97aa" />
        </div>
        <div class="field">
          <label for="outlineColor">輪郭色</label>
          <input id="outlineColor" type="color" value="#10202c" />
        </div>
        <div class="field">
          <label for="backgroundColor">背景色</label>
          <input id="backgroundColor" type="color" value="#d7e1ea" />
        </div>
        <div class="field">
          <label for="meshOpacity">本体濃度 <span class="value" id="meshOpacityValue"></span></label>
          <input id="meshOpacity" type="range" min="0.15" max="1" step="0.01" value="1.00" />
        </div>
      </section>

      <section class="group">
        <h2>Lighting</h2>
        <div class="field">
          <label for="ambient">Ambient <span class="value" id="ambientValue"></span></label>
          <input id="ambient" type="range" min="0" max="1" step="0.01" value="1.00" />
        </div>
        <div class="field">
          <label for="diffuse">Diffuse <span class="value" id="diffuseValue"></span></label>
          <input id="diffuse" type="range" min="0" max="1" step="0.01" value="0.82" />
        </div>
        <div class="field">
          <label for="specular">Specular <span class="value" id="specularValue"></span></label>
          <input id="specular" type="range" min="0" max="2" step="0.01" value="0.18" />
        </div>
        <div class="field">
          <label for="roughness">Roughness <span class="value" id="roughnessValue"></span></label>
          <input id="roughness" type="range" min="0" max="1" step="0.01" value="0.88" />
        </div>
        <div class="field">
          <label for="fresnel">Fresnel <span class="value" id="fresnelValue"></span></label>
          <input id="fresnel" type="range" min="0" max="3" step="0.01" value="1.00" />
        </div>
      </section>

      <section class="group">
        <h2>Outline</h2>
        <div class="field">
          <label for="edgeWidth">線幅 <span class="value" id="edgeWidthValue"></span></label>
          <input id="edgeWidth" type="range" min="1" max="10" step="1" value="3" />
        </div>
        <div class="field">
          <label for="edgeThreshold">稜線角度 <span class="value" id="edgeThresholdValue"></span></label>
          <input id="edgeThreshold" type="range" min="1" max="85" step="1" value="28" />
        </div>
      </section>
    </aside>

    <main class="viewer">
      <div id="plot"></div>
      <div class="status" id="status"></div>
      <div class="badge">推奨初期値: Solid + Outline</div>
    </main>
  </div>

  <script src="__PLOTLY_CDN__"></script>
  <script>
    const dataModel = __MODEL_DATA__;
    const plot = document.getElementById('plot');
    const status = document.getElementById('status');

    const state = {
      displayMode: 'solid-outline',
      axisScaleMode: 'off',
      xScale: 1.0,
      yScale: 1.0,
      zScale: 1.0,
      heightColorMode: 'off',
      bodyColor: '#7f97aa',
      outlineColor: '#10202c',
      backgroundColor: '#d7e1ea',
      meshOpacity: 1.0,
      ambient: 1.0,
      diffuse: 0.82,
      specular: 0.18,
      roughness: 0.88,
      fresnel: 1.0,
      edgeWidth: 3,
      edgeThreshold: 28,
    };

    function setStatus(message) {
      status.style.display = message ? 'block' : 'none';
      status.textContent = message || '';
    }

    function updateValue(id, value, digits = 2, suffix = '') {
      document.getElementById(id).textContent = `${Number(value).toFixed(digits)}${suffix}`;
    }

    function bindRange(id, key, valueId, digits = 2, suffix = '') {
      const input = document.getElementById(id);
      const apply = () => {
        state[key] = Number(input.value);
        updateValue(valueId, input.value, digits, suffix);
        render();
      };
      input.addEventListener('input', apply);
      updateValue(valueId, input.value, digits, suffix);
    }

    function bindColor(id, key) {
      const input = document.getElementById(id);
      input.addEventListener('input', () => {
        state[key] = input.value;
        render();
      });
    }

    function axisMultiplier(axisKey) {
      if (axisKey === 'x') return state.xScale;
      if (axisKey === 'y') return state.yScale;
      return state.zScale;
    }

    function scaledVertex(vertex) {
      return [
        vertex[0] * state.xScale,
        vertex[1] * state.yScale,
        vertex[2] * state.zScale,
      ];
    }

    function scaledAxisValues(axisKey) {
      const scale = axisMultiplier(axisKey);
      const values = dataModel[axisKey].map((value) => value * scale);
      return values;
    }

    function buildEdgeTrace(thresholdDeg) {
      const xs = [];
      const ys = [];
      const zs = [];
      const edges = dataModel.edges;
      const vertices = dataModel.vertices;

      for (let idx = 0; idx < edges.length; idx += 1) {
        const edge = edges[idx];
        if (edge.angle < thresholdDeg) continue;
        const a = scaledVertex(vertices[edge.a]);
        const b = scaledVertex(vertices[edge.b]);
        xs.push(a[0], b[0], null);
        ys.push(a[1], b[1], null);
        zs.push(a[2], b[2], null);
      }

      return {
        type: 'scatter3d',
        mode: 'lines',
        x: xs,
        y: ys,
        z: zs,
        hoverinfo: 'skip',
        line: {
          color: state.outlineColor,
          width: state.edgeWidth,
        },
        visible: state.displayMode !== 'solid',
        showlegend: false,
      };
    }

    function buildMeshTrace() {
      const scaledX = scaledAxisValues('x');
      const scaledY = scaledAxisValues('y');
      const scaledZ = scaledAxisValues('z');
      const trace = {
        type: 'mesh3d',
        x: scaledX,
        y: scaledY,
        z: scaledZ,
        i: dataModel.i,
        j: dataModel.j,
        k: dataModel.k,
        flatshading: false,
        color: state.bodyColor,
        opacity: state.displayMode === 'outline' ? 0.0 : state.meshOpacity,
        lighting: {
          ambient: state.ambient,
          diffuse: state.diffuse,
          specular: state.specular,
          roughness: state.roughness,
          fresnel: state.fresnel,
        },
        lightposition: { x: 180, y: 220, z: 160 },
        hoverinfo: 'skip',
        showscale: false,
        showlegend: false,
      };

      if (state.heightColorMode === 'on') {
        trace.intensity = scaledZ;
        trace.intensitymode = 'vertex';
        trace.colorscale = 'Turbo';
        trace.cmin = dataModel.zRange[0] * state.zScale;
        trace.cmax = dataModel.zRange[1] * state.zScale;
        trace.showscale = true;
        trace.colorbar = {
          title: { text: 'Height' },
          thickness: 12,
          len: 0.6,
          x: 0.98,
          y: 0.5,
        };
        delete trace.color;
      }

      return trace;
    }

    function buildAxis(axisKey, titleText) {
      const axis = dataModel.axes[axisKey];
      const scale = axisMultiplier(axisKey);
      const visible = state.axisScaleMode === 'on';
      return {
        visible,
        title: { text: visible ? titleText : '' },
        showbackground: false,
        showgrid: visible,
        gridcolor: 'rgba(80, 102, 120, 0.16)',
        zeroline: visible,
        zerolinecolor: 'rgba(80, 102, 120, 0.22)',
        showline: visible,
        linecolor: 'rgba(80, 102, 120, 0.35)',
        ticks: visible ? 'outside' : '',
        ticklen: visible ? 4 : 0,
        tickcolor: 'rgba(56, 76, 92, 0.6)',
        tickvals: visible ? axis.tickvals.map((v) => v * scale) : [],
        ticktext: visible ? axis.ticktext.map((v) => (Number(v) * scale).toFixed(1)) : [],
        range: axis.range.map((v) => v * scale),
      };
    }

    function baseLayout() {
      return {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: { l: 0, r: 0, t: 0, b: 0 },
        showlegend: false,
        scene: {
          bgcolor: state.backgroundColor,
          aspectmode: 'data',
          dragmode: 'orbit',
          camera: dataModel.camera,
          xaxis: buildAxis('x', 'X (mm)'),
          yaxis: buildAxis('y', 'Y (mm)'),
          zaxis: buildAxis('z', 'Z (mm)'),
        },
      };
    }

    function render() {
      const traces = [buildMeshTrace(), buildEdgeTrace(state.edgeThreshold)];
      Plotly.react(plot, traces, baseLayout(), {
        displaylogo: false,
        responsive: true,
        displayModeBar: true,
        scrollZoom: true,
      }).catch((error) => {
        console.error(error);
        setStatus('3D表示の更新に失敗しました。');
      });
    }

    document.getElementById('displayMode').addEventListener('change', (event) => {
      state.displayMode = event.target.value;
      render();
    });
    document.getElementById('axisScaleMode').addEventListener('change', (event) => {
      state.axisScaleMode = event.target.value;
      render();
    });
    document.getElementById('heightColorMode').addEventListener('change', (event) => {
      state.heightColorMode = event.target.value;
      render();
    });
    document.getElementById('fitView').addEventListener('click', () => {
      Plotly.relayout(plot, { 'scene.camera': dataModel.camera });
    });

    bindRange('xScale', 'xScale', 'xScaleValue');
    bindRange('yScale', 'yScale', 'yScaleValue');
    bindRange('zScale', 'zScale', 'zScaleValue');
    bindColor('bodyColor', 'bodyColor');
    bindColor('outlineColor', 'outlineColor');
    bindColor('backgroundColor', 'backgroundColor');
    bindRange('meshOpacity', 'meshOpacity', 'meshOpacityValue');
    bindRange('ambient', 'ambient', 'ambientValue');
    bindRange('diffuse', 'diffuse', 'diffuseValue');
    bindRange('specular', 'specular', 'specularValue');
    bindRange('roughness', 'roughness', 'roughnessValue');
    bindRange('fresnel', 'fresnel', 'fresnelValue');
    bindRange('edgeWidth', 'edgeWidth', 'edgeWidthValue', 0);
    bindRange('edgeThreshold', 'edgeThreshold', 'edgeThresholdValue', 0, '°');

    try {
      render();
      setStatus('');
    } catch (error) {
      console.error(error);
      setStatus('このHTMLを開くのに必要なスクリプトを初期化できませんでした。');
    }
  </script>
</body>
</html>
"""


def ensure_stl(input_path: Path, workdir: Path) -> Path:
    if input_path.suffix.lower() == ".stl":
        return input_path
    if input_path.suffix.lower() in [".step", ".stp"]:
        stl_path = workdir / f"{input_path.stem}.stl"
        import gmsh

        gmsh.initialize()
        try:
            gmsh.open(str(input_path))
            gmsh.write(str(stl_path))
        finally:
            gmsh.finalize()
        return stl_path
    return input_path


def load_mesh(input_path: Path, workdir: Path):
    import trimesh

    mesh_path = ensure_stl(input_path, workdir)
    scene_or_mesh = trimesh.load(mesh_path, force="scene")
    if hasattr(scene_or_mesh, "dump"):
        meshes = [g for g in scene_or_mesh.dump() if hasattr(g, "faces")]
        mesh = trimesh.util.concatenate(meshes)
    else:
        mesh = scene_or_mesh
    mesh = mesh.process(validate=True)
    mesh.merge_vertices()
    return mesh


def decimate_mesh(mesh, target_faces: int):
    import pymeshlab
    import trimesh

    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int32)

    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(vertex_matrix=vertices, face_matrix=faces), "input")
    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=int(max(1000, target_faces)),
        preserveboundary=True,
        boundaryweight=2.0,
        preservenormal=True,
        preservetopology=True,
        planarquadric=True,
        planarweight=0.01,
        autoclean=True,
    )
    current = ms.current_mesh()
    simplified = trimesh.Trimesh(
        vertices=np.asarray(current.vertex_matrix(), dtype=np.float64),
        faces=np.asarray(current.face_matrix(), dtype=np.int64),
        process=False,
    )
    simplified.remove_unreferenced_vertices()
    simplified.merge_vertices()
    return simplified


def simplify_mesh_for_html(mesh):
    face_count = int(len(mesh.faces))
    if face_count <= AUTO_SIMPLIFY_FACE_THRESHOLD:
        return mesh, {
            "original_faces": face_count,
            "final_faces": face_count,
            "simplified": False,
        }

    simplified = decimate_mesh(mesh, AUTO_SIMPLIFY_TARGET_FACES)

    final_faces = int(len(simplified.faces))
    if final_faces > AUTO_SIMPLIFY_HARD_CAP:
        simplified = decimate_mesh(simplified, AUTO_SIMPLIFY_HARD_CAP)
        final_faces = int(len(simplified.faces))

    return simplified, {
        "original_faces": face_count,
        "final_faces": final_faces,
        "simplified": True,
    }


def compute_edges(mesh) -> list[dict[str, float | int]]:
    edge_faces: dict[tuple[int, int], list[int]] = {}
    faces = np.asarray(mesh.faces, dtype=np.int64)
    normals = np.asarray(mesh.face_normals, dtype=np.float64)

    for face_index, face in enumerate(faces):
        tri_edges = ((face[0], face[1]), (face[1], face[2]), (face[2], face[0]))
        for a, b in tri_edges:
            key = (int(min(a, b)), int(max(a, b)))
            edge_faces.setdefault(key, []).append(face_index)

    result: list[dict[str, float | int]] = []
    for (a, b), adjacent_faces in edge_faces.items():
        if len(adjacent_faces) == 1:
            angle = 180.0
        else:
            n1 = normals[adjacent_faces[0]]
            n2 = normals[adjacent_faces[1]]
            cosine = float(np.clip(np.dot(n1, n2), -1.0, 1.0))
            angle = float(np.degrees(np.arccos(cosine)))
        result.append({"a": a, "b": b, "angle": round(angle, 4)})
    return result


def build_model_data(mesh) -> dict:
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    min_corner = vertices.min(axis=0)
    max_corner = vertices.max(axis=0)
    center = (min_corner + max_corner) / 2.0
    vertices = vertices - center

    spans = vertices.max(axis=0) - vertices.min(axis=0)
    max_span = float(max(spans.max(), 1.0))
    eye = {
        "x": 2.35,
        "y": 1.85,
        "z": 1.25,
    }

    def axis_info(index: int) -> dict:
        original_min = float(min_corner[index])
        original_max = float(max_corner[index])
        shifted_min = float(original_min - center[index])
        shifted_max = float(original_max - center[index])
        size = max(original_max - original_min, 0.0)
        step_count = 5
        tickvals = np.linspace(shifted_min, shifted_max, step_count + 1).tolist()
        ticktext = [f"{v:.1f}" for v in np.linspace(0.0, size, step_count + 1)]
        padding = max(size * 0.08, 1.0)
        return {
            "range": [shifted_min - padding, shifted_max + padding],
            "tickvals": tickvals,
            "ticktext": ticktext,
        }

    return {
        "vertices": vertices.tolist(),
        "x": vertices[:, 0].tolist(),
        "y": vertices[:, 1].tolist(),
        "z": vertices[:, 2].tolist(),
        "zRange": [
            float(vertices[:, 2].min()) if len(vertices) else 0.0,
            float(vertices[:, 2].max()) if len(vertices) else 0.0,
        ],
        "i": faces[:, 0].astype(int).tolist(),
        "j": faces[:, 1].astype(int).tolist(),
        "k": faces[:, 2].astype(int).tolist(),
        "edges": compute_edges(mesh),
        "axes": {
            "x": axis_info(0),
            "y": axis_info(1),
            "z": axis_info(2),
        },
        "camera": {
            "center": {"x": 0, "y": 0, "z": 0},
            "eye": {k: float(v * (1.8 if max_span < 1.0 else 1.0)) for k, v in eye.items()},
            "up": {"x": 0, "y": 0, "z": 1},
        },
    }


def estimate_model_payload_bytes(model_data: dict) -> int:
    return len(json.dumps(model_data, ensure_ascii=False).encode("utf-8"))


def fit_mesh_to_size_budget(mesh):
    original_faces = int(len(mesh.faces))
    working = mesh
    simplified = False

    for _ in range(4):
        model_data = build_model_data(working)
        payload_bytes = estimate_model_payload_bytes(model_data)
        estimated_html_bytes = payload_bytes + 250_000
        if estimated_html_bytes <= TARGET_HTML_BYTES:
            return working, model_data, {
                "original_faces": original_faces,
                "final_faces": int(len(working.faces)),
                "simplified": simplified,
                "estimated_html_kb": round(estimated_html_bytes / 1024),
            }

        ratio = TARGET_HTML_BYTES / max(estimated_html_bytes, 1)
        current_faces = int(len(working.faces))
        target_faces = int(max(8_000, current_faces * max(0.35, min(0.85, ratio * 0.92))))
        if target_faces >= current_faces:
            break
        working = decimate_mesh(working, target_faces)
        simplified = True

    model_data = build_model_data(working)
    payload_bytes = estimate_model_payload_bytes(model_data)
    estimated_html_bytes = payload_bytes + 250_000
    return working, model_data, {
        "original_faces": original_faces,
        "final_faces": int(len(working.faces)),
        "simplified": simplified,
        "estimated_html_kb": round(estimated_html_bytes / 1024),
    }


def build_html(model_name: str, model_data: dict, mesh_info: dict) -> str:
    if mesh_info["simplified"]:
        meta = (
            f"HTML表示用に自動軽量化: "
            f"{mesh_info['original_faces']:,} faces -> {mesh_info['final_faces']:,} faces"
        )
    else:
        meta = f"Faces: {mesh_info['final_faces']:,}"
    meta += f" / Est. HTML: {mesh_info['estimated_html_kb']:,} KB"
    return (
        HTML_TEMPLATE.replace("__MODEL_NAME__", html.escape(model_name))
        .replace("__MESH_INFO__", html.escape(meta))
        .replace("__MODEL_DATA__", json.dumps(model_data, ensure_ascii=False))
        .replace("__PLOTLY_CDN__", PLOTLY_CDN)
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_model", type=Path, help="STEP/STL/OBJ/PLY...")
    ap.add_argument("output_html", type=Path)
    args = ap.parse_args()

    args.output_html.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        mesh = load_mesh(args.input_model, td_path)
        mesh, mesh_info = simplify_mesh_for_html(mesh)
        mesh, model_data, budget_info = fit_mesh_to_size_budget(mesh)
        mesh_info.update(budget_info)

        html_text = build_html(
            model_name=args.input_model.name,
            model_data=model_data,
            mesh_info=mesh_info,
        )
        args.output_html.write_text(html_text, encoding="utf-8")


if __name__ == "__main__":
    main()
