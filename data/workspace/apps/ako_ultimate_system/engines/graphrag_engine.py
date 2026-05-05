import requests

class GraphRAGEngine:
    def run(self, query: str) -> str:
        try:
            # GraphRAG の代用として、Task/不具合の連鎖（依頼者、担当者、ステータス）を検索
            url = f"http://localhost:8792/api/tasks?q={query}&limit=5"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if not results:
                    return f"[GraphRAG] '{query}' に関する因果・タスク関係は見つかりませんでした。"
                
                text = f"[GraphRAG/Task分析結果] ({len(results)}件)\n"
                for r in results:
                    text += f"- [{r['status']}] {r['request_date']} {r['requester']} -> {r['assignee']}: {r['subject']}\n"
                    text += f"  > 原因/概要: {r['summary']}\n"
                    if r['reply_summary']:
                        text += f"  > 対策/回答: {r['reply_summary']}\n"
                return text
            else:
                return f"[GraphRAG ERROR] API status {response.status_code}"
        except Exception as e:
            return f"[GraphRAG ERROR] {str(e)}"
