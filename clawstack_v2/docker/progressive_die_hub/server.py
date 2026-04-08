"""
server.py — Progressive Die Hub FastAPI バックエンド
"""
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import geometry_processor as gp
import strip_layout as sl
import radioss_generator as rg
import calculix_generator as cg
import report_generator as rep

# ── 定数 ─────────────────────────────────────────────────────────────────────
JOBS_DIR = Path("/tmp/pdie_jobs")
JOBS_DIR.mkdir(parents=True, exist_ok=True)

OPENRADIOSS_CONTAINER = "clawstack-unified-openradioss-1"
ANTIGRAVITY_CONTAINER = "clawstack-unified-clawdbot-gateway-1"

app = FastAPI(title="Progressive Die Hub", version="1.0.0")
app.mount("/static", StaticFiles(directory="/app/static"), name="static")


# ── ユーティリティ ─────────────────────────────────────────────────────────────
def _job_dir(job_id: str) -> Path:
    d = JOBS_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_job(job_id: str) -> dict:
    import json
    p = JOBS_DIR / job_id / "job.json"
    if not p.exists():
        raise HTTPException(404, f"ジョブが見つかりません: {job_id}")
    return json.loads(p.read_text(encoding='utf-8'))


def _save_job(job_id: str, data: dict):
    import json
    p = JOBS_DIR / job_id / "job.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


# ── エンドポイント ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse("/app/static/index.html")


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    """DXF / STEP アップロード → ジオメトリ解析"""
    ext = Path(file.filename).suffix.lower().lstrip('.')
    if ext not in ('dxf', 'stp', 'step'):
        raise HTTPException(400, f"未対応形式: {ext}. DXF または STEP のみ対応")

    job_id  = str(uuid.uuid4())[:8]
    job_dir = _job_dir(job_id)
    saved   = job_dir / file.filename

    content = await file.read()
    saved.write_bytes(content)

    try:
        geom = gp.analyze_file(str(saved), ext)
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(422, f"ファイル解析エラー: {e}")

    _save_job(job_id, {
        'job_id':   job_id,
        'filename': file.filename,
        'ext':      ext,
        'file':     str(saved),
        'geom':     geom,
        'params':   {},
        'layout':   None,
        'fem':      None,
        'calc':     None,
    })

    return JSONResponse({'job_id': job_id, 'geom': geom})


@app.post("/api/strip-layout")
async def strip_layout(
    job_id:        str = Form(...),
    material:      str = Form('SPCC'),
    thickness:     float = Form(1.0),
    bend_radius:   float = Form(1.0),
    bend_angle:    float = Form(90.0),
    strip_margin:  float = Form(1.6),
):
    """ストリップレイアウト生成"""
    if material not in sl.MATERIALS:
        raise HTTPException(400, f"未対応材料: {material}")

    job = _load_job(job_id)
    geom = job['geom']

    try:
        result = sl.run(
            geom=geom,
            material_key=material,
            thickness=thickness,
            bend_radius=bend_radius,
            bend_angle=bend_angle,
            strip_width_margin=strip_margin,
        )
    except Exception as e:
        raise HTTPException(422, f"ストリップレイアウト生成エラー: {e}")

    # SVG ファイル保存
    svg_path = _job_dir(job_id) / "strip_layout.svg"
    svg_path.write_text(result['svg'], encoding='utf-8')

    job['params'] = {
        'material':    material,
        'thickness':   thickness,
        'bend_radius': bend_radius,
        'bend_angle':  bend_angle,
        'filename':    job['filename'],
    }
    # SVG は容量が大きいのでジョブには保存しない
    job['layout'] = {k: v for k, v in result.items() if k != 'svg'}
    job['layout']['svg'] = result['svg']  # レポート用に保持
    _save_job(job_id, job)

    return JSONResponse({
        'job_id':  job_id,
        'summary': result['summary'],
        'stations': result['stations'],
        'blank':   result['blank'],
        'svg':     result['svg'],
    })


@app.post("/api/generate-fem")
async def generate_fem(
    job_id: str = Form(...),
):
    """OpenRadioss + CalculiX 入力デッキ生成"""
    job  = _load_job(job_id)
    geom = job['geom']
    layout = job.get('layout')
    if not layout:
        raise HTTPException(400, "先にストリップレイアウトを生成してください")

    params   = job['params']
    mat_key  = params['material']
    mat      = sl.MATERIALS[mat_key]
    thickness = params['thickness']

    blank    = layout['blank']
    blank_w  = blank['flat_width']
    blank_h  = geom['dimensions']['height']
    stations = layout['stations']
    holes    = geom.get('holes', [])

    # 代表穴径（最初の穴、なければ板厚×2）
    punch_dia = holes[0]['r'] * 2 if holes else thickness * 2.0
    clearance = mat['clearance_ratio'] * thickness

    job_dir_path = str(_job_dir(job_id))

    # ── OpenRadioss 打ち抜き ────────────────────────────────────────────
    blank_result = rg.generate_blanking(
        blank_w, blank_h, thickness,
        punch_dia, mat, clearance, job_dir_path)

    starter_path = _job_dir(job_id) / "blanking_starter.rad"
    engine_path  = _job_dir(job_id) / "blanking_engine.rad"
    starter_path.write_text(blank_result['starter'], encoding='utf-8')
    engine_path.write_text(blank_result['engine'],   encoding='utf-8')

    # ── OpenRadioss V 曲げ ──────────────────────────────────────────────
    bend_result = rg.generate_bending(
        blank_w, thickness,
        params.get('bend_angle', 90.0),
        params.get('bend_radius', 1.0),
        mat, job_dir_path)

    b_starter = _job_dir(job_id) / "bending_starter.rad"
    b_engine  = _job_dir(job_id) / "bending_engine.rad"
    b_starter.write_text(bend_result['starter'], encoding='utf-8')
    b_engine.write_text( bend_result['engine'],  encoding='utf-8')

    # ── CalculiX パンチ強度 ─────────────────────────────────────────────
    # 最も小さい穴のパンチが最も応力集中する → 穴打ち工程のみの力を使用
    hole_station = next((s for s in stations if s['operation'] == 'hole_punch'), None)
    if hole_station:
        punch_force_per_punch = hole_station['punch_force'] / max(1, len(holes))
    else:
        # 穴なし → ノッチ力で代表
        notch_st = next((s for s in stations if s['operation'] == 'notch'), None)
        punch_force_per_punch = (notch_st['punch_force'] if notch_st else 10.0)
    # パンチ長さ = 板厚×15 推奨（座屈を避けるため）
    punch_len = max(20.0, punch_dia * 8.0)
    # ダイ肉厚 = 標準 punch_dia × 1.5 以上（JIS推奨）
    die_wall = max(8.0, punch_dia * 1.5)
    ccx_inp, punch_info = cg.generate_punch_strength(
        punch_dia, punch_len, thickness, punch_force_per_punch)
    ccx_die_inp, die_info = cg.generate_die_insert_strength(
        punch_dia, die_wall, punch_force_per_punch)

    (JOBS_DIR / job_id / "punch_strength.inp").write_text(ccx_inp,     encoding='utf-8')
    (JOBS_DIR / job_id / "die_strength.inp").write_text(  ccx_die_inp, encoding='utf-8')

    job['fem']  = {'blanking': blank_result, 'bending': bend_result}
    job['calc'] = {'punch': punch_info, 'die': die_info}
    _save_job(job_id, job)

    return JSONResponse({
        'job_id': job_id,
        'blanking': blank_result['info'],
        'bending':  bend_result['info'],
        'punch':    punch_info,
        'die':      die_info,
        'files': [
            'blanking_starter.rad',
            'blanking_engine.rad',
            'bending_starter.rad',
            'bending_engine.rad',
            'punch_strength.inp',
            'die_strength.inp',
        ],
    })


@app.post("/api/run-radioss")
async def run_radioss(job_id: str = Form(...)):
    """OpenRadioss コンテナで打ち抜き+曲げ解析を実行"""
    job_dir_path = _job_dir(job_id)

    # コンテナ起動確認（未起動なら起動）
    check = subprocess.run(
        ['docker', 'inspect', '--format', '{{.State.Running}}',
         OPENRADIOSS_CONTAINER],
        capture_output=True, text=True)
    if check.stdout.strip() != 'true':
        try:
            subprocess.run(
                ['docker', 'compose', 'up', '-d', 'openradioss'],
                cwd='/workspace', timeout=30, check=True)
        except Exception as e:
            raise HTTPException(503, f"OpenRadioss コンテナ起動失敗: {e}")

    # 入力ファイルをコンテナへコピー
    for f in ['blanking_starter.rad', 'blanking_engine.rad',
              'bending_starter.rad',  'bending_engine.rad']:
        src = job_dir_path / f
        if src.exists():
            subprocess.run(['docker', 'cp', str(src),
                            f'{OPENRADIOSS_CONTAINER}:/work/{f}'])

    # 実行
    results = {}
    for label, starter, engine in [
        ('blanking', 'blanking_starter', 'blanking_engine'),
        ('bending',  'bending_starter',  'bending_engine'),
    ]:
        r = subprocess.run(
            ['docker', 'exec', OPENRADIOSS_CONTAINER,
             'bash', '-lc',
             f'cd /work && openradioss -nt 2 {starter} {engine} 2>&1 | tail -20'],
            capture_output=True, text=True, timeout=300)
        results[label] = {
            'returncode': r.returncode,
            'stdout':     r.stdout[-2000:],
            'success':    r.returncode == 0,
        }

    return JSONResponse({'job_id': job_id, 'results': results})


@app.post("/api/run-calculix")
async def run_calculix(job_id: str = Form(...)):
    """CalculiX (Antigravity コンテナ) でパンチ強度解析を実行"""
    job_dir_path = _job_dir(job_id)

    check = subprocess.run(
        ['docker', 'inspect', '--format', '{{.State.Running}}',
         ANTIGRAVITY_CONTAINER],
        capture_output=True, text=True)
    if check.stdout.strip() != 'true':
        raise HTTPException(503,
            "Antigravity コンテナが未起動です。"
            "`docker compose up -d antigravity` で起動してください")

    results = {}
    for inp_file in ['punch_strength', 'die_strength']:
        src = job_dir_path / f'{inp_file}.inp'
        if not src.exists():
            continue
        subprocess.run(['docker', 'cp', str(src),
                        f'{ANTIGRAVITY_CONTAINER}:/tmp/{inp_file}.inp'])
        r = subprocess.run(
            ['docker', 'exec', ANTIGRAVITY_CONTAINER,
             'bash', '-lc',
             f'cd /tmp && ccx {inp_file} 2>&1 | tail -20'],
            capture_output=True, text=True, timeout=120)
        results[inp_file] = {
            'returncode': r.returncode,
            'stdout':     r.stdout[-2000:],
            'success':    r.returncode == 0,
        }

    return JSONResponse({'job_id': job_id, 'results': results})


@app.get("/api/report/{job_id}", response_class=HTMLResponse)
async def get_report(job_id: str):
    """HTML 報告書生成・返却"""
    job = _load_job(job_id)

    html = rep.generate(
        geom=job['geom'],
        layout=job.get('layout') or {},
        fem_blanking=(job.get('fem') or {}).get('blanking'),
        fem_bending= (job.get('fem') or {}).get('bending'),
        calc_punch=  (job.get('calc') or {}).get('punch'),
        calc_die=    (job.get('calc') or {}).get('die'),
        params=job.get('params') or {},
    )

    report_path = _job_dir(job_id) / "report.html"
    report_path.write_text(html, encoding='utf-8')
    return HTMLResponse(html)


@app.get("/api/download/{job_id}/{filename}")
async def download(job_id: str, filename: str):
    """FEM 入力ファイルダウンロード"""
    p = _job_dir(job_id) / filename
    if not p.exists():
        raise HTTPException(404, f"{filename} が見つかりません")
    return FileResponse(str(p), filename=filename)


@app.get("/api/materials")
async def get_materials():
    return JSONResponse({k: {
        'name': v['name'],
        'E': v['E'], 'nu': v['nu'],
        'yield_stress': v['yield_stress'],
        'uts': v['uts'],
        'k_factor': v['k_factor'],
    } for k, v in sl.MATERIALS.items()})


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "progressive_die_hub"}
