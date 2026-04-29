from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

client = QdrantClient(host="localhost", port=6333)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
collection = "tool_registry"

tools = [
    {"name": "sql_readonly_query", "summary": "Read-only SQL SELECT query for inspection, defect, SPC, or production data", "risk": "read", "requires": ["db_connected"]},
    {"name": "mqtt_publish", "summary": "Publish press machine telemetry such as SPM, shot count, chokotei to MQTT", "risk": "write", "requires": ["mqtt_connected"]},
    {"name": "nodered_flow_trigger", "summary": "Trigger approved Node-RED flow for CSV transfer, Dropbox upload, or IoT workflow", "risk": "write", "requires": ["nodered_connected"]},
    {"name": "paperless_search", "summary": "Search indexed QA manuals, SDS, drawings, audit reports in Paperless", "risk": "read", "requires": ["paperless_connected"]},
    {"name": "github_backup_then_patch", "summary": "Create GitHub backup branch before large code or layout modification", "risk": "dangerous", "requires": ["github_connected"]},
]

client.recreate_collection(collection_name=collection, vectors_config=VectorParams(size=384, distance=Distance.COSINE))
points = []
for i, t in enumerate(tools):
    points.append(PointStruct(id=i, vector=model.encode(t["summary"]).tolist(), payload=t))
client.upsert(collection_name=collection, points=points)
print(f"initialized {collection} with {len(points)} tools")
