# -*- coding: utf-8 -*-
from __future__ import annotations
import copy
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_RE = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")
DEFAULT_BASE = "http://127.0.0.1:8188"


class ComfyError(RuntimeError):
    """ComfyUIが返したエラー本文を保持する例外。"""

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.detail = detail


def health(base_url=DEFAULT_BASE, timeout=5):
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/system_stats", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _request(url, payload=None, timeout=30):
    """ComfyUIはバリデーション失敗を400のJSON本文で返すため、本文を必ず読み出す。"""
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except Exception:
            detail = {"raw": raw[:4000]}
        raise ComfyError(f"ComfyUI HTTP {e.code}: {_summarize_error(detail)}", detail) from None
    return json.loads(body) if body else {}


def _summarize_error(detail):
    """ComfyUIのバリデーションエラーを1行に要約する。"""
    if not isinstance(detail, dict):
        return str(detail)[:300]
    parts = []
    err = detail.get("error")
    if isinstance(err, dict):
        parts.append(str(err.get("message") or err.get("type") or ""))
    elif err:
        parts.append(str(err))
    for node_id, node_err in (detail.get("node_errors") or {}).items():
        for e in node_err.get("errors", []):
            parts.append(f"node {node_id} {node_err.get('class_type', '')}: {e.get('message')} ({e.get('details')})")
    return " / ".join(p for p in parts if p)[:1000] or str(detail)[:300]


def find_tokens(obj):
    """ワークフロー内の {{TOKEN}} を列挙する。"""
    found = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            found |= find_tokens(k)
            found |= find_tokens(v)
    elif isinstance(obj, list):
        for v in obj:
            found |= find_tokens(v)
    elif isinstance(obj, str):
        found |= set(TOKEN_RE.findall(obj))
    return found


def _replace_tokens(obj, mapping):
    if isinstance(obj, dict):
        return {k: _replace_tokens(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_tokens(v, mapping) for v in obj]
    if isinstance(obj, str):
        # 文字列全体がちょうど1つのトークンなら、値の型（int/float/bool）をそのまま保つ。
        # ComfyUIはINT/FLOAT入力に文字列を渡すと型エラーになるため。
        whole = TOKEN_RE.fullmatch(obj)
        if whole and whole.group(1) in mapping:
            return mapping[whole.group(1)]
        out = obj
        for k, v in mapping.items():
            out = out.replace("{{" + k + "}}", str(v))
        return out
    return obj


def render_workflow(workflow_path: Path, mapping: dict, allow_missing=False):
    """ワークフローJSONを読み、トークンを置換して返す。
    未置換トークンが残っていれば、そのまま投入して不可解なエラーになる前に落とす。"""
    workflow = json.loads(Path(workflow_path).read_text(encoding="utf-8"))
    declared = find_tokens(workflow)
    rendered = _replace_tokens(copy.deepcopy(workflow), mapping)
    remaining = find_tokens(rendered)
    if remaining and not allow_missing:
        raise ComfyError(
            "未置換のトークンが残っています: " + ", ".join(sorted(remaining))
            + f"（このワークフローのトークン: {', '.join(sorted(declared))}）"
        )
    return rendered


def validate_workflow(workflow: dict, base_url=DEFAULT_BASE, timeout=30):
    """投入前に、稼働中ComfyUIの /object_info と突合して問題を洗い出す。
    モデル未配置はここで「候補一覧に無い値」として検出できる。"""
    info = _request(base_url.rstrip("/") + "/object_info", timeout=timeout)
    problems = []
    for node_id, node in workflow.items():
        cls = node.get("class_type")
        if cls not in info:
            problems.append(f"node {node_id}: クラス {cls} がこのComfyUIに存在しません")
            continue
        spec = info[cls].get("input", {})
        fields = {}
        for kind in ("required", "optional"):
            fields.update(spec.get(kind) or {})
        for name, value in (node.get("inputs") or {}).items():
            if name not in fields:
                problems.append(f"node {node_id} {cls}: 入力 {name} は存在しません")
                continue
            if isinstance(value, list):
                continue  # 他ノードへのリンク
            allowed = fields[name][0]
            if isinstance(allowed, list):
                if not allowed:
                    problems.append(f"node {node_id} {cls}.{name}: 選択肢が空です（モデル未配置）: {value!r}")
                elif value not in allowed:
                    problems.append(
                        f"node {node_id} {cls}.{name}: {value!r} は候補にありません（例: {allowed[:3]}）"
                    )
    return problems


def submit_api_workflow(workflow_path: Path, mapping: dict, base_url=DEFAULT_BASE, timeout=30):
    """後方互換: トークン置換して /prompt へ投入し、応答（prompt_id等）を返す。"""
    workflow = render_workflow(workflow_path, mapping)
    return submit_rendered(workflow, base_url=base_url, timeout=timeout)


def submit_rendered(workflow: dict, base_url=DEFAULT_BASE, timeout=30):
    return _request(base_url.rstrip("/") + "/prompt", {"prompt": workflow}, timeout=timeout)


def wait_for_result(prompt_id: str, base_url=DEFAULT_BASE, poll=2.0, timeout=1800):
    """/history をポーリングして完了を待ち、履歴エントリを返す。"""
    url = base_url.rstrip("/") + "/history/" + urllib.parse.quote(prompt_id)
    deadline = time.time() + timeout
    while time.time() < deadline:
        hist = _request(url, timeout=30)
        entry = hist.get(prompt_id)
        if entry:
            status = entry.get("status", {})
            if status.get("completed") or status.get("status_str") in ("success", "error"):
                if status.get("status_str") == "error":
                    raise ComfyError("ComfyUI実行エラー: " + _summarize_status(status), status)
                return entry
        time.sleep(poll)
    raise ComfyError(f"{timeout}秒以内に完了しませんでした (prompt_id={prompt_id})")


def _summarize_status(status):
    msgs = []
    for item in status.get("messages", []) or []:
        if isinstance(item, list) and len(item) >= 2 and item[0] == "execution_error":
            d = item[1] or {}
            msgs.append(f"{d.get('node_type')}: {d.get('exception_message')}")
    return " / ".join(msgs) or json.dumps(status, ensure_ascii=False)[:500]


def collect_outputs(history_entry: dict, base_url=DEFAULT_BASE):
    """履歴から出力ファイル一覧（/view で取得できるURL付き）を作る。"""
    out = []
    for node_id, node_out in (history_entry.get("outputs") or {}).items():
        for key, items in node_out.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict) or "filename" not in item:
                    continue
                q = urllib.parse.urlencode({
                    "filename": item.get("filename", ""),
                    "subfolder": item.get("subfolder", ""),
                    "type": item.get("type", "output"),
                })
                out.append({
                    "node_id": node_id,
                    "kind": key,
                    "filename": item.get("filename"),
                    "subfolder": item.get("subfolder", ""),
                    "type": item.get("type", "output"),
                    "url": base_url.rstrip("/") + "/view?" + q,
                })
    return out


def download_output(item: dict, dest_dir: Path, timeout=120):
    """/view から実ファイルを取得してローカルへ保存する。"""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / item["filename"]
    with urllib.request.urlopen(item["url"], timeout=timeout) as r:
        dest.write_bytes(r.read())
    return dest


def run_workflow(workflow_path: Path, mapping: dict, base_url=DEFAULT_BASE,
                 validate=True, wait=True, timeout=1800, dest_dir=None):
    """登録済みワークフローを『置換 → 事前検証 → 投入 → 完了待ち → 出力回収』まで通す。"""
    workflow = render_workflow(workflow_path, mapping)
    result = {"workflow": str(workflow_path), "validated": None, "prompt_id": None, "outputs": []}
    if validate:
        problems = validate_workflow(workflow, base_url=base_url)
        result["validated"] = problems
        if problems:
            raise ComfyError("事前検証で問題が見つかりました:\n  - " + "\n  - ".join(problems), problems)
    resp = submit_rendered(workflow, base_url=base_url)
    result["prompt_id"] = resp.get("prompt_id")
    if not wait:
        return result
    entry = wait_for_result(result["prompt_id"], base_url=base_url, timeout=timeout)
    result["outputs"] = collect_outputs(entry, base_url=base_url)
    if dest_dir:
        result["saved"] = [str(download_output(o, dest_dir)) for o in result["outputs"]]
    return result
