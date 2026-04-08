#!/bin/sh
# LiteLLM custom entrypoint
# NOTE: `litellm` CLI uses site-packages, not /app.
# All functional patches target site-packages; /app patches are kept for parity.
#
# 1. Pre-install orjson so fastapi sees it before it's imported (LiteLLM v1.10.1 bug)
# 2. Patch proxy_server.py (both) to strip chat-only params from /v1/embeddings requests
# 3. Patch proxy_server.py site-packages to fix async routing for openai/* local models
# 4. Patch ollama.py to use OLLAMA_API_BASE env var (both locations)
# 5. Patch main.py Ollama api_base resolution (both locations)
# 6. Patch openai.py api_key fallback (both locations)

# Pre-install orjson BEFORE litellm imports fastapi
pip install orjson -q 2>&1 | grep -v "^$" || true

# Apply all patches
python3 - <<'PYEOF'
import sys, os, re

# ── Patch 1: proxy_server.py — strip chat params from embedding requests ──────
# Applies to BOTH /app (old sync) and site-packages (async FastAPI used by CLI)
def patch_proxy_server_embedding(f):
    try:
        with open(f) as fh:
            content = fh.read()
    except Exception as e:
        print(f"[embed-patch] Could not read {f}: {e}", flush=True)
        return

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

    if new in content:
        print(f"[embed-patch] Already applied: {f}", flush=True)
        return
    if old not in content:
        print(f"[embed-patch] WARNING: Target string not found in {f}", flush=True)
        return
    with open(f, "w") as fh:
        fh.write(content.replace(old, new, 1))
    print(f"[embed-patch] SUCCESS: Patched {f}", flush=True)

for _f in ["/app/litellm/proxy/proxy_server.py",
           "/usr/local/lib/python3.9/site-packages/litellm/proxy/proxy_server.py"]:
    patch_proxy_server_embedding(_f)

# ── Patch 2: site-packages proxy_server.py — fix async routing for local models ─
# The litellm CLI uses site-packages async FastAPI proxy.
# When llm_router misses a model (openai/* local models), fall back to litellm_params.
def patch_proxy_routing():
    f = "/usr/local/lib/python3.9/site-packages/litellm/proxy/proxy_server.py"
    MARKER = "[routing-fix-v1]"
    try:
        with open(f) as fh:
            content = fh.read()
    except Exception as e:
        print(f"[routing-fix] Could not read {f}: {e}", flush=True)
        return
    if MARKER in content:
        print(f"[routing-fix] Already patched: {f}", flush=True)
        return
    OLD = (
        '        router_model_names = [m["model_name"] for m in llm_model_list] if llm_model_list is not None else []\n'
        '        if llm_router is not None and data["model"] in router_model_names: # model in router model list \n'
        '                response = await llm_router.acompletion(**data)\n'
        '        else: \n'
        '            response = await litellm.acompletion(**data)'
    )
    NEW = (
        '        router_model_names = [m["model_name"] for m in llm_model_list] if llm_model_list is not None else []  # ' + MARKER + '\n'
        '        print(f"[routing-fix] REQ model={data.get(chr(39)+chr(109)+chr(111)+chr(100)+chr(101)+chr(108)+chr(39))} router={llm_router is not None} names={router_model_names}", flush=True)\n'
        '        _mdl_entry = next((m for m in (llm_model_list or []) if m["model_name"] == data.get("model")), None)\n'
        '        if llm_router is not None and data["model"] in router_model_names: # model in router model list \n'
        '                response = await llm_router.acompletion(**data)\n'
        '        elif _mdl_entry is not None:\n'
        '            _lp = _mdl_entry.get("litellm_params", {})\n'
        '            _d = dict(data)\n'
        '            _d["model"] = _lp.get("model", _d["model"])\n'
        '            if "api_base" in _lp: _d.setdefault("api_base", _lp["api_base"])\n'
        '            if "api_key" in _lp: _d.setdefault("api_key", _lp["api_key"])\n'
        '            print(f"[routing-fix] FALLBACK model={_d.get(chr(39)+chr(109)+chr(111)+chr(100)+chr(101)+chr(108)+chr(39))} api_base={_d.get(chr(39)+chr(97)+chr(112)+chr(105)+chr(95)+chr(98)+chr(97)+chr(115)+chr(101)+chr(39))}", flush=True)\n'
        '            response = await litellm.acompletion(**_d)\n'
        '        else: \n'
        '            response = await litellm.acompletion(**data)'
    )
    if OLD not in content:
        print(f"[routing-fix] WARNING: Target block not found. Showing context:", flush=True)
        idx = content.find('router_model_names = [m["model_name"]')
        if idx >= 0:
            print(repr(content[idx:idx+400]), flush=True)
        return
    with open(f, "w") as fh:
        fh.write(content.replace(OLD, NEW, 1))
    print(f"[routing-fix] SUCCESS: Patched {f}", flush=True)

patch_proxy_routing()

# ── Patch 3: ollama.py — replace localhost:11434 default with OLLAMA_API_BASE ─
def patch_ollama(filepath):
    OLD = '"http://localhost:11434"'
    NEW = 'os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")'
    try:
        with open(filepath) as fh:
            content = fh.read()
    except:
        return False
    if NEW in content:
        return None  # already patched
    if OLD not in content:
        return False  # not found
    patched = content.replace(OLD, NEW)
    if 'import os' not in patched[:300]:
        patched = 'import os\n' + patched
    with open(filepath, "w") as fh:
        fh.write(patched)
    return True

for p in ["/app/litellm/llms/ollama.py",
          "/usr/local/lib/python3.9/site-packages/litellm/llms/ollama.py"]:
    result = patch_ollama(p)
    if result is True:
        print(f"[ollama-patch] SUCCESS: Patched {p}", flush=True)
    elif result is None:
        print(f"[ollama-patch] Already patched: {p}", flush=True)

# ── Patch 4: main.py — fix Ollama api_base to use OLLAMA_API_BASE env var ─────
def patch_main(filepath):
    MARKER = '[main-patch-v2]'
    try:
        with open(filepath) as fh:
            content = fh.read()
    except:
        return False
    if MARKER in content:
        return None  # already patched
    OLD_PAT = r'elif custom_llm_provider == "ollama":\s+api_base = \(\s+litellm\.api_base or\s+api_base or\s+get_secret\("OLLAMA_API_BASE"\) or\s+"http://localhost:11434"\s+\)'
    NEW_CODE = ('elif custom_llm_provider == "ollama":  # ' + MARKER + '\n'
                '            _ollama_env = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")\n'
                '            api_base = litellm.api_base or api_base or _ollama_env')
    match = re.search(OLD_PAT, content, re.DOTALL)
    if not match:
        return False
    patched = content[:match.start()] + NEW_CODE + content[match.end():]
    if 'import os' not in patched[:1000]:
        patched = 'import os\n' + patched
    with open(filepath, "w") as fh:
        fh.write(patched)
    return True

for p in ["/app/litellm/main.py",
          "/usr/local/lib/python3.9/site-packages/litellm/main.py"]:
    result = patch_main(p)
    if result is True:
        print(f"[main-patch] SUCCESS: Patched {p}", flush=True)
    elif result is None:
        print(f"[main-patch] Already patched: {p}", flush=True)
    elif result is False:
        print(f"[main-patch] WARNING: Pattern not found in {p}", flush=True)

# ── Patch 5: openai.py — api_key None → fall back to OPENAI_API_KEY env var ──
def patch_openai(filepath):
    OLD = 'openai_aclient = AsyncOpenAI(api_key=api_key, base_url=api_base,'
    NEW = 'openai_aclient = AsyncOpenAI(api_key=api_key if api_key is not None else os.environ.get("OPENAI_API_KEY"), base_url=api_base,'
    try:
        with open(filepath) as fh:
            content = fh.read()
    except:
        return False
    if NEW in content:
        return None
    if OLD not in content:
        return False
    patched = content.replace(OLD, NEW)
    if 'import os' not in patched[:300]:
        patched = 'import os\n' + patched
    with open(filepath, "w") as fh:
        fh.write(patched)
    return True

for p in ["/app/litellm/llms/openai.py",
          "/usr/local/lib/python3.9/site-packages/litellm/llms/openai.py"]:
    result = patch_openai(p)
    if result is True:
        print(f"[openai-patch] SUCCESS: Patched {p}", flush=True)
    elif result is None:
        print(f"[openai-patch] Already patched: {p}", flush=True)

PYEOF

# Clear Python bytecode cache and recompile from patched sources
find /app/litellm -name "*.pyc" -delete 2>/dev/null || true
find /usr/local/lib/python3.9/site-packages/litellm -name "*.pyc" -delete 2>/dev/null || true
# Force recompile patched modules so litellm CLI loads fresh bytecode
python3 -m compileall -q /usr/local/lib/python3.9/site-packages/litellm/proxy/ \
                          /usr/local/lib/python3.9/site-packages/litellm/llms/ \
                          /usr/local/lib/python3.9/site-packages/litellm/ \
                          /app/litellm/proxy/ \
                          /app/litellm/llms/ \
                          2>/dev/null || true

exec litellm --config /app/proxy_server_config.yaml --port 4000
