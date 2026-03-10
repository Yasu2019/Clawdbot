from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, subprocess, pathlib

app = FastAPI(title="Godot Builder", version="1.1")

SECRETS_DIR = os.environ.get("SECRETS_DIR", "/workspace/secrets")
KEYSTORE_PATH = os.environ.get("KEYSTORE_PATH", f"{SECRETS_DIR}/release.keystore")
KEYSTORE_PASSWORD = os.environ.get("KEYSTORE_PASSWORD", "")
KEY_ALIAS = os.environ.get("KEY_ALIAS", "")
KEY_PASSWORD = os.environ.get("KEY_PASSWORD", "")

class AndroidBuild(BaseModel):
    project_id: str
    godot_project_path: str
    output_dir: str
    android: dict

def run(cmd: list[str], cwd: str | None = None):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stdout)
    return p.stdout

def ensure_export_presets(project_path: str, android_cfg: dict):
    p = pathlib.Path(project_path)
    cfg = p / "export_presets.cfg"
    package_name = android_cfg["package_name"]
    version_name = android_cfg["version_name"]
    version_code = android_cfg["version_code"]

    # Minimal debug preset; release preset intentionally omitted in v1.1 (avoid keystore fields)
    cfg.write_text(f"""[preset.0]

name="Android Debug"
platform="Android"
runnable=true
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path=""
script_export_mode=1

[preset.0.options]
package/unique_name="{package_name}"
version/name="{version_name}"
version/code={version_code}
""", encoding="utf-8")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/build/android")
def build_android(req: AndroidBuild):
    project_path = req.godot_project_path
    out_dir = req.output_dir

    if not os.path.isdir(project_path):
        raise HTTPException(400, "godot_project_path not found")

    os.makedirs(out_dir, exist_ok=True)
    ensure_export_presets(project_path, req.android)

    android_out = os.path.join(out_dir, "android")
    os.makedirs(android_out, exist_ok=True)

    package = req.android["package_name"]
    vname = req.android["version_name"]

    apk_path = os.path.join(android_out, f"{package}_{vname}_debug.apk")

    try:
        # preset name must match ensure_export_presets
        run(["godot", "--headless", "--path", project_path, "--export-debug", "Android Debug", apk_path])
    except Exception as e:
        raise HTTPException(500, f"debug apk export failed:\n{e}")

    # Release AAB is intentionally skipped in v1.1 (avoid storing signing fields in presets)
    # In v1.2: generate release preset in-memory with signing fields, then export AAB.

    return {"ok": True, "apk": apk_path}
