import os
import requests
import json
import uuid
import re
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# --- Configuration ---
MD_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace\ingested_books"
INFINITY_URL = "http://127.0.0.1:7997/embeddings"
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION_NAME = "universal_knowledge"
MODEL_ID = "mixedbread-ai/mxbai-embed-large-v1"
VECTOR_SIZE = 1024 # mxbai-embed-large-v1 dimensions

client = QdrantClient(url=QDRANT_URL)

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def init_qdrant():
    collections = client.get_collections()
    exists = any(c.name == COLLECTION_NAME for c in collections.collections)
    if not exists:
        log(f"Creating collection {COLLECTION_NAME}...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
    else:
        log(f"Collection {COLLECTION_NAME} exists.")

def get_infinity_embedding(text):
    try:
        response = requests.post(INFINITY_URL, json={
            "model": MODEL_ID,
            "input": [text]
        }, timeout=30)
        if response.status_code == 200:
            return response.json()["data"][0]["embedding"]
        else:
            log(f"Infinity Error ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        log(f"Infinity Connection Error: {e}")
        return None

def chunk_markdown(content):
    # Split by headers first to preserve context
    sections = re.split(r'\n(#{1,4} .*)', content)
    chunks = []
    current_chunk = ""
    
    for section in sections:
        if len(current_chunk) + len(section) > 1500: # Limit chunk size
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = section
        else:
            current_chunk += section
            
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Further split long chunks by paragraphs if needed
    final_chunks = []
    for c in chunks:
        if len(c) > 2000:
            sub_chunks = c.split('\n\n')
            final_chunks.extend([sc for sc in sub_chunks if sc.strip()])
        else:
            final_chunks.append(c)
            
    return [c for c in final_chunks if len(c) > 50]

def process_md_file(filepath):
    filename = os.path.basename(filepath)
    rel_path = os.path.relpath(filepath, MD_DIR)
    log(f"Ingesting: {rel_path}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        chunks = chunk_markdown(content)
        points = []
        
        for i, chunk in enumerate(chunks):
            # Attempt to extract page number if common pattern exists
            page_match = re.search(r'--- Page (\d+) ---', chunk)
            page_num = int(page_match.group(1)) if page_match else None
            
            vector = get_infinity_embedding(chunk)
            if vector:
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{rel_path}_{i}"))
                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "source": rel_path,
                        "text": chunk,
                        "page": page_num,
                        "timestamp": datetime.now().isoformat()
                    }
                ))
            
            if len(points) >= 10:
                client.upsert(collection_name=COLLECTION_NAME, points=points)
                points = []
                
        if points:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            
        log(f"Successfully ingested {len(chunks)} chunks from {filename}")
        
    except Exception as e:
        log(f"Error processing {filename}: {e}")

def main():
    log("Starting Universal Knowledge Ingestion...")
    init_qdrant()
    
    md_files = []
    for root, _, files in os.walk(MD_DIR):
        for file in files:
            if file.lower().endswith('.md'):
                md_files.append(os.path.join(root, file))
    
    log(f"Found {len(md_files)} MD files to process.")
    
    for md in md_files:
        process_md_file(md)
    
    log("Ingestion Complete.")

if __name__ == "__main__":
    main()
