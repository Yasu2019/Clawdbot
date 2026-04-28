"""IATF動画工場 オーケストレーター
PDF → 台本 → TTS → Rhubarb → Blender → FFmpeg → MP4
"""
import json, os, sys, tempfile, time
from pathlib import Path
import psycopg2

# パスをsys.pathに追加
sys.path.insert(0, str(Path(__file__).parent))

from pdf_extractor     import extract_pdf, list_audit_pdfs
from script_generator  import generate_script
from tts_renderer      import render_script_audio
from rhubarb_runner    import build_phoneme_timeline
from blender_animator  import generate_blender_script, run_blender
from video_composer    import merge_audio_tracks, compose_video

OUTPUT_ROOT   = Path(os.getenv("IATF_VIDEO_OUTPUT", "/data/iatf_videos"))
AUDIO_ROOT    = Path(os.getenv("IATF_AUDIO_CACHE",  "/tmp/iatf_audio"))
BLENDER_BIN   = os.getenv("BLENDER_BIN", "blender")
RHUBARB_BIN   = os.getenv("RHUBARB_BIN", "/usr/local/bin/rhubarb")

DB_DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/sim_trials"
)


# ── DB操作 ──────────────────────────────────────────────────────────

def _db_conn():
    return psycopg2.connect(DB_DSN)


def _ensure_table():
    with _db_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS generated_videos (
                id           SERIAL PRIMARY KEY,
                pdf_name     TEXT NOT NULL,
                clause       TEXT,
                topic        TEXT,
                output_mp4   TEXT,
                status       TEXT DEFAULT 'pending',
                model_used   TEXT,
                duration_sec FLOAT,
                error_msg    TEXT,
                created_at   TIMESTAMPTZ DEFAULT NOW(),
                updated_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.commit()


def _db_insert(pdf_name: str, clause: str, topic: str) -> int:
    with _db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO generated_videos (pdf_name, clause, topic, status) "
            "VALUES (%s, %s, %s, 'running') RETURNING id",
            (pdf_name, clause, topic)
        )
        row_id = cur.fetchone()[0]
        conn.commit()
    return row_id


def _db_update(row_id: int, status: str, output_mp4: str = None,
               model_used: str = None, duration_sec: float = None,
               error_msg: str = None):
    with _db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE generated_videos SET status=%s, output_mp4=%s, model_used=%s, "
            "duration_sec=%s, error_msg=%s, updated_at=NOW() WHERE id=%s",
            (status, output_mp4, model_used, duration_sec, error_msg, row_id)
        )
        conn.commit()


def _already_done(pdf_name: str) -> bool:
    with _db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM generated_videos WHERE pdf_name=%s AND status='done'",
            (pdf_name,)
        )
        return cur.fetchone() is not None


# ── パイプライン本体 ────────────────────────────────────────────────

def process_pdf(pdf_path: Path, force: bool = False) -> bool:
    _ensure_table()
    pdf_name = pdf_path.name

    if not force and _already_done(pdf_name):
        print(f"  SKIP (already done): {pdf_name}")
        return True

    # 箇条番号・トピックをファイル名から推測
    # 例: "IATF 16949 内部監査資料_8.5.4_梱包工程.pdf"
    parts = pdf_path.stem.split("_")
    clause = parts[1] if len(parts) > 1 else "?"
    topic  = parts[2] if len(parts) > 2 else pdf_path.stem

    row_id = _db_insert(pdf_name, clause, topic)
    print(f"\n{'='*60}")
    print(f"[{row_id}] {pdf_name}")
    print(f"{'='*60}")

    try:
        # 1. PDF抽出
        print("  [1/6] PDF抽出...")
        pdf_text = extract_pdf(pdf_path)
        print(f"        {len(pdf_text)} chars")

        # 2. 台本生成
        print("  [2/6] 台本生成 (Kimi K2.6)...")
        script = generate_script(pdf_text, clause, topic)
        model_used = script.get("model_used", "unknown")
        print(f"        model={model_used}, scenes={len(script.get('scenes',[]))}")

        # 3. TTS音声生成
        print("  [3/6] TTS音声生成 (VoiceVox)...")
        audio_dir = AUDIO_ROOT / pdf_path.stem
        timeline = render_script_audio(script, audio_dir)
        print(f"        {len(timeline)} lines, total={sum(e['duration_sec'] for e in timeline):.1f}s")

        if not timeline:
            raise RuntimeError("TTS timeline empty")

        total_sec = max(e["start_sec"] + e["duration_sec"] for e in timeline) + 2.0

        # 4. Rhubarb リップシンク
        print("  [4/6] Rhubarb リップシンク...")
        phoneme_data = build_phoneme_timeline(timeline, RHUBARB_BIN)
        print(f"        {len(phoneme_data)} phoneme entries")

        # 5. Blenderレンダリング
        print("  [5/6] Blenderレンダリング...")
        video_dir = OUTPUT_ROOT / pdf_path.stem
        frames_dir = video_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        blender_script_str = generate_blender_script(timeline, phoneme_data, frames_dir)
        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(blender_script_str)
            script_path = Path(tmp.name)

        ok = run_blender(script_path, BLENDER_BIN)
        script_path.unlink(missing_ok=True)
        if not ok:
            raise RuntimeError("Blender render failed")

        # 6. FFmpeg合成
        print("  [6/6] FFmpeg MP4合成...")
        master_wav = video_dir / "master_audio.wav"
        merge_audio_tracks(timeline, total_sec, master_wav)

        output_mp4 = video_dir / f"{pdf_path.stem}.mp4"
        ok = compose_video(frames_dir, master_wav, output_mp4)
        if not ok:
            raise RuntimeError("FFmpeg compose failed")

        print(f"  DONE: {output_mp4}")
        _db_update(row_id, "done", str(output_mp4), model_used, total_sec)
        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        _db_update(row_id, "error", error_msg=str(e))
        return False


def run_batch(limit: int = 1, force: bool = False):
    """未処理PDFをlimit本だけ処理する。n8n cronから呼び出す。"""
    pdfs = list_audit_pdfs()
    print(f"Found {len(pdfs)} PDFs")
    done = 0
    for pdf in pdfs:
        if done >= limit:
            break
        if not force and _already_done(pdf.name):
            continue
        ok = process_pdf(pdf, force=force)
        if ok:
            done += 1
    print(f"\nBatch complete: {done}/{limit} processed")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf",   help="特定PDFのみ処理")
    ap.add_argument("--limit", type=int, default=1, help="バッチ処理本数 (default=1)")
    ap.add_argument("--force", action="store_true",   help="処理済みも再処理")
    args = ap.parse_args()

    if args.pdf:
        process_pdf(Path(args.pdf), force=args.force)
    else:
        run_batch(limit=args.limit, force=args.force)
