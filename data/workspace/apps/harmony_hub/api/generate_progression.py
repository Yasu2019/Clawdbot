import json
import random
import sys
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
CHORDS_FILE = BASE_DIR / "data" / "chords.json"
PATTERNS_FILE = BASE_DIR / "data" / "patterns.json"

# ABC Notation Mapping (Simplified triads)
ABC_MAP = {
    "C": "[CEG]", "Dm": "[DFA]", "Em": "[EGB]", "F": "[FAc]", "G": "[GBd]", "Am": "[Ace]", "Bdim": "[Bdf]",
    "G": "[GBd]", "Am": "[Ace]", "Bm": "[Bdf#]", "C": "[ceg]", "D": "[df#a]", "Em": "[egb]", "F#dim": "[f#ac]",
    "D": "[DF#A]", "Em": "[EGB]", "F#m": "[F#Ac#]", "G": "[GBd]", "A": "[Ace]", "Bm": "[Bdf#]", "C#dim": "[c#eg]",
    "A": "[AC#E]", "Bm": "[BDF#]", "C#m": "[C#EG#]", "D": "[DFA]", "E": "[EG#B]", "F#m": "[F#Ac#]", "G#dim": "[g#bd]"
}

def to_abc(chords, title="Composition"):
    abc = f"X:1\nT:{title}\nM:4/4\nL:1/1\nK:C\n"
    # Clean chord names for mapping
    cleaned = [c.split('(')[0] for c in chords]
    notes = [ABC_MAP.get(c, "[CEG]") for c in cleaned]
    abc += " | ".join(notes) + " |]"
    return abc

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_progression(key="C", genre=None, mood=None, famous=None, artist=None):
    chords_data = load_json(CHORDS_FILE)
    patterns_data = load_json(PATTERNS_FILE)
    
    # Identify if key is major or minor
    is_minor = key.endswith("m")
    key_map = chords_data["minor_keys"] if is_minor else chords_data["major_keys"]
    
    if key not in key_map:
        return {"error": f"Key {key} not found."}
    
    scale_chords = key_map[key]
    
    # Roman Numeral mapping (simplified)
    # This regex-free approach handles basic extensions by checking prefix
    base_rn_map = {
        "I": 0, "ii": 1, "iii": 2, "IV": 3, "V": 4, "vi": 5, "vii": 6, "viidim": 6,
        "i": 0, "iidim": 1, "III": 2, "iv": 3, "v": 4, "VI": 5, "VII": 6
    }
    borrowed_map = ["bII", "bIII", "bV", "bVI", "bVII", "#ivdim"]

    pattern = None
    if artist and artist in patterns_data.get("artist_styles", {}):
        pattern = random.choice(patterns_data["artist_styles"][artist]["progressions"])
    elif famous and famous in patterns_data["famous_patterns"]:
        pattern = patterns_data["famous_patterns"][famous]["progression"]
    elif genre and genre in patterns_data["genres"]:
        pattern = random.choice(patterns_data["genres"][genre]["progressions"])
    elif mood and mood in patterns_data["moods"]:
        pattern = random.choice(patterns_data["moods"][mood]["progressions"])
    else:
        # Default Pop
        pattern = patterns_data["genres"]["Pop"]["progressions"][0]

    result = []
    for rn in pattern:
        found = False
        # Sort by length descending to match longest prefix (e.g., viidim before vii)
        sorted_keys = sorted(base_rn_map.keys(), key=len, reverse=True)
        for k in sorted_keys:
            if rn.startswith(k):
                idx = base_rn_map[k]
                chord = scale_chords[idx]
                # Append the extension if present (e.g. maj7)
                extension = rn[len(k):]
                result.append(f"{chord}{extension}")
                found = True
                break
        
        if not found:
            # Handle borrowed/chromatic
            result.append(f"{rn}({key})") 
            
    return {
        "key": key,
        "genre": genre,
        "mood": mood,
        "famous": famous,
        "artist": artist,
        "progression": result,
        "roman_numerals": pattern,
        "abc": to_abc(result, f"{artist or genre or mood or famous or 'Music'} in {key}")
    }

if __name__ == "__main__":
    # Simple CLI for testing
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", default="C")
    parser.add_argument("--genre")
    parser.add_argument("--mood")
    parser.add_argument("--famous")
    parser.add_argument("--artist")
    args = parser.parse_args()
    
    res = get_progression(args.key, args.genre, args.mood, args.famous, args.artist)
    print(json.dumps(res, indent=2, ensure_ascii=False))