"""Windows ホスト直接実行ランナー
Docker不要。Windows Blender + ホストPython で動作。
低優先度プロセスでバックグラウンド実行。

使い方:
  python run_host.py               # 未処理PDFを1本
  python run_host.py --limit 3     # 3本
  python run_host.py --pdf "..."   # 特定PDF
"""
import sys, os, json, subprocess, time, tempfile, wave, hashlib, requests
from pathlib import Path

# パス設定
ROOT       = Path(__file__).parent.parent.parent.parent  # d:/Clawdbot_Docker_20260125
PDF_DIR    = ROOT / "iatf_system/db/documents"
OUTPUT_DIR = ROOT / "data/iatf_videos"
AUDIO_DIR  = Path(tempfile.gettempdir()) / "iatf_audio"
LOG_FILE   = OUTPUT_DIR / "generation.log"

BLENDER_BIN  = r"C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"
FFMPEG_BIN   = os.getenv("FFMPEG_BIN", r"C:/Users/yasu/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1-full_build/bin/ffmpeg.exe")
LITELLM_URL  = os.getenv("LITELLM_URL",  "http://localhost:4001")
LITELLM_KEY  = os.getenv("LITELLM_MASTER_KEY", "local-dev-key")
VOICEVOX_URL = os.getenv("VOICEVOX_URL", "http://localhost:50021")

# .envからAPI keyをロード（LiteLLM未達時の直接フォールバック用）
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _, _v = _line.partition("=")
            if _k.strip() not in os.environ:
                os.environ[_k.strip()] = _v.strip()

sys.path.insert(0, str(Path(__file__).parent / "pipeline"))

# ── ロガー ────────────────────────────────────────────────────────
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ── DB（省略可能）───────────────────────────────────────────────
def _try_db_insert(pdf_name, clause, topic):
    try:
        import psycopg2
        pg_pw = os.environ.get("POSTGRES_PASSWORD", "change_me")
        db = psycopg2.connect(f"postgresql://postgres:{pg_pw}@localhost:5432/sim_trials?connect_timeout=5")
        with db, db.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS generated_videos (
                id SERIAL PRIMARY KEY, pdf_name TEXT, clause TEXT, topic TEXT,
                output_mp4 TEXT, status TEXT DEFAULT 'pending',
                model_used TEXT, duration_sec FLOAT, error_msg TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
            )""")
            cur.execute(
                "INSERT INTO generated_videos (pdf_name, clause, topic, status) VALUES (%s,%s,%s,'running') RETURNING id",
                (pdf_name, clause, topic))
            row_id = cur.fetchone()[0]
        db.close()
        return row_id
    except Exception as e:
        log(f"  DB skip: {e}")
        return None

def _try_db_update(row_id, status, output_mp4=None, model_used=None, error_msg=None):
    if row_id is None:
        return
    try:
        import psycopg2
        pg_pw = os.environ.get("POSTGRES_PASSWORD", "change_me")
        db = psycopg2.connect(f"postgresql://postgres:{pg_pw}@localhost:5432/sim_trials?connect_timeout=5")
        with db, db.cursor() as cur:
            cur.execute(
                "UPDATE generated_videos SET status=%s, output_mp4=%s, model_used=%s, error_msg=%s, updated_at=NOW() WHERE id=%s",
                (status, output_mp4, model_used, error_msg, row_id))
        db.close()
    except Exception:
        pass


# ── 生成済みチェック ─────────────────────────────────────────────
def _is_done(pdf_name):
    mp4 = OUTPUT_DIR / Path(pdf_name).stem / f"{Path(pdf_name).stem}.mp4"
    return mp4.exists()


# ── PDF抽出 ─────────────────────────────────────────────────────
def extract_pdf(pdf_path: Path) -> str:
    from pdf_extractor import extract_pdf as _ex
    return _ex(pdf_path)


# ── 台本生成 ─────────────────────────────────────────────────────
def generate_script(pdf_text: str, clause: str, topic: str) -> dict:
    from script_generator import generate_script as _gen
    return _gen(pdf_text, clause, topic)


# ── TTS ─────────────────────────────────────────────────────────
def render_audio(script: dict, audio_dir: Path) -> list:
    from tts_renderer import render_script_audio
    return render_script_audio(script, audio_dir)


# ── Rhubarb（スキップ可）→ 基本リップシンクフォールバック ───────
def build_phonemes_fallback(timeline: list) -> list:
    """Rhubarbなしの場合：発話区間をAフォネームで埋める簡易フォールバック。"""
    phonemes = []
    for entry in timeline:
        start = entry["start_sec"]
        end   = start + entry["duration_sec"]
        step  = 0.1  # 100msごとにAフォネーム
        t = start
        while t < end - 0.05:
            phonemes.append({
                "character": entry["character"],
                "start": t,
                "end":   min(t + step, end),
                "value": "A",
            })
            t += step
    return phonemes


# ── Blender レンダリング ─────────────────────────────────────────
def render_blender(timeline: list, phonemes: list, frames_dir: Path, fps=30) -> bool:
    from blender_animator import generate_blender_script
    script_str = generate_blender_script(timeline, phonemes, frames_dir)
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", encoding="utf-8", delete=False) as tmp:
        tmp.write(script_str)
        script_path = Path(tmp.name)

    cmd = [BLENDER_BIN, "--background", "--python", str(script_path)]
    log(f"  Blender起動: {' '.join(cmd[:2])} ...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=None)
    script_path.unlink(missing_ok=True)
    if result.returncode != 0:
        log(f"  Blender ERROR (last 500):\n{result.stderr[-500:]}")
        return False
    log("  Blender完了")
    return True


def visual_qa_frames(frames_dir: Path, video_dir: Path) -> dict:
    from visual_qa import assert_visual_quality

    report_dir = video_dir / "visual_qa"
    report = assert_visual_quality(frames_dir, report_dir)
    log(f"  Visual QA OK: {report['frame_count']} frames / {report.get('contact_sheet')}")
    return report


def slide_preflight_gate(script: dict, timeline: list, video_dir: Path, title: str) -> dict:
    from slide_preflight import run_slide_preflight

    report = run_slide_preflight(script, timeline, video_dir, title)
    log(f"  Slide preflight OK: {report['contact_sheet']}")
    return report


def compose_approved_slide_video(video_dir: Path, stem: str) -> Path:
    from slide_video_builder import build_reviewed_slide_video

    report = build_reviewed_slide_video(
        video_dir,
        reviewer=os.getenv("IATF_VIDEO_REVIEWER_NAME", "Configured AI visual review gate"),
        review_note="Slide preflight approved; composing reviewed slide video.",
        output_name=f"{stem}_slide_reviewed.mp4",
    )
    log(f"  Slide video OK: {report['output_mp4']}")
    log(f"  Spot check OK: {report['spot_check']['contact_sheet']}")
    return Path(report["output_mp4"])


# ── 字幕SRT生成 ──────────────────────────────────────────────────
def _sec_to_srt(s: float) -> str:
    h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")

def generate_srt(timeline: list, out_path: Path):
    lines = []
    for i, e in enumerate(timeline, 1):
        lines.append(str(i))
        lines.append(f"{_sec_to_srt(e['start_sec'])} --> {_sec_to_srt(e['start_sec'] + e['duration_sec'])}")
        char_jp = {"bulma":"ブルマ","goku":"悟空","gohan":"御飯","android17":"17号",
                   "android18":"18号","roshi":"亀仙人","trunks":"トランクス"}.get(e["character"], e["character"])
        lines.append(f"【{char_jp}】{e['text']}")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ── FFmpeg 合成 ───────────────────────────────────────────────────
def compose_mp4(timeline: list, frames_dir: Path, video_dir: Path, pdf_stem: str, total_sec: float, fps=30) -> Path:
    # 1. 音声合成
    master_wav = video_dir / "master_audio.wav"
    inputs, filters = [], []
    for i, e in enumerate(timeline):
        inputs += ["-i", e["wav"]]
        d = int(e["start_sec"] * 1000)
        filters.append(f"[{i}]adelay={d}|{d}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(timeline)))
    filters.append(f"{mix}amix=inputs={len(timeline)}:duration=longest[aout]")
    subprocess.run(
        [FFMPEG_BIN, "-y"] + inputs +
        ["-filter_complex", ";".join(filters), "-map", "[aout]", "-t", str(total_sec), str(master_wav)],
        check=True, capture_output=True, timeout=300)

    # 2. 字幕SRT生成
    srt_path = video_dir / "subtitles.srt"
    generate_srt(timeline, srt_path)

    # 3. タイトルカード用フレームを先頭5秒分追加（黒背景+テキスト）
    # 4. フレーム連番+音声+字幕→MP4
    raw_mp4 = video_dir / "raw_render.mp4"
    frame_pattern = str(frames_dir / "frame_%04d.png")
    subprocess.run([
        FFMPEG_BIN, "-y",
        "-framerate", str(fps), "-i", frame_pattern,
        "-i", str(master_wav),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest",
        str(raw_mp4),
    ], check=True, capture_output=True, timeout=3600)

    # 5. 字幕焼き込み
    output_mp4 = video_dir / f"{pdf_stem}.mp4"
    try:
        subprocess.run([
            FFMPEG_BIN, "-y", "-i", str(raw_mp4),
            "-vf", f"subtitles={str(srt_path).replace(chr(92), '/')}:force_style='FontSize=20,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2'",
            "-c:a", "copy",
            str(output_mp4),
        ], check=True, capture_output=True, timeout=3600)
    except Exception:
        log("  字幕焼き込みスキップ（libassなし）")
        raw_mp4.rename(output_mp4)

    return output_mp4


# ── メインパイプライン ───────────────────────────────────────────
def process_pdf(pdf_path: Path) -> bool:
    stem   = pdf_path.stem
    parts  = stem.replace("箇条", "").split("_")
    clause = parts[1].strip() if len(parts) > 1 else "?"
    topic  = parts[2].strip() if len(parts) > 2 else stem

    log(f"\n{'='*60}")
    log(f"PDF: {pdf_path.name}")
    log(f"箇条: {clause}  トピック: {topic}")
    log(f"{'='*60}")

    video_dir  = OUTPUT_DIR / stem
    frames_dir = video_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    audio_dir  = AUDIO_DIR / stem
    audio_dir.mkdir(parents=True, exist_ok=True)

    row_id = _try_db_insert(pdf_path.name, clause, topic)

    script_json_path   = video_dir / "script.json"
    timeline_json_path = video_dir / "timeline.json"
    model = "unknown"

    try:
        # Resume: skip steps 1-4 if intermediate files already exist
        if script_json_path.exists() and timeline_json_path.exists():
            log("[1-4/6] resume: script.json + timeline.json 検出 → スキップ")
            script   = json.loads(script_json_path.read_text(encoding="utf-8"))
            timeline = json.loads(timeline_json_path.read_text(encoding="utf-8"))
            total_sec = max(e["start_sec"] + e["duration_sec"] for e in timeline) + 2.0
            model = script.get("model_used", "resume")
        else:
            log("[1/6] PDF抽出...")
            pdf_text = extract_pdf(pdf_path)
            log(f"      {len(pdf_text):,} 文字")

            log("[2/6] 台本生成 (Kimi K2.6 / max_tokens=8000)...")
            script = generate_script(pdf_text, clause, topic)
            model  = script.get("model_used", "?")
            scenes = len(script.get("scenes", []))
            log(f"      model={model}, {scenes}場面")
            script_json_path.write_text(
                json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

            log("[3/6] TTS音声生成 (VoiceVox)...")
            timeline = render_audio(script, audio_dir)
            total_sec = max(e["start_sec"] + e["duration_sec"] for e in timeline) + 2.0
            log(f"      {len(timeline)}行, 合計{total_sec:.1f}秒")
            timeline_json_path.write_text(
                json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

        log("[3.5/6] Slide preflight: generate slides + AI visual review gate...")
        slide_preflight_gate(script, timeline, video_dir, stem)

        render_mode = os.getenv("IATF_VIDEO_RENDER_MODE", "slides").strip().lower()
        if render_mode == "slides":
            log("[4-6/6] Approved slide video compose + periodic spot checks...")
            output_mp4 = compose_approved_slide_video(video_dir, stem)
            _try_db_update(row_id, "done", str(output_mp4), model)
            return True

        log("[4/6] リップシンク (フォールバックモード)...")
        phonemes = build_phonemes_fallback(timeline)
        log(f"      {len(phonemes)}フォネームエントリ")

        existing_frames = len(list(frames_dir.glob("frame_*.png")))
        expected_frames = int(total_sec * 30)
        if existing_frames >= expected_frames * 0.95:
            log(f"[5/6] Blenderレンダリング skip: {existing_frames}フレーム既存 (期待値{expected_frames}の95%以上)")
        else:
            log("[5/6] Blenderレンダリング...")
            ok = render_blender(timeline, phonemes, frames_dir)
            if not ok:
                raise RuntimeError("Blenderレンダリング失敗")

        log("[5.5/6] Visual QA: sample frames + contact sheet...")
        visual_qa_frames(frames_dir, video_dir)

        log("[6/6] FFmpeg MP4合成 + 字幕焼き込み...")
        output_mp4 = compose_mp4(timeline, frames_dir, video_dir, stem, total_sec)
        log(f"  完了: {output_mp4}")

        _try_db_update(row_id, "done", str(output_mp4), model)
        return True

    except Exception as e:
        log(f"  ERROR: {e}")
        _try_db_update(row_id, "error", error_msg=str(e))
        return False


def list_pending(limit: int) -> list[Path]:
    pdfs = sorted(PDF_DIR.glob("IATF 16949 内部監査資料*.pdf"))
    return [p for p in pdfs if not _is_done(p.name)][:limit]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf",   help="特定PDFパス")
    ap.add_argument("--limit", type=int, default=1)
    args = ap.parse_args()

    # Windowsプロセス優先度を「低」に設定
    try:
        import psutil
        p = psutil.Process()
        p.nice(psutil.IDLE_PRIORITY_CLASS)
        log("プロセス優先度: IDLE (低)")
    except Exception:
        log("psutil未インストール - 通常優先度で実行")

    if args.pdf:
        process_pdf(Path(args.pdf))
    else:
        pending = list_pending(args.limit)
        log(f"未処理PDF: {len(pending)}本")
        for pdf in pending:
            process_pdf(pdf)
