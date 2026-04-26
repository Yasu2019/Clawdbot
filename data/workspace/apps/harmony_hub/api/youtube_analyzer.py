import os
import sys
import json
import subprocess
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "temp_audio"
KNOWLEDGE_FILE = BASE_DIR / "data" / "youtube_knowledge.json"

# Ensure temp dir exists
TEMP_DIR.mkdir(exist_ok=True)

def analyze_audio(file_path):
    """
    Analyze local audio file using librosa.
    Returns estimated BPM and Key.
    """
    try:
        import librosa
        import numpy as np
        
        y, sr = librosa.load(file_path)
        
        # Tempo
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        
        # Chroma analysis for Key detection (Simplified)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_sum = np.sum(chroma, axis=1)
        
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        estimated_key_idx = np.argmax(chroma_sum)
        estimated_key = keys[estimated_key_idx]
        
        return {
            "bpm": float(tempo[0]) if isinstance(tempo, (list, np.ndarray)) else float(tempo),
            "key": estimated_key,
            "status": "Success"
        }
    except ImportError:
        return {"error": "librosa not installed", "status": "Failed"}
    except Exception as e:
        return {"error": str(e), "status": "Failed"}

def download_youtube_audio(url):
    """
    Download audio from YouTube using yt-dlp.
    """
    output_template = str(TEMP_DIR / "%(title)s.%(ext)s")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-x", "--audio-format", "mp3",
        "-o", output_template,
        "--get-title", # We'll run twice or use a hack to get title
        url
    ]
    
    try:
        # Get video ID and title
        info_raw = subprocess.check_output([
            sys.executable, "-m", "yt_dlp", 
            "--get-id", "--get-title", url
        ])
        
        # Detect encoding: Docker/Linux usually utf-8, Windows host might be cp932
        encoding = 'utf-8' if os.name == 'posix' else 'cp932'
        raw_lines = info_raw.decode(encoding, errors='replace').strip().split('\n')
        info_lines = [line for line in raw_lines if not line.startswith('WARNING:')]
        
        if len(info_lines) < 2:
            return {"error": f"Failed to parse ID/Title from: {info_lines}"}
            
        video_id = info_lines[1].strip()
        title = info_lines[0].strip()
        
        file_path = TEMP_DIR / f"{video_id}.mp3"
        
        # Download and extract audio if not already exists
        if not file_path.exists():
            subprocess.run([
                sys.executable, "-m", "yt_dlp",
                "-x", "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", str(file_path),
                url
            ], check=True)
        
        return {"title": title, "file_path": str(file_path)}
    except Exception as e:
        return {"error": str(e)}

def get_playlist_ids(url):
    """
    If URL is a playlist, return list of video IDs.
    """
    try:
        res = subprocess.check_output([
            sys.executable, "-m", "yt_dlp",
            "--flat-playlist", "--get-id", url
        ])
        return res.decode('utf-8').strip().split('\n')
    except Exception as e:
        print(f"Playlist expansion failed: {e}")
        return []

def process_url(url):
    # Detect playlist
    if "list=" in url:
        print(f"Playlist detected. Expanding: {url}")
        ids = get_playlist_ids(url)
        print(f"Found {len(ids)} videos. Processing each...")
        results = []
        for vid in ids:
            if not vid.strip(): continue
            v_url = f"https://www.youtube.com/watch?v={vid}"
            results.append(process_url(v_url))
        return results

    print(f"Downloading: {url}...")
    dl_res = download_youtube_audio(url)
    if "error" in dl_res:
        print(f"Error downloading {url}: {dl_res['error']}")
        return dl_res
    
    print(f"Analyzing: {dl_res['title']}...")
    analysis = analyze_audio(dl_res['file_path'])
    
    result = {
        "url": url,
        "title": dl_res['title'],
        "bpm": analysis.get("bpm"),
        "key": analysis.get("key"),
        "timestamp": "2026-04-25"
    }
    
    # Save to knowledge
    try:
        data = []
        if KNOWLEDGE_FILE.exists():
            with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        # Avoid duplicates
        if not any(d.get("url") == url for d in data):
            data.append(result)
            with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save: {e}")
        
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_analyzer.py <URL1> <URL2> ...")
        sys.exit(1)
        
    urls = sys.argv[1:]
    for url in urls:
        res = process_url(url)
        # Results might be a list if it was a playlist
        if isinstance(res, list):
            print(f"Processed playlist: {len(res)} items.")
        else:
            print(json.dumps(res, indent=2, ensure_ascii=False))
