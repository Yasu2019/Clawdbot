import subprocess
import sys
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
PENDING_FILE = BASE_DIR / "data" / "pending_urls.txt"

GENRES = [
    "Classical music masterpieces",
    "Jazz standards top 50",
    "Latest K-POP hits 2026",
    "Popular J-POP 2026 charts",
    "Wind Orchestra masterpieces 吹奏楽名曲"
]

def scout_genre(genre):
    print(f"Scouting for: {genre}...")
    try:
        # Search for top 10 results
        cmd = [
            "python3", "-m", "yt_dlp",
            f"ytsearch10:{genre}",
            "--get-id",
            "--flat-playlist"
        ]
        res = subprocess.check_output(cmd).decode('utf-8').strip().split('\n')
        urls = [f"https://www.youtube.com/watch?v={vid}" for vid in res if vid.strip()]
        return urls
    except Exception as e:
        print(f"Scout failed for {genre}: {e}")
        return []

def run_scout():
    all_urls = []
    for genre in GENRES:
        urls = scout_genre(genre)
        all_urls.extend(urls)
    
    if not all_urls:
        print("No URLs found.")
        return

    # Add to pending_urls.txt
    try:
        with open(PENDING_FILE, "a", encoding="utf-8") as f:
            f.write("\n# Auto-Scouted Genre Hits\n")
            for url in all_urls:
                f.write(f"{url}\n")
        print(f"Added {len(all_urls)} URLs to the queue.")
    except Exception as e:
        print(f"Failed to update pending list: {e}")

if __name__ == "__main__":
    run_scout()
