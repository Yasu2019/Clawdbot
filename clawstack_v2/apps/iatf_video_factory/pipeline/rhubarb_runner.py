"""Rhubarb Lip Sync ラッパー — WAV → フォネームJSONL。"""
import json, subprocess, tempfile
from pathlib import Path

RHUBARB_BIN = "/usr/local/bin/rhubarb"


def run_rhubarb(wav_path: Path, character: str, rhubarb_bin: str = RHUBARB_BIN) -> list[dict]:
    """WAVファイルをRhubarbに通してフォネームリストを返す。"""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out_path = Path(tmp.name)

    cmd = [
        rhubarb_bin,
        "-f", "json",
        "-o", str(out_path),
        "--machineReadable",
        str(wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"  Rhubarb failed for {wav_path.name}: {result.stderr[-500:]}")
        return []

    data = json.loads(out_path.read_text())
    out_path.unlink(missing_ok=True)

    phonemes = []
    for entry in data.get("mouthCues", []):
        phonemes.append({
            "character": character,
            "start":     entry["start"],
            "end":       entry["end"],
            "value":     entry["value"],
        })
    return phonemes


def build_phoneme_timeline(audio_timeline: list[dict], rhubarb_bin: str = RHUBARB_BIN) -> list[dict]:
    """タイムライン全エントリのWAVをRhubarbに通し、絶対時刻に変換して返す。"""
    all_phonemes = []
    for entry in audio_timeline:
        wav_path = Path(entry["wav"])
        if not wav_path.exists():
            continue
        relative = run_rhubarb(wav_path, entry["character"], rhubarb_bin)
        offset = entry["start_sec"]
        for p in relative:
            all_phonemes.append({
                "character": p["character"],
                "start":     p["start"] + offset,
                "end":       p["end"]   + offset,
                "value":     p["value"],
            })
    return all_phonemes
