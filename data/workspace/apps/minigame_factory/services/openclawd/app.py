import json, os, uuid
from fastapi import FastAPI
from jsonschema import Draft202012Validator

SCHEMA_PATH = os.environ.get("SCHEMA_PATH", "/workspace/schemas/game_spec.schema.json")
SCHEMA = json.loads(open(SCHEMA_PATH, "r", encoding="utf-8").read())
VALIDATOR = Draft202012Validator(SCHEMA)

app = FastAPI(title="OpenClawd Stub", version="1.1")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/draft_spec")
def draft_spec(user_intent: dict):
    # Minimal stub that returns a valid spec
    pid = user_intent.get("game_id") or uuid.uuid4().hex
    spec = {
        "game_id": pid,
        "title": user_intent.get("title", "Dungeon v2"),
        "genre": user_intent.get("genre", "dungeon"),
        "targets": {"android": True, "web_singlehtml": True},
        "session": {"length_sec": 180, "difficulty": 2},
        "perspective": {"allow_toggle": True, "default": "fps", "modes": ["fps", "topdown"]},
        "controls": {
            "android": {"move": "virtual_joystick", "look": "swipe", "shoot": "tap", "toggle_view": "button"},
            "desktop": {"move": "WASD", "look": "mouse", "shoot": "LMB", "toggle_view": "V"}
        },
        "build": {
            "android": {
                "package_name": "com.example.dungeonv2",
                "version_name": "0.1.0",
                "version_code": 1,
                "export_format": ["apk_debug"]
            },
            "web": {"single_file": True}
        }
    }
    errors = list(VALIDATOR.iter_errors(spec))
    if errors:
        return {"ok": False, "error": errors[0].message}
    return {"ok": True, "spec": spec}
