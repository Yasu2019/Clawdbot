import requests
import json

INFINITY_URL = "http://127.0.0.1:7997/embeddings"
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION_NAME = "universal_knowledge"
MODEL_ID = "mixedbread-ai/mxbai-embed-large-v1"

def test_search(query):
    print(f"Query: {query}")
    
    # 1. Embed query
    res = requests.post(INFINITY_URL, json={"model": MODEL_ID, "input": [query]})
    vector = res.json()["data"][0]["embedding"]
    
    # 2. Search Qdrant
    res = requests.post(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search", json={
        "vector": vector,
        "limit": 3,
        "with_payload": True
    })
    
    results = res.json()["result"]
    for i, r in enumerate(results):
        print(f"\n--- Result {i+1} (Score: {r['score']:.4f}) ---")
        print(f"Source: {r['payload']['source']}")
        print(f"Snippet: {r['payload']['text'][:300]}...")

if __name__ == "__main__":
    test_search("なぜなぜ分析の10則について教えて")
