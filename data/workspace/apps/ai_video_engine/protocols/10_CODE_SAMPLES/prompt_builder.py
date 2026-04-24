import json
from pathlib import Path

TEMPLATE_PATH = Path("03_JSON_SCHEMA_TEMPLATE.json")

def load_template():
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def build_project(project_id: str, shot_id: str):
    data = load_template()
    data["project_id"] = project_id
    data["shot_id"] = shot_id
    return data

def save_project(data, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    data = build_project("my_project", "shot_001")
    save_project(data, "my_project_shot_001.json")
    print("saved: my_project_shot_001.json")
