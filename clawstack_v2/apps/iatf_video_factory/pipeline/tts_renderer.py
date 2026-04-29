"""VoiceVox TTS — キャラクター別音声生成。"""
import requests, wave, json, hashlib, os
from pathlib import Path

VOICEVOX_URL = os.getenv("VOICEVOX_URL", "http://localhost:50021")

SPEAKER_MAP = {
    "bulma":     2,   # 四国めたん ノーマル
    "goku":      8,   # 春日部つむぎ
    "gohan":     3,   # ずんだもん ノーマル
    "android17": 9,   # 波音リツ
    "android18": 10,  # 雨晴はう
    "roshi":     11,  # 玄野武宏
    "trunks":    7,   # ずんだもん ツンツン
}

SPEAKER_PARAMS = {
    "bulma":     {"speedScale": 1.0, "pitchScale": 0.0,   "intonationScale": 1.2},
    "goku":      {"speedScale": 1.05,"pitchScale": -0.03,  "intonationScale": 1.3},
    "gohan":     {"speedScale": 1.0, "pitchScale": 0.02,  "intonationScale": 1.1},
    "android17": {"speedScale": 0.95,"pitchScale": -0.02,  "intonationScale": 1.1},
    "android18": {"speedScale": 1.0, "pitchScale": 0.0,   "intonationScale": 1.2},
    "roshi":     {"speedScale": 0.88,"pitchScale": -0.08,  "intonationScale": 1.4},
    "trunks":    {"speedScale": 1.1, "pitchScale": 0.01,  "intonationScale": 1.2},
}


def synthesize(character: str, text: str, out_dir: Path) -> Path:
    speaker_id = SPEAKER_MAP.get(character, 3)
    params = SPEAKER_PARAMS.get(character, {})
    cache_key = hashlib.md5(f"{character}:{text}".encode()).hexdigest()[:12]
    out_path = out_dir / f"{character}_{cache_key}.wav"
    if out_path.exists():
        return out_path

    # 長いテキストは分割合成してメモリ節約
    text_short = text[:200] if len(text) > 200 else text

    r = requests.post(
        f"{VOICEVOX_URL}/audio_query",
        params={"text": text_short, "speaker": speaker_id},
        timeout=60,
    )
    r.raise_for_status()
    query = r.json()
    for k, v in params.items():
        query[k] = v

    r2 = requests.post(
        f"{VOICEVOX_URL}/synthesis",
        params={"speaker": speaker_id},
        json=query,
        headers={"Content-Type": "application/json"},
        timeout=300,
    )
    r2.raise_for_status()
    out_path.write_bytes(r2.content)
    return out_path


def get_duration(wav_path: Path) -> float:
    with wave.open(str(wav_path)) as wf:
        return wf.getnframes() / wf.getframerate()


def render_script_audio(script: dict, audio_dir: Path) -> list[dict]:
    """台本の全セリフをTTS変換。タイムラインリストを返す。"""
    audio_dir.mkdir(parents=True, exist_ok=True)
    timeline = []
    current_time = 0.0

    lines_all = [(s, l) for s in script.get("scenes", []) for l in s.get("lines", [])]
    total = len(lines_all)
    for i, (scene, line) in enumerate(lines_all):
        char = line["character"]
        text = line["text"]
        print(f"  TTS [{i+1}/{total}] {char}: {text[:40]}...", flush=True)
        wav_path = synthesize(char, text, audio_dir)
        duration = get_duration(wav_path)
        timeline.append({
            "scene_id":   scene["scene_id"],
            "character":  char,
            "text":       text,
            "emotion":    line.get("emotion", "normal"),
            "pose":       line.get("pose", "neutral"),
            "wav":        str(wav_path),
            "start_sec":  current_time,
            "duration_sec": duration,
        })
        current_time += duration + 0.3  # 0.3秒ポーズ

    return timeline


if __name__ == "__main__":
    out = Path("/tmp/test_audio")
    wav = synthesize("bulma", "こんにちは、本日はIATF内部監査について学びましょう。", out)
    print(f"Generated: {wav}, duration: {get_duration(wav):.2f}s")
