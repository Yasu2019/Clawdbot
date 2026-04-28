"""IATF動画エディタ API — FastAPI (port 18797)
タイムスタンプ + 自然言語指示 → Blenderパッチ → 部分再レンダリング → MP4
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os, json, tempfile
from pathlib import Path

from edit_engine import generate_patch, apply_patch_to_blend, render_segment
from video_composer_local import replace_segment

BLENDER_BIN     = os.getenv("BLENDER_BIN", "blender")
IATF_VIDEO_ROOT = Path(os.getenv("IATF_VIDEO_ROOT", "/data/iatf_videos"))

app = FastAPI(title="IATF Video Editor API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── リクエスト/レスポンスモデル ───────────────────────────────────

class VideoListItem(BaseModel):
    name:        str
    mp4_path:    str
    duration_sec: float | None = None

class EditRequest(BaseModel):
    video_name:    str
    timestamp_sec: float
    end_sec:       float
    character:     str
    instruction:   str

class EditResponse(BaseModel):
    job_id:       str
    patch_script: str
    status:       str

class ApplyRequest(BaseModel):
    job_id:       str
    video_name:   str
    patch_script: str
    start_sec:    float
    end_sec:      float

class ExportResponse(BaseModel):
    output_mp4: str


# ── ジョブステータス (インメモリ、簡易版) ────────────────────────
_jobs: dict[str, dict] = {}


# ── エンドポイント ────────────────────────────────────────────────

@app.get("/videos", response_model=list[VideoListItem])
def list_videos():
    """生成済みMP4一覧を返す。"""
    results = []
    for mp4 in sorted(IATF_VIDEO_ROOT.rglob("*.mp4")):
        results.append(VideoListItem(
            name=mp4.stem,
            mp4_path=str(mp4),
        ))
    return results


@app.get("/video/{video_name}/stream")
def stream_video(video_name: str):
    """MP4ファイルをストリーミング配信する。"""
    mp4 = _find_mp4(video_name)
    if not mp4:
        raise HTTPException(404, f"{video_name} not found")
    return FileResponse(mp4, media_type="video/mp4")


@app.get("/video/{video_name}/timeline")
def get_timeline(video_name: str):
    """タイムラインJSONを返す（台本情報）。"""
    video_dir = IATF_VIDEO_ROOT / video_name
    timeline_json = video_dir / "timeline.json"
    if not timeline_json.exists():
        return []
    return json.loads(timeline_json.read_text(encoding="utf-8"))


@app.post("/edit/generate", response_model=EditResponse)
def generate_edit(req: EditRequest):
    """自然言語指示からBlenderパッチを生成する（未適用）。"""
    import uuid
    job_id = str(uuid.uuid4())[:8]

    patch = generate_patch(
        instruction=req.instruction,
        timestamp_sec=req.timestamp_sec,
        character=req.character,
        video_meta={"video_name": req.video_name},
    )
    _jobs[job_id] = {
        "status": "generated",
        "patch": patch,
        "video_name": req.video_name,
        "start_sec": req.timestamp_sec,
        "end_sec": req.end_sec,
        "character": req.character,
        "instruction": req.instruction,
    }
    return EditResponse(job_id=job_id, patch_script=patch, status="generated")


@app.post("/edit/apply", response_model=ExportResponse)
def apply_edit(req: ApplyRequest):
    """パッチを適用して部分再レンダリングし、MP4を差し替えた新ファイルを返す。"""
    video_dir = IATF_VIDEO_ROOT / req.video_name
    mp4 = _find_mp4(req.video_name)
    if not mp4:
        raise HTTPException(404, f"MP4 not found: {req.video_name}")

    blend_file = video_dir / f"{req.video_name}.blend"
    if not blend_file.exists():
        raise HTTPException(404, "blendファイルが見つかりません。再レンダリング機能には.blendが必要です。")

    # 1. パッチ適用 → blendを上書き
    ok = apply_patch_to_blend(blend_file, req.patch_script, BLENDER_BIN)
    if not ok:
        raise HTTPException(500, "Blenderパッチ適用失敗")

    # 2. 部分再レンダリング
    fps = 30
    start_frame = max(0, int(req.start_sec * fps) - 3)
    end_frame   = int(req.end_sec * fps) + 3

    patch_frames = video_dir / "patch_frames"
    patch_frames.mkdir(exist_ok=True)
    ok = render_segment(blend_file, start_frame, end_frame, patch_frames, BLENDER_BIN)
    if not ok:
        raise HTTPException(500, "部分レンダリング失敗")

    # 3. パッチフレーム → 一時MP4
    patch_mp4 = video_dir / "patch_segment.mp4"
    import subprocess
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(patch_frames / "frame_%04d.png"),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        str(patch_mp4),
    ], check=True, timeout=600)

    # 4. セグメント差し替え
    output_mp4 = video_dir / f"{req.video_name}_edited_{req.job_id}.mp4"
    ok = replace_segment(mp4, patch_mp4, req.start_sec, req.end_sec, output_mp4)
    if not ok:
        raise HTTPException(500, "FFmpegセグメント差し替え失敗")

    if req.job_id in _jobs:
        _jobs[req.job_id]["status"] = "applied"
        _jobs[req.job_id]["output"] = str(output_mp4)

    return ExportResponse(output_mp4=str(output_mp4))


@app.get("/job/{job_id}")
def get_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


# ── ユーティリティ ────────────────────────────────────────────────

def _find_mp4(video_name: str) -> Path | None:
    for mp4 in IATF_VIDEO_ROOT.rglob(f"{video_name}.mp4"):
        return mp4
    return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18797)
