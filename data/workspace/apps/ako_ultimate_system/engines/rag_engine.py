import requests
import json

class RAGEngine:
    def run(self, query: str) -> str:
        try:
            url = f"http://localhost:8792/api/search?q={query}&limit=5"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if not results:
                    return f"[RAG] '{query}' に関する情報は見つかりませんでした。"
                
                text = f"[Email Search API 結果] ({len(results)}件)\n"
                for r in results:
                    text += f"- {r['email_date']} {r['sender']}: {r['subject']}\n"
                    text += f"  > {r['snippet']}\n"
                return text
            else:
                return f"[RAG ERROR] API returned status {response.status_code}"
        except Exception as e:
            return f"[RAG ERROR] {str(e)}"
