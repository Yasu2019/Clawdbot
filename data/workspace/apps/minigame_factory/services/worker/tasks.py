import os, json, shutil, requests
from jsonschema import validate

PROJECTS_DIR = os.environ["PROJECTS_DIR"]
OUTPUT_DIR = os.environ["OUTPUT_DIR"]
TEMPLATES_DIR = os.environ["TEMPLATES_DIR"]
SCHEMA_PATH = os.environ["SCHEMA_PATH"]
GODOT_BUILDER_URL = os.environ["GODOT_BUILDER_URL"]
NODE_BUILDER_URL = os.environ["NODE_BUILDER_URL"]

with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    SCHEMA = json.load(f)

def _pdir(project_id: str) -> str:
    return os.path.join(PROJECTS_DIR, project_id)

def _load_spec(project_id: str) -> dict:
    path = os.path.join(_pdir(project_id), "game_spec.json")
    with open(path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    validate(instance=spec, schema=SCHEMA)
    return spec

def _copy_template(template_name: str, dst_dir: str):
    src = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.isdir(src):
        raise RuntimeError(f"template not found: {template_name}")
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    shutil.copytree(src, dst_dir)

def build_project(project_id: str):
    spec = _load_spec(project_id)

    work_dir = os.path.join(_pdir(project_id), "work")
    out_dir = os.path.join(OUTPUT_DIR, project_id)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(work_dir, exist_ok=True)

    godot_template = "godot_dualview_dungeon_v2"
    web_template = "threejs_singlehtml_dungeon_v1"

    # Android (Godot)
    if spec["targets"]["android"]:
        godot_proj_dir = os.path.join(work_dir, "godot")
        _copy_template(godot_template, godot_proj_dir)

        payload = {
            "project_id": project_id,
            "godot_project_path": godot_proj_dir,
            "output_dir": out_dir,
            "android": spec["build"]["android"]
        }
        r = requests.post(f"{GODOT_BUILDER_URL}/build/android", json=payload, timeout=60*60)
        r.raise_for_status()

    # Web single HTML (Three.js)
    if spec["targets"]["web_singlehtml"]:
        payload = {
            "project_id": project_id,
            "template_name": web_template,
            "output_dir": out_dir,
            "spec": spec
        }
        r = requests.post(f"{NODE_BUILDER_URL}/build/singlehtml", json=payload, timeout=10*60)
        r.raise_for_status()

    return {"ok": True, "project_id": project_id}
