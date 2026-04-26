#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
WORKFLOW_ID = "zO38wIUIoZJ7KsyS"
ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "ai_scout_fix_status.json"
JST = timezone(timedelta(hours=9))
TS = datetime.now(JST).strftime("%Y%m%d_%H%M%S")


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(status: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    headers = {
        "X-N8N-API-KEY": API_KEY,
        "Content-Type": "application/json",
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def backup_workflow(wf: dict) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"workflow_{wf['id']}_ai_scout_fix_{TS}.json"
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def find_node(wf: dict, name: str) -> dict:
    for node in wf["nodes"]:
        if node["name"] == name:
            return node
    raise KeyError(f"node not found: {name}")


def patch_queries(node: dict) -> bool:
    assignments = node["parameters"]["assignments"]["assignments"]
    desired = {
        "q1": "frontier AI model release openai anthropic google deepmind 2026",
        "q2": "Qwen Llama Mistral DeepSeek compact local model release 2026",
        "q3": "video generation music generation image generation lipsync AI release 2026",
        "q4": "deep learning research paper open source model release 2026",
        "q5": "Rowan Cheung Ethan Mollick Alina K. Miller Logan Kilpatrick AI Explained latest AI",
    }
    changed = False
    for item in assignments:
        name = item.get("name")
        if name in desired and item.get("value") != desired[name]:
            item["value"] = desired[name]
            changed = True
    return changed


def patch_summary_node(node: dict) -> bool:
    changed = False
    desired_url = "http://host.docker.internal:11434/api/generate"
    desired_body = (
        "={{ JSON.stringify({ "
        "model: 'qwen2.5-coder:7b', "
        "prompt: 'あなたはAI業界ウォッチャーです。与えられた検索結果から、"
        "AIモデル、動画生成、音楽生成、画像生成、リップシンク、DeepLearning、"
        "業務活用の観点で本当に新しい情報だけを日本語で5-10件の箇条書きに整理してください。"
        "各項目は短く、媒体名や人物名が分かる場合は含めてください。"
        "SNSや動画は検索結果に含まれる公開ページだけを根拠にし、未確認の断定は避けてください。"
        "検索結果:\\n' + $json.summary_input, "
        "stream: false, "
        "options: { num_predict: 700, temperature: 0.2 } "
        "}) }}"
    )
    if node["parameters"].get("url") != desired_url:
        node["parameters"]["url"] = desired_url
        changed = True
    if node["parameters"].get("body") != desired_body:
        node["parameters"]["body"] = desired_body
        changed = True
    node["parameters"]["method"] = "POST"
    node["parameters"]["sendHeaders"] = True
    node["parameters"]["headerParameters"] = {
        "parameters": [
            {"name": "Content-Type", "value": "application/json"},
        ]
    }
    node["parameters"]["sendBody"] = True
    node["parameters"]["contentType"] = "raw"
    return changed


def patch_extract_node(node: dict) -> bool:
    desired_code = """
const body = $input.item.json || {};
const content = (body.response || '').trim() || '(結果なし)';
const today = new Date().toLocaleDateString('ja-JP', { timeZone: 'Asia/Tokyo' });
return [{
  json: {
    message: `AI Scout 日報 (${today})\\n\\n${content}\\n\\n---\\n取得元: SearXNG 公開Web検索`
  }
}];
""".strip()
    if node["parameters"].get("jsCode") != desired_code:
        node["parameters"]["jsCode"] = desired_code
        return True
    return False


def patch_aggregate_node(node: dict) -> bool:
    desired_code = """
const allItems = $input.all();
const today = new Date().toLocaleDateString('ja-JP', { timeZone: 'Asia/Tokyo' });
const categories = [
  { key: 'frontier ai model', title: 'AIモデル' },
  { key: 'qwen llama mistral deepseek', title: 'ローカルLLM' },
  { key: 'video generation music generation image generation lipsync', title: '動画・音楽・画像・LipSync' },
  { key: 'deep learning research paper', title: 'DeepLearning / 論文' },
  { key: 'rowan cheung ethan mollick', title: '注目発信者 / メディア' },
];
const sections = new Map(categories.map((item) => [item.title, []]));
const seen = new Set();
for (const item of allItems) {
  const data = item.json || {};
  const query = (data.query || '').toLowerCase();
  const category = categories.find((entry) => query.includes(entry.key))?.title || 'その他';
  if (!sections.has(category)) sections.set(category, []);
  for (const hit of (data.results || []).slice(0, 3)) {
    const url = hit.url || '';
    const title = (hit.title || '').trim();
    const key = `${title}::${url}`;
    if (!title || seen.has(key)) continue;
    seen.add(key);
    sections.get(category).push(`- ${title}\\n  ${url}`);
  }
}
const parts = [`AI Scout 日報 (${today})`, '', '取得元: SearXNG 公開Web検索', ''];
for (const [title, hits] of sections.entries()) {
  if (!hits.length) continue;
  parts.push(`【${title}】`);
  parts.push(...hits.slice(0, 3));
  parts.push('');
}
parts.push('備考: Instagram / X / YouTube / TikTok の直接スクレイプではなく、公開Web検索の結果を整理しています。');
return [{ json: { message: parts.join('\\n').trim() } }];
""".strip()
    if node["parameters"].get("jsCode") != desired_code:
        node["parameters"]["jsCode"] = desired_code
        return True
    return False


def connect(wf: dict, source_name: str, target_name: str) -> bool:
    wf.setdefault("connections", {})
    wf["connections"].setdefault(source_name, {"main": [[]]})
    main = wf["connections"][source_name]["main"]
    if not main:
        main.append([])
    first = main[0]
    if not any(conn.get("node") == target_name for conn in first):
        first.append({"node": target_name, "type": "main", "index": 0})
        return True
    return False


def replace_connections(wf: dict, source_name: str, target_names: list[str]) -> bool:
    wf.setdefault("connections", {})
    wf["connections"][source_name] = {
        "main": [[{"node": target_name, "type": "main", "index": 0} for target_name in target_names]]
    }
    return True


def update_workflow(wf: dict) -> dict:
    payload = {k: v for k, v in wf.items() if k in {"name", "nodes", "connections", "settings", "staticData"}}
    return request_json(f"/workflows/{wf['id']}", method="PUT", payload=payload)


def main() -> None:
    status = {
        "startedAt": now_jst(),
        "step": "patching",
        "workflowId": WORKFLOW_ID,
        "changes": [],
    }
    write_status(status)

    wf = request_json(f"/workflows/{WORKFLOW_ID}")
    status["backup"] = backup_workflow(wf)

    if patch_queries(find_node(wf, "Search Queries")):
        status["changes"].append("updated search queries")
    if patch_aggregate_node(find_node(wf, "Aggregate Results")):
        status["changes"].append("patched Aggregate Results to deterministic daily digest")
    if patch_summary_node(find_node(wf, "Gemini Summary")):
        status["changes"].append("patched Gemini Summary to direct Ollama")
    if patch_extract_node(find_node(wf, "Extract AI Report")):
        status["changes"].append("patched Extract AI Report for /api/generate response")
    replace_connections(wf, "Aggregate Results", ["Telegram Notify"])
    status["changes"].append("rerouted Aggregate Results directly to Telegram Notify")

    updated = None
    if status["changes"]:
        updated = update_workflow(wf)
        status["updatedAt"] = updated.get("updatedAt")

    status["finishedAt"] = now_jst()
    status["step"] = "completed"
    write_status(status)


if __name__ == "__main__":
    main()
