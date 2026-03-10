#!/bin/sh
# LiteLLM custom entrypoint
# 1. Pre-install orjson so fastapi sees it before it's imported (LiteLLM v1.10.1 bug)
# 2. Patch proxy_server.py to strip chat-only params from /v1/embeddings requests
#    (OpenClaw's memory_search sends 'messages' alongside embedding input)

# Pre-install orjson BEFORE litellm imports fastapi
pip install orjson -q 2>&1 | grep -v "^$" || true

# Apply patch to strip 'messages' from embedding requests
python3 - <<'PYEOF'
import sys

f = "/usr/local/lib/python3.9/site-packages/litellm/proxy/proxy_server.py"
try:
    with open(f, "r") as fh:
        content = fh.read()
except Exception as e:
    print(f"[litellm-patch] Could not read {f}: {e}", flush=True)
    sys.exit(0)

old = '''        if "metadata" in data:
            data["metadata"]["user_api_key"] = user_api_key_dict["api_key"]
        else:
            data["metadata"] = {"user_api_key": user_api_key_dict["api_key"]}

        ## ROUTE TO CORRECT ENDPOINT ##'''

new = '''        if "metadata" in data:
            data["metadata"]["user_api_key"] = user_api_key_dict["api_key"]
        else:
            data["metadata"] = {"user_api_key": user_api_key_dict["api_key"]}

        ## Strip chat-only params that break embedding clients (e.g. OpenClaw sends 'messages')
        for _chat_param in ["messages", "temperature", "stream", "max_tokens", "stop",
                            "functions", "tools", "response_format", "top_p", "n",
                            "presence_penalty", "frequency_penalty", "logit_bias"]:
            data.pop(_chat_param, None)

        ## ROUTE TO CORRECT ENDPOINT ##'''

if old not in content:
    if new in content:
        print("[litellm-patch] Patch already applied, skipping.", flush=True)
    else:
        print("[litellm-patch] WARNING: Target string not found - version may have changed.", flush=True)
    sys.exit(0)

patched = content.replace(old, new, 1)
with open(f, "w") as fh:
    fh.write(patched)

print("[litellm-patch] SUCCESS: Patched proxy_server.py to strip chat params from embedding requests.", flush=True)
PYEOF

exec litellm --config /app/proxy_server_config.yaml --port 4000
