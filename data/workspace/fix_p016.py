import json, urllib.request

API = "http://n8n:5678/api/v1"
KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
WF_ID = "sYuks4F4aDvENqpl"

# GET current workflow
req = urllib.request.Request(f"{API}/workflows/{WF_ID}",
    headers={"X-N8N-API-KEY": KEY})
with urllib.request.urlopen(req) as r:
    wf = json.load(r)

# Build clean JS code — each line is a separate string to avoid newline-in-literal issues
lines = [
    "const now = new Date().toLocaleString('ja-JP', {timeZone: 'Asia/Tokyo'});",
    "const first = $input.first();",
    "const report = (first && first.json && (first.json.stdout || first.json.data)) || '(データが空です)';",
    "const reportStr = String(report);",
    "const NL = String.fromCharCode(10);",
    "const truncated = reportStr.length > 3800 ? reportStr.substring(0, 3800) + NL + '...(省略)' : reportStr;",
    "const header = '\U0001F4E7 P016 Email\u5831\u544a (' + now + ')';",
    "const msg = header + NL + NL + truncated;",
    "return [{ json: { text: msg } }];",
]
clean_code = "\n".join(lines)

# Patch the node
patched = False
for node in wf.get("nodes", []):
    if node.get("name") == "\u30e1\u30c3\u30bb\u30fc\u30b8\u6574\u5f62":
        old = node["parameters"].get("jsCode", "")
        node["parameters"]["jsCode"] = clean_code
        patched = True
        print(f"[OK] Patched node. Old length={len(old)}, new length={len(clean_code)}")

if not patched:
    print("[ERROR] Node not found!")
    raise SystemExit(1)

# Build PUT payload (only allowed fields)
allowed = {"name", "nodes", "connections", "settings", "staticData"}
payload = {k: v for k, v in wf.items() if k in allowed}

body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
put_req = urllib.request.Request(
    f"{API}/workflows/{WF_ID}",
    data=body,
    headers={"X-N8N-API-KEY": KEY, "Content-Type": "application/json"},
    method="PUT",
)
with urllib.request.urlopen(put_req) as r:
    resp = json.load(r)

print(f"[OK] Updated. updatedAt={resp.get('updatedAt')} active={resp.get('active')}")

# Verify: re-fetch and check
req2 = urllib.request.Request(f"{API}/workflows/{WF_ID}",
    headers={"X-N8N-API-KEY": KEY})
with urllib.request.urlopen(req2) as r:
    wf2 = json.load(r)
for node in wf2.get("nodes", []):
    if node.get("name") == "\u30e1\u30c3\u30bb\u30fc\u30b8\u6574\u5f62":
        saved = node["parameters"].get("jsCode", "")
        print("[VERIFY] Saved code (first 200 chars):", repr(saved[:200]))
        if "\n" in saved.split("3800")[1][:30]:
            print("[WARN] Still contains literal newline after 3800!")
        else:
            print("[OK] No literal newline in string literal area")
