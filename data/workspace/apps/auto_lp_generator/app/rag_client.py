import os, requests

def rag_suggest_context(theme: str, source_hint: str = "") -> str:
    gateway=os.getenv("OPENCLAW_GATEWAY_URL","").rstrip('/')
    token=os.getenv("OPENCLAW_BEARER_TOKEN","")
    if not gateway or not token:
        return "OpenClaw RAG未設定。OPENCLAW_GATEWAY_URL と OPENCLAW_BEARER_TOKEN を設定すると資料検索を接続できます。"
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"}
    payload={"query":f"{theme} {source_hint} 品質保証 IATF 工程 不良 是正","top_k":5}
    errors=[]
    for url in [f"{gateway}/rag/search", f"{gateway}/api/rag/search", f"{gateway}/search"]:
        try:
            r=requests.post(url,json=payload,headers=headers,timeout=20)
            if r.status_code < 400: return str(r.json())[:4000]
            errors.append(f"{url}: {r.status_code}")
        except Exception as e: errors.append(f"{url}: {e}")
    return "RAG接続失敗: " + " / ".join(errors)
