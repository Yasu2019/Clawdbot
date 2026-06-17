#!/usr/bin/env python3
"""IATF Video Thumbnail Generator & AI QA Checker

1. Scans data/iatf_videos/ for *_slide_reviewed.mp4
2. Extracts thumbnail at 5s using ffmpeg
3. Reads script.json for topic/clause/dialogue
4. Calls Gemini Vision to verify thumbnail matches script content
5. Saves results to data/workspace/apps/growth_dashboard/iatf_video_qa_status.json
"""
import sys, os, json, subprocess, base64, re, time, hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

# ── paths ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = REPO_ROOT / "data" / "iatf_videos"
THUMB_OUT = REPO_ROOT / "data" / "workspace" / "apps" / "growth_dashboard" / "iatf_thumbnails"
QA_STATUS = REPO_ROOT / "data" / "workspace" / "apps" / "growth_dashboard" / "iatf_video_qa_status.json"
INCIDENT_LOG = REPO_ROOT / "data" / "workspace" / "iatf_video_qa_incidents.jsonl"

THUMB_OUT.mkdir(parents=True, exist_ok=True)

# ── load .env GEMINI_API_KEY ───────────────────────────────────────────────
def _load_env():
    p = REPO_ROOT
    for _ in range(6):
        env_file = p / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
        if p.parent == p:
            break
        p = p.parent

_load_env()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

# ── helpers ────────────────────────────────────────────────────────────────
def safe_name(text: str) -> str:
    """Create filesystem-safe short name from video title."""
    text = re.sub(r"[^\w　-鿿゠-ヿ぀-ゟ]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:80]

def extract_thumbnail(mp4: Path, out: Path) -> bool:
    """Extract frame at 5s. Returns True on success."""
    cmd = [
        "ffmpeg", "-y", "-ss", "5", "-i", str(mp4),
        "-vframes", "1", "-q:v", "3", "-vf", "scale=480:-1",
        str(out)
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    return out.exists() and out.stat().st_size > 1000

def probe_duration(mp4: Path) -> float | None:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(mp4)],
        capture_output=True, text=True, timeout=10
    )
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return None

def read_script(folder: Path) -> dict:
    """Read script.json; return clause/topic/summary or {}."""
    s = folder / "script.json"
    if not s.exists():
        return {}
    try:
        d = json.loads(s.read_bytes().decode("utf-8"))
        clause = d.get("clause", "")
        topic = d.get("topic", "")
        scenes = d.get("scenes", [])
        texts = []
        for sc in scenes[:5]:
            dlg = sc.get("dialogue", [])
            for line in dlg[:2]:
                t = line.get("text", "")
                if t and t not in ("...", ""):
                    texts.append(t[:120])
        return {
            "clause": clause,
            "topic": topic,
            "scene_count": len(scenes),
            "summary": " / ".join(texts[:4]),
        }
    except Exception as e:
        return {"error": str(e)}

def load_contact_sheet(folder: Path) -> Path | None:
    """Return slide_preflight/contact_sheet.jpg if it exists."""
    cs = folder / "slide_preflight" / "contact_sheet.jpg"
    return cs if cs.exists() else None

def image_to_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()

def _extract_json_from_text(text: str) -> dict | None:
    """Robustly extract first JSON object from Gemini response text."""
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    # Try raw_decode from each '{'
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text, m.start())
            if isinstance(obj, dict) and "match" in obj:
                return obj
        except json.JSONDecodeError:
            continue
    # Last resort: extract key-value pairs manually
    result = {}
    for key in ("match", "score", "reason", "slide_text_found"):
        pat = rf'"{key}"\s*:\s*([^,\n\}}]+)'
        m2 = re.search(pat, text)
        if m2:
            val = m2.group(1).strip().strip('"')
            if key == "match":
                result[key] = val.lower() in ("true", "1", "yes")
            elif key == "score":
                try:
                    result[key] = int(re.search(r"\d+", val).group())
                except Exception:
                    result[key] = 0
            else:
                result[key] = val[:200]
    issues_m = re.search(r'"issues"\s*:\s*\[([^\]]*)\]', text, re.DOTALL)
    if issues_m:
        result["issues"] = [s.strip().strip('"') for s in issues_m.group(1).split(",") if s.strip()]
    return result if "match" in result else None

def gemini_vision_qa(thumbnail: Path, contact: Path | None, script_info: dict) -> dict:
    """Call Gemini Vision to check thumbnail/slides against script. Returns QA dict."""
    if not GEMINI_KEY:
        return {"status": "skip", "reason": "GEMINI_API_KEY not set"}

    # Prefer contact sheet (shows all slides) over single thumbnail
    qa_image = contact if contact else thumbnail
    if not qa_image or not qa_image.exists():
        return {"status": "skip", "reason": "no image available"}

    topic = script_info.get("topic", "unknown")
    clause = script_info.get("clause", "unknown")
    summary = script_info.get("summary", "")

    prompt = (
        f"You are a QA reviewer for IATF 16949 internal audit training videos. "
        f"The image shows slide(s) from a video titled 'Clause {clause}: {topic}'. "
        f"Script summary: {summary[:300]}. "
        f"Check: (1) Do slide titles/content match clause {clause} / {topic}? "
        f"(2) Is the script content reflected in the slides? "
        f"(3) Any clearly wrong or unrelated content? "
        f"Reply ONLY with a JSON object (no markdown, no explanation): "
        f'{{ "match": true/false, "score": 0-100, "issues": [], '
        f'"reason": "one sentence", "slide_text_found": "keywords" }}'
    )

    try:
        import urllib.request
        body = json.dumps({
            "model": "gemini-2.5-flash",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_to_b64(qa_image)}"
                    }},
                    {"type": "text", "text": prompt}
                ]
            }],
            "max_tokens": 512
        }).encode("utf-8")

        req = urllib.request.Request(
            GEMINI_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {GEMINI_KEY}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            content = json.loads(resp.read())["choices"][0]["message"]["content"]

        obj = _extract_json_from_text(content)
        if obj:
            return {
                "status": "pass" if obj.get("match") and obj.get("score", 0) >= 70 else "fail",
                "score": obj.get("score", 0),
                "issues": obj.get("issues", []),
                "reason": obj.get("reason", ""),
                "slide_text_found": obj.get("slide_text_found", ""),
                "raw_match": obj.get("match", False),
            }
        return {"status": "error", "reason": f"unparseable response: {content[:100]}"}

    except urllib.error.HTTPError as e:
        if e.code == 429:
            return {"status": "rate_limited", "reason": "Gemini 429 - skip for now"}
        return {"status": "error", "reason": f"HTTP {e.code}"}
    except Exception as e:
        return {"status": "error", "reason": str(e)[:200]}

def append_incident(video_id: str, title: str, issues: list, clause: str, topic: str):
    """Append mismatch incident to JSONL log."""
    entry = {
        "ts": datetime.now().isoformat(),
        "video_id": video_id,
        "title": title,
        "clause": clause,
        "topic": topic,
        "issues": issues,
        "status": "open",
        "countermeasure": "台本/スライドのテキスト整合性を手動確認し、run_host.py --force で再生成"
    }
    with open(INCIDENT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"  ⚠️  INCIDENT logged: {video_id}")

def _save_results(results, passed, failed, skipped, errors, total):
    output = {
        "generated_at": datetime.now().isoformat(),
        "total": total,
        "processed": len(results),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
        "broken_count": sum(1 for r in results if r.get("broken")),
        "videos": results,
    }
    QA_STATUS.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

# ── main loop ──────────────────────────────────────────────────────────────
def main():
    print(f"[IATF QA] Scanning {VIDEOS_DIR} ...")
    mp4s = sorted(VIDEOS_DIR.rglob("*_slide_reviewed.mp4"))
    print(f"[IATF QA] Found {len(mp4s)} videos")

    results = []
    passed = failed = skipped = errors = 0

    for i, mp4 in enumerate(mp4s, 1):
        folder = mp4.parent
        title = folder.name
        vid_id = safe_name(title)[:60]
        size_mb = mp4.stat().st_size / 1024 / 1024

        print(f"\n[{i}/{len(mp4s)}] {title[:60]}")
        print(f"  size: {size_mb:.1f} MB")

        # ── thumbnail extraction ──
        thumb_path = THUMB_OUT / f"{vid_id}.jpg"
        if thumb_path.exists():
            print(f"  thumb: cached ({thumb_path.name})")
        else:
            ok = extract_thumbnail(mp4, thumb_path)
            print(f"  thumb: {'OK' if ok else 'FAILED'} → {thumb_path.name}")

        thumb_url = f"/apps/growth_dashboard/iatf_thumbnails/{quote(thumb_path.name)}"

        # ── contact sheet ──
        contact = load_contact_sheet(folder)
        contact_url = None
        if contact:
            # Copy contact sheet to thumbnails dir for serving
            cs_dest = THUMB_OUT / f"{vid_id}_cs.jpg"
            if not cs_dest.exists():
                cs_dest.write_bytes(contact.read_bytes())
            contact_url = f"/apps/growth_dashboard/iatf_thumbnails/{quote(cs_dest.name)}"

        # ── script info ──
        script_info = read_script(folder)
        duration = probe_duration(mp4)

        # ── Gemini Vision QA ──
        print(f"  clause: {script_info.get('clause','?')} / topic: {script_info.get('topic','?')}")
        qa = gemini_vision_qa(
            thumb_path if thumb_path.exists() else None,
            contact,
            script_info
        )
        print(f"  QA: {qa.get('status','?')} score={qa.get('score','?')} {qa.get('reason','')[:60]}")

        # ── count ──
        status = qa.get("status", "error")
        if status == "pass":
            passed += 1
        elif status == "fail":
            failed += 1
            append_incident(
                vid_id, title,
                qa.get("issues", ["内容不一致"]),
                script_info.get("clause", ""),
                script_info.get("topic", "")
            )
        elif status in ("skip", "rate_limited"):
            skipped += 1
        else:
            errors += 1

        qa["checked_at"] = datetime.now().isoformat()

        # ── flag broken videos (< 500KB) ──
        broken = size_mb < 0.5
        if broken:
            print(f"  [BROKEN] file too small ({size_mb:.2f} MB)")

        entry = {
            "id": vid_id,
            "title": title,
            "clause": script_info.get("clause", ""),
            "topic": script_info.get("topic", ""),
            "mp4_path": str(mp4.relative_to(REPO_ROOT)).replace("\\", "/"),
            "thumbnail_url": thumb_url,
            "contact_sheet_url": contact_url,
            "file_size_mb": round(size_mb, 2),
            "duration_sec": duration,
            "scene_count": script_info.get("scene_count", 0),
            "script_summary": script_info.get("summary", "")[:300],
            "broken": broken,
            "qa": qa,
        }
        results.append(entry)

        # Incremental save after each video
        _save_results(results, passed, failed, skipped, errors, len(mp4s))

        # Rate-limit guard
        time.sleep(3)

    # ── write results ──
    output = {
        "generated_at": datetime.now().isoformat(),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
        "broken_count": sum(1 for r in results if r.get("broken")),
        "videos": results,
    }
    QA_STATUS.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[IATF QA] Done: {passed} pass / {failed} fail / {skipped} skip / {errors} err")
    print(f"[IATF QA] Results → {QA_STATUS}")
    print(f"[IATF QA] Incidents → {INCIDENT_LOG}")

if __name__ == "__main__":
    main()
