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
STATUS_PATH = ROOT / "data" / "workspace" / "ai_scout_rankings_status.json"
JST = timezone(timedelta(hours=9))
TS = datetime.now(JST).strftime("%Y%m%d_%H%M%S")


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(status: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    headers = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def backup_workflow(wf: dict) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"workflow_{wf['id']}_ai_scout_rankings_{TS}.json"
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def find_node(wf: dict, name: str) -> dict:
    for node in wf["nodes"]:
        if node["name"] == name:
            return node
    raise KeyError(f"node not found: {name}")


def build_execute_node(*, node_id: str, name: str, position: list[int], command: str) -> dict:
    return {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.executeCommand",
        "typeVersion": 1,
        "position": position,
        "parameters": {"command": command},
    }


def ensure_node(wf: dict, desired_node: dict) -> bool:
    for index, node in enumerate(wf["nodes"]):
        if node["name"] == desired_node["name"]:
            if node != desired_node:
                wf["nodes"][index] = desired_node
                return True
            return False
    wf["nodes"].append(desired_node)
    return True


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


def patch_aggregate_node(node: dict) -> bool:
    desired_code = """
const allItems = $input.all();
const today = new Date().toLocaleDateString('ja-JP', { timeZone: 'Asia/Tokyo' });
const searchCategories = [
  { key: 'frontier ai model', title: 'AIモデル' },
  { key: 'qwen llama mistral deepseek', title: 'ローカルLLM' },
  { key: 'video generation music generation image generation lipsync', title: '動画・音楽・画像・LipSync' },
  { key: 'deep learning research paper', title: 'DeepLearning / 論文' },
  { key: 'rowan cheung ethan mollick', title: '注目発信者 / メディア' },
];
function classify(query) {
  const lowered = (query || '').toLowerCase();
  for (const entry of searchCategories) {
    if (lowered.includes(entry.key)) return entry.title;
  }
  return 'その他';
}
const sections = new Map(searchCategories.map((entry) => [entry.title, []]));
sections.set('その他', []);
const fixedSourceSections = [];
let rankingPayload = null;
const seen = new Set();
for (const item of allItems) {
  const data = item.json || {};
  if (data.stdout) {
    try {
      const parsed = JSON.parse(data.stdout);
      if (parsed.sources) {
        for (const sourceEntry of parsed.sources) {
          const hits = (sourceEntry.results || []).map((result) => `- ${result.title}\\n  ${result.url}`);
          if (hits.length) {
            fixedSourceSections.push({
              title: `${sourceEntry.category} (${sourceEntry.source})`,
              hits,
            });
          }
        }
      }
      if (parsed.cloud_rankings) {
        rankingPayload = parsed;
      }
    } catch (error) {
    }
    continue;
  }
  const category = classify(data.query || '');
  for (const hit of (data.results || []).slice(0, 3)) {
    const title = (hit.title || '').trim();
    const url = (hit.url || '').trim();
    if (!title || !url) continue;
    const dedupe = `${title}::${url}`;
    if (seen.has(dedupe)) continue;
    seen.add(dedupe);
    sections.get(category).push(`- ${title}\\n  ${url}`);
  }
}
const parts = [
  `AI Scout / モデルランキング日報 (${today})`,
  '',
];
if (rankingPayload) {
  parts.push(`端末: ${rankingPayload.hardware.machine} / ${rankingPayload.hardware.cpu} / ${rankingPayload.hardware.ram} / ${rankingPayload.hardware.gpu}`);
  parts.push('');
  parts.push('■ クラウドAI 総合');
  parts.push(`- ${rankingPayload.cloud_rankings.overall.join(' / ')}`);
  parts.push('■ クラウドAI 賢さ');
  parts.push(`- ${rankingPayload.cloud_rankings.smartest.join(' / ')}`);
  parts.push('■ クラウドAI 速さ');
  parts.push(`- ${rankingPayload.cloud_rankings.fastest.join(' / ')}`);
  parts.push('■ クラウドAI 価格');
  parts.push(`- ${rankingPayload.cloud_rankings.lowest_cost.join(' / ')}`);
  parts.push('');
  parts.push('■ ローカルAI 総合');
  parts.push(`- ${rankingPayload.local_rankings.overall_open.join(' / ')}`);
  parts.push('■ ローカルAI 賢さ');
  parts.push(`- ${rankingPayload.local_rankings.smartest_open.join(' / ')}`);
  parts.push('■ ローカルAI 実用');
  parts.push(`- ${rankingPayload.local_rankings.practical_local.join(' / ')}`);
  parts.push('');
  parts.push('■ このMiniPC向け推奨');
  parts.push(`- 総合おすすめ: ${rankingPayload.mini_pc_recommendation.overall.model} (${rankingPayload.mini_pc_recommendation.overall.reason})`);
  parts.push(`- 速度優先: ${rankingPayload.mini_pc_recommendation.fast.model} (${rankingPayload.mini_pc_recommendation.fast.reason})`);
  parts.push(`- 既定非推奨: ${rankingPayload.mini_pc_recommendation.avoid_default.join(' / ')}`);
  parts.push(`- 次に試す候補: ${rankingPayload.mini_pc_recommendation.next_try.join(' / ')}`);
  parts.push(`- ローカル搭載: ${(rankingPayload.installed_local_models || []).join(', ') || '取得失敗'}`);
  parts.push('');
  parts.push('■ 参照元チェック');
  for (const ref of (rankingPayload.references_checked || [])) {
    parts.push(`- ${ref.name}: ${ref.status}`);
    parts.push(`  ${ref.url}`);
  }
  parts.push('');
}
for (const [title, hits] of sections.entries()) {
  if (!hits.length) continue;
  parts.push(`■ ${title}`);
  parts.push(...hits.slice(0, 3));
  parts.push('');
}
for (const section of fixedSourceSections) {
  parts.push(`■ ${section.title}`);
  parts.push(...section.hits.slice(0, 3));
  parts.push('');
}
parts.push('参照元: Artificial Analysis / LMArena / Hugging Face Open LLM Leaderboard / Intel Low-bit Quantized Open LLM Leaderboard / LM Studio Model Catalog / Ollama Library');
parts.push('方針: 公開ページと公開RSSのみ。Instagram / X / TikTok の直接スクレイプは使わない。');
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
    status = {"startedAt": now_jst(), "step": "patching", "workflowId": WORKFLOW_ID, "changes": []}
    write_status(status)
    wf = request_json(f"/workflows/{WORKFLOW_ID}")
    status["backup"] = backup_workflow(wf)

    ranking_node = build_execute_node(
        node_id="node-fetch-model-rankings",
        name="Fetch: Model Rankings",
        position=[420, 1420],
        command="python3 /workspace/fetch_ai_model_rankings.py",
    )
    if ensure_node(wf, ranking_node):
        status["changes"].append("ensured node Fetch: Model Rankings")
    if ensure_connection(wf, "Search Queries", "Fetch: Model Rankings"):
        status["changes"].append("connected Search Queries -> Fetch: Model Rankings")
    if ensure_connection(wf, "Fetch: Model Rankings", "Aggregate Results"):
        status["changes"].append("connected Fetch: Model Rankings -> Aggregate Results")
    if patch_aggregate_node(find_node(wf, "Aggregate Results")):
        status["changes"].append("patched Aggregate Results for rankings report")

    if status["changes"]:
        updated = update_workflow(wf)
        status["updatedAt"] = updated.get("updatedAt")

    status["finishedAt"] = now_jst()
    status["step"] = "completed"
    write_status(status)


if __name__ == "__main__":
    main()
