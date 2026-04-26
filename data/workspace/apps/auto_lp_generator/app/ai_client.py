import os, requests

def ai_refine_brief(theme: str, rag_context: str = "") -> str:
    mode=os.getenv("AI_MODE","local_template")
    if mode != "litellm":
        return f"""【ローカル構成案】
テーマ: {theme}

1. 課題提示
2. KPIサマリー
3. 工程フロー
4. 不良・是正の見える化
5. 顧客/監査員向け説明
6. 次アクション

RAG参考:
{rag_context[:1200] if rag_context else 'RAG未接続。'}"""
    base=os.getenv("LITELLM_BASE_URL","http://127.0.0.1:4000").rstrip('/')
    model=os.getenv("LITELLM_MODEL","google/gemini-2.5-flash")
    key=os.getenv("LITELLM_API_KEY","")
    headers={"Content-Type":"application/json"}
    if key: headers["Authorization"]=f"Bearer {key}"
    payload={"model":model,"messages":[{"role":"system","content":"製造業QA向けLPの情報設計者として簡潔に構成案を作る。"},{"role":"user","content":f"テーマ: {theme}\n参考情報:\n{rag_context}"}],"temperature":0.3}
    try:
        r=requests.post(f"{base}/v1/chat/completions",json=payload,headers=headers,timeout=30); r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"LiteLLM呼び出し失敗。ローカル案にフォールバック: {e}"
