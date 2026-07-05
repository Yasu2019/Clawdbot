# -*- coding: utf-8 -*-
"""U2: お手本レジストリ照合(S3) — skill_pipeline_implementation_spec.md 準拠。

status=="interpreted" の依頼の interpretation.skill_name を reference_registry.yaml
で照合し、BVHをzipから展開(未展開時)して reference を追記、status="reference_found"。
レジストリ未登録は status="needs_human_source"(Web自動DLはv1では行わない — ライセンス
誤取得リスク。人間が候補URLを提示する)。

usage: python u2_reference_finder.py --once
"""
import argparse, json, os, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\skill_requests.json"
REGISTRY = os.path.join(HERE, "reference_registry.yaml")
DATASET_DIR = r"C:\v50_work\datasets\100style"
DATASET_ZIP = os.path.join(DATASET_DIR, "100STYLE.zip")


def load_registry():
    """registryの固定形(skills: / <name>: / clip: / note:)だけ読む最小パーサ。
    pyyamlがあれば正攻法で読む。"""
    try:
        import yaml
        with open(REGISTRY, encoding="utf-8") as f:
            return yaml.safe_load(f)["skills"]
    except ImportError:
        pass
    skills, cur = {}, None
    for raw in open(REGISTRY, encoding="utf-8"):
        line = raw.split("#")[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        key, _, val = line.strip().partition(":")
        val = val.strip()
        if indent == 2 and not val:            # skill name
            cur = key
            skills[cur] = {}
        elif indent >= 4 and cur:
            skills[cur][key] = val
    return skills


def ensure_extracted(rel_path):
    """zip内相対パスのBVHを展開済みにして絶対パスを返す。"""
    abs_path = os.path.join(DATASET_DIR, rel_path.replace("/", os.sep))
    if os.path.exists(abs_path):
        return abs_path
    with zipfile.ZipFile(DATASET_ZIP) as z:
        z.extract(rel_path, DATASET_DIR)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(abs_path)
    return abs_path


def run_once():
    if not os.path.exists(STORE):
        print("no queue file"); return 0
    skills = load_registry()
    data = json.load(open(STORE, encoding="utf-8"))
    changed = 0
    for req in data.get("requests", []):
        if req.get("status") != "interpreted":
            continue
        name = (req.get("interpretation") or {}).get("skill_name")
        entry = skills.get(name)
        if entry and entry.get("clip"):
            try:
                bvh = ensure_extracted(entry["clip"])
                req["reference"] = {"bvh": bvh, "registry_note": entry.get("note", ""),
                                    "license": "CC-BY-4.0 100STYLE (decision on file)"}
                # 判断済みデータセット内のためS5スキップ可(spec U3)
                req["status"] = "retarget_ready"
            except Exception as e:
                req["status"] = "needs_human_source"
                req["notes"] = f"U2: clip extraction failed: {type(e).__name__}: {e}"
        else:
            req["status"] = "needs_human_source"
            req["notes"] = (f"U2: skill '{name}' はレジストリ未登録。"
                            "人間がお手本候補(BVH/動画URL)を提示してください。")
        req["reference_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        changed += 1
        print(f"U2 {req['id']}: {name} -> {req['status']}"
              + (f" ({req['reference']['bvh']})" if req.get("reference") else ""))
    if changed:
        with open(STORE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"U2 done: {changed} request(s) processed")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.parse_args()
    raise SystemExit(run_once())
