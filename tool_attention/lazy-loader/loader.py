from fastapi import FastAPI, HTTPException

app = FastAPI(title="Lazy MCP Schema Loader")

SCHEMAS = {
    "sql_readonly_query": {"description": "Run SELECT-only SQL query", "parameters": {"query": "string"}, "guard": "reject non-SELECT"},
    "mqtt_publish": {"description": "Publish telemetry to MQTT broker", "parameters": {"topic": "string", "payload": "object"}},
    "nodered_flow_trigger": {"description": "Trigger approved Node-RED flow", "parameters": {"flow_id": "string", "input": "object"}},
    "paperless_search": {"description": "Search Paperless indexed documents", "parameters": {"query": "string"}},
    "github_backup_then_patch": {"description": "Create GitHub backup branch before large code patch", "parameters": {"repo": "string", "branch": "string"}, "requires_human_approval": True},
}

@app.get("/schema/{tool_name}")
def schema(tool_name: str):
    if tool_name not in SCHEMAS:
        raise HTTPException(status_code=404, detail="schema not found")
    return {"tool": tool_name, "schema": SCHEMAS[tool_name]}
