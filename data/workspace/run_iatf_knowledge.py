import time
import os
import glob
import requests
import json
import shutil
from datetime import datetime
import sys
import subprocess

# Ensure libraries
try:
    import pypdf
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
    import pypdf

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "qdrant-client"])
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct

# Configuration
# Path inside container (assuming mapped)
WATCH_DIR = "/home/node/paperless/consume/IATF_documents"
ARCHIVE_DIR = "/home/node/paperless/consume/IATF_documents/processed_by_knowledge" # Temp safe spot? 
# Note: Paperless might consume files. Best to process VERY fast or rely on Paperless API.
# For this prototype, we assume we catch them or they are static.
# If Paperless is aggressive, we might need a different strategy.
# Let's assume files are placed here.

OLLAMA_URL = "http://ollama:11434/api/embeddings"
MODEL_NAME = "nomic-embed-text"
QDRANT_URL = "http://qdrant:6333"
COLLECTION_NAME = "iatf_knowledge"

client = QdrantClient(url=QDRANT_URL)

def log(msg):
    print(f"[{datetime.now()}] {msg}")

def init_qdrant():
    collections = client.get_collections()
    exists = any(c.name == COLLECTION_NAME for c in collections.collections)
    if not exists:
        log(f"Creating collection {COLLECTION_NAME}...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
    else:
        log(f"Collection {COLLECTION_NAME} exists.")

def get_embedding(text):
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": text
        })
        if response.status_code == 200:
            return response.json()["embedding"]
        else:
            log(f"Ollama Error: {response.text}")
            return None
    except Exception as e:
        log(f"Embedding Error: {e}")
        return None

def extract_text_from_pdf(filepath):
    text = ""
    try:
        reader = pypdf.PdfReader(filepath)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        log(f"PDF Read Error: {e}")
    return text

def process_file(filepath):
    log(f"Processing knowledge: {filepath}")
    filename = os.path.basename(filepath)
    
    # 1. Extract
    full_text = extract_text_from_pdf(filepath)
    if not full_text:
        return

    # 2. Chunk (Simple split by paragraphs or length)
    chunks = [chunk for chunk in full_text.split('\n\n') if len(chunk) > 50]
    
    # 3. Embed & Store
    points = []
    for i, chunk in enumerate(chunks):
        vector = get_embedding(chunk)
        if vector:
            points.append(PointStruct(
                id=abs(hash(f"{filename}_{i}")), # Simple deterministic hash
                vector=vector,
                payload={"source": filename, "text": chunk, "chunk_id": i}
            ))
            
            # Batch upload every 10 chunks
            if len(points) >= 10:
                client.upsert(collection_name=COLLECTION_NAME, points=points)
                points = []

    # Upload remaining
    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    log(f"Ingested {len(chunks)} chunks from {filename}.")

def main():
    log("Clawdbot IATF Knowledge Agent Started.")
    init_qdrant()
    
    processed_files = set()
    
    while True:
        # Recursive search for PDFs
        files = glob.glob(os.path.join(WATCH_DIR, "**/*.pdf"), recursive=True)
        for f in files:
            if f not in processed_files:
                try:
                    process_file(f)
                    processed_files.add(f)
                except Exception as e:
                    log(f"Error processing {f}: {e}")
        
        time.sleep(60) # Check every minute

if __name__ == "__main__":
    main()
