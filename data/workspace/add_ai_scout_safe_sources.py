#!/usr/bin/env python3
import copy
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
WORKFLOW_ID = "zO38wIUIoZJ7KsyS"
ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "ai_scout_safe_sources_status.json"
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
    path = BACKUP_DIR / f"workflow_{wf['id']}_ai_scout_safe_sources_{TS}.json"
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def find_node(wf: dict, name: str) -> dict:
    for node in wf["nodes"]:
        if node["name"] == name:
            return node
    raise KeyError(f"node not found: {name}")


def ensure_assignment(node: dict, name: str, value: str) -> bool:
    assignments = node["parameters"]["assignments"]["assignments"]
    for item in assignments:
        if item.get("name") == name:
            if item.get("value") != value:
                item["value"] = value
                return True
            return False
    assignments.append(
        {
            "id": name,
            "name": name,
            "value": value,
            "type": "string",
        }
    )
    return True


def build_search_node(
    base_node: dict,
    *,
    node_id: str,
    name: str,
    position: list[int],
    query_expr: str,
    time_range: str = "week",
) -> dict:
    node = copy.deepcopy(base_node)
    node["id"] = node_id
    node["name"] = name
    node["position"] = position
    params = node["parameters"]
    params["queryParameters"] = {
        "parameters": [
            {"name": "q", "value": query_expr},
            {"name": "format", "value": "json"},
            {"name": "language", "value": "en"},
            {"name": "time_range", "value": time_range},
        ]
    }
    return node


def ensure_node(wf: dict, desired_node: dict) -> bool:
    for index, node in enumerate(wf["nodes"]):
        if node["name"] == desired_node["name"]:
            if node != desired_node:
                wf["nodes"][index] = desired_node
                return True
            return False
    wf["nodes"].append(desired_node)
    return True


def build_execute_node(*, node_id: str, name: str, position: list[int], command: str) -> dict:
    return {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.executeCommand",
        "typeVersion": 1,
        "position": position,
        "parameters": {"command": command},
    }


def ensure_connection(wf: dict, source_name: str, target_name: str) -> bool:
    wf.setdefault("connections", {})
    wf["connections"].setdefault(source_name, {"main": [[]]})
    main = wf["connections"][source_name]["main"]
    if not main:
        main.append([])
    row = main[0]
    if any(conn.get("node") == target_name for conn in row):
        return False
    row.append({"node": target_name, "type": "main", "index": 0})
    return True


def remove_node_by_name(wf: dict, name: str) -> bool:
    before = len(wf["nodes"])
    wf["nodes"] = [node for node in wf["nodes"] if node["name"] != name]
    changed = len(wf["nodes"]) != before
    if name in wf.get("connections", {}):
        del wf["connections"][name]
        changed = True
    for source in wf.get("connections", {}).values():
        for lane in source.get("main", []):
            kept = [conn for conn in lane if conn.get("node") != name]
            if len(kept) != len(lane):
                lane[:] = kept
                changed = True
    return changed


def patch_aggregate_node(node: dict) -> bool:
    desired_code = """
const allItems = $input.all();
const today = new Date().toLocaleDateString('ja-JP', { timeZone: 'Asia/Tokyo' });
const sourceCatalog = [
  {
    title: 'AIモデル',
    matches: ['frontier ai model', 'openai anthropic google deepmind'],
  },
  {
    title: 'ローカルLLM',
    matches: ['qwen llama mistral deepseek'],
  },
  {
    title: '動画・音楽・画像・LipSync',
    matches: ['video generation music generation image generation lipsync'],
  },
  {
    title: 'DeepLearning / 論文',
    matches: ['deep learning research paper'],
  },
  {
    title: '注目発信者 / メディア',
    matches: ['rowan cheung ethan mollick'],
  },
  {
    title: '公式サイト / ニュースレター',
    matches: ['site:rowancheung.com', 'site:rundown.ai', 'site:therundown.ai', 'site:oneusefulthing.org'],
  },
  {
    title: '公式プロフィール / ブログ',
    matches: ['site:alliekmiller.com', 'site:blog.google', 'site:developers.googleblog.com'],
  },
  {
    title: 'YouTube 公開チャンネル',
    matches: ['site:youtube.com', 'site:youtube.com/@aiexplained-official'],
  },
];
const fixedSources = [
  'Rowan Cheung: https://rowancheung.com / https://www.rundown.ai / https://www.therundown.ai',
  'Ethan Mollick: https://www.oneusefulthing.org',
  'Allie K. Miller: https://www.alliekmiller.com',
  'Logan Kilpatrick: https://blog.google/authors/logan-kilpatrick/',
  'AI Explained: https://www.youtube.com/results?search_query=AI+Explained',
];
function classify(query) {
  const lowered = (query || '').toLowerCase();
  for (const entry of sourceCatalog) {
    if (entry.matches.some((token) => lowered.includes(token))) return entry.title;
  }
  return 'その他';
}
const sections = new Map(sourceCatalog.map((entry) => [entry.title, []]));
sections.set('その他', []);
const seen = new Set();
for (const item of allItems) {
  const data = item.json || {};
  const query = data.query || '';
  const category = classify(query);
  for (const hit of (data.results || []).slice(0, 4)) {
    const title = (hit.title || '').trim();
    const url = (hit.url || '').trim();
    if (!title || !url) continue;
    const dedupe = `${title}::${url}`;
    if (seen.has(dedupe)) continue;
    seen.add(dedupe);
    sections.get(category).push(`- ${title}\\n  ${url}`);
  }
}
const publicSourceSections = [];
for (const item of allItems) {
  const data = item.json || {};
  if (!data.stdout) continue;
  try {
    const parsed = JSON.parse(data.stdout);
    for (const sourceEntry of (parsed.sources || [])) {
      const hits = (sourceEntry.results || []).map((result) => `- ${result.title}\\n  ${result.url}`);
      if (hits.length) {
        publicSourceSections.push({
          title: `${sourceEntry.category} (${sourceEntry.source})`,
          hits,
        });
      }
    }
  } catch (error) {
    publicSourceSections.push({
      title: '固定監視先 helper',
      hits: ['- 公開ソース helper の解析に失敗しました'],
    });
  }
}
const parts = [
  `AI Scout 日報 (${today})`,
  '',
  '取得元: SearXNG 経由の公開Web検索',
  '方針: Instagram / X / TikTok の直接スクレイプは使わず、公開ページ・公式サイト・公開YouTubeページのみを対象にしています。',
  '',
  '固定監視先:',
  ...fixedSources.map((line) => `- ${line}`),
  '',
];
for (const [title, hits] of sections.entries()) {
  if (!hits.length) continue;
  parts.push(`■ ${title}`);
  parts.push(...hits.slice(0, 4));
  parts.push('');
}
for (const section of publicSourceSections) {
  parts.push(`■ ${section.title}`);
  parts.push(...section.hits.slice(0, 4));
  parts.push('');
}
parts.push('補足: 公開検索結果ベースの日報です。さらに深掘りが必要なテーマは個別に検索して確認してください。');
return [{ json: { message: parts.join('\\n').trim() } }];
""".strip()
    if node["parameters"].get("jsCode") != desired_code:
        node["parameters"]["jsCode"] = desired_code
        return True
    return False


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

    queries_node = find_node(wf, "Search Queries")
    if ensure_assignment(
        queries_node,
        "q6",
        "Rowan Cheung The Rundown AI latest",
    ):
        status["changes"].append("added q6 official Rowan/The Rundown sources")
    if ensure_assignment(
        queries_node,
        "q7",
        "Ethan Mollick latest AI",
    ):
        status["changes"].append("added q7 Ethan Mollick official site query")
    if ensure_assignment(
        queries_node,
        "q8",
        "Allie K. Miller latest AI",
    ):
        status["changes"].append("added q8 Allie K. Miller official site query")
    if ensure_assignment(
        queries_node,
        "q9",
        "Logan Kilpatrick latest AI",
    ):
        status["changes"].append("added q9 Logan Kilpatrick public Google blog query")
    if ensure_assignment(
        queries_node,
        "q10",
        "AI Explained latest AI YouTube",
    ):
        status["changes"].append("added q10 AI Explained public YouTube query")

    base_search_node = find_node(wf, "Search: AI Models")
    if remove_node_by_name(wf, "Search: Official Experts"):
        status["changes"].append("removed legacy Search: Official Experts node")
    if remove_node_by_name(wf, "Search: YouTube Public"):
        status["changes"].append("removed legacy Search: YouTube Public node")
    new_nodes = [
        build_search_node(
            base_search_node,
            node_id="node-search-official-rowan",
            name="Search: Official Rowan",
            position=[420, 220],
            query_expr="={{ $json.q6 }}",
            time_range="month",
        ),
        build_search_node(
            base_search_node,
            node_id="node-search-ethan-mollick",
            name="Search: Ethan Mollick",
            position=[420, 420],
            query_expr="={{ $json.q7 }}",
            time_range="month",
        ),
        build_search_node(
            base_search_node,
            node_id="node-search-allie-miller",
            name="Search: Allie K. Miller",
            position=[420, 620],
            query_expr="={{ $json.q8 }}",
            time_range="month",
        ),
        build_search_node(
            base_search_node,
            node_id="node-search-logan-kilpatrick",
            name="Search: Logan Kilpatrick",
            position=[420, 820],
            query_expr="={{ $json.q9 }}",
            time_range="month",
        ),
        build_search_node(
            base_search_node,
            node_id="node-search-youtube-ai-explained",
            name="Search: YouTube AI Explained",
            position=[420, 1020],
            query_expr="={{ $json.q10 }}",
            time_range="month",
        ),
        build_execute_node(
            node_id="node-fetch-public-sources",
            name="Fetch: Public Sources",
            position=[420, 1220],
            command="python3 /workspace/fetch_ai_public_sources.py",
        ),
    ]
    for node in new_nodes:
        if ensure_node(wf, node):
            status["changes"].append(f"ensured node {node['name']}")
        if ensure_connection(wf, "Search Queries", node["name"]):
            status["changes"].append(f"connected Search Queries -> {node['name']}")
        if ensure_connection(wf, node["name"], "Aggregate Results"):
            status["changes"].append(f"connected {node['name']} -> Aggregate Results")

    if patch_aggregate_node(find_node(wf, "Aggregate Results")):
        status["changes"].append("expanded Aggregate Results with fixed-source sections")

    updated = None
    if status["changes"]:
        updated = update_workflow(wf)
        status["updatedAt"] = updated.get("updatedAt")

    status["finishedAt"] = now_jst()
    status["step"] = "completed"
    write_status(status)


if __name__ == "__main__":
    main()
