# -*- coding: utf-8 -*-
from __future__ import annotations
import copy
import json
import urllib.request
from pathlib import Path


def health(base_url="http://127.0.0.1:8188", timeout=5):
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/system_stats", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _replace_tokens(obj, mapping):
    if isinstance(obj, dict):
        return {k: _replace_tokens(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_tokens(v, mapping) for v in obj]
    if isinstance(obj, str):
        out = obj
        for k, v in mapping.items():
            out = out.replace("{{" + k + "}}", str(v))
        return out
    return obj


def submit_api_workflow(workflow_path: Path, mapping: dict, base_url="http://127.0.0.1:8188", timeout=30):
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    workflow = _replace_tokens(copy.deepcopy(workflow), mapping)
    payload = json.dumps({"prompt": workflow}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/prompt",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))
