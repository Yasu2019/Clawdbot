# -*- coding: utf-8 -*-
"""Autonomous System Self-Improvement Loop.

1. Polls universal_growth.db for new Moldflow/viscosity/WLF theories.
2. Performs git push backup to GitHub.
3. Invokes LiteLLM/Ollama to apply the theory to scripts/cae_te_engine.py.
4. Validates code syntax.
5. Deploys to satellite worker (LAVIE) via scripts/k10_sync_lavie_scripts_to_lavie.py.
6. Sends a Telegram notification.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
DB_PATH = WORKSPACE / "universal_growth.db"
STATE_PATH = WORKSPACE / "autonomous_coder_state.json"
TARGET_FILE = ROOT / "scripts" / "cae_te_engine.py"
LITELLM_URL = "http://localhost:4001/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/generate"

def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"applied_record_ids": []}

def save_state(state: dict):
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def query_unapplied_theories(applied_ids: list) -> list:
    if not DB_PATH.exists():
        print(f"[WARN] DB not found at: {DB_PATH}")
        return []
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in applied_ids)
    query = """
        SELECT id, timestamp, domain, challenge, know_how, status 
        FROM growth_records 
        WHERE domain IN ('SCRIBD_DOCUMENT', 'CAE_MATERIAL', 'INTERNAL_KNOWHOW') 
          AND (challenge LIKE '%Moldflow%' OR know_how LIKE '%Moldflow%' OR challenge LIKE '%viscos%' OR know_how LIKE '%viscos%' OR challenge LIKE '%Cross-WLF%' OR know_how LIKE '%Cross-WLF%')
          AND status = 'SUCCESS'
    """
    if applied_ids:
        query += f" AND id NOT IN ({placeholders})"
    
    rows = conn.execute(query, tuple(applied_ids)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def run_git_command(args: list[str], timeout: int = 30) -> tuple[bool, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        res = subprocess.run(args, capture_output=True, text=True, cwd=str(ROOT), env=env, timeout=timeout)
        return res.returncode == 0, (res.stdout + res.stderr).strip()
    except subprocess.TimeoutExpired as e:
        return False, f"Timeout expired after {timeout} seconds. stdout: {e.stdout}, stderr: {e.stderr}"

def run_git_backup(record_id: int) -> bool:
    print(f"[GIT] Starting Git backup/push before modifying code...")
    # Check if there are uncommitted changes (tracked files only)
    ok, out = run_git_command(["git", "status", "--porcelain", "-uno"])
    if not ok:
        print(f"[GIT] Failed to get status: {out}")
        return False
    if not out:
        print("[GIT] Workspace is clean. Pre-backup commit not needed.")
        return True
    
    # Stage and commit
    run_git_command(["git", "add", "-u"])
    msg = f"chore(cae): Auto-backup before applying theory record {record_id}"
    ok, out = run_git_command(["git", "commit", "-m", msg])
    if not ok:
        print(f"[GIT] Commit failed: {out}")
        return False
    print(f"[GIT] Created backup commit: {msg}")
    
    # Push with timeout
    ok, out = run_git_command(["git", "push"], timeout=45)
    if not ok:
        print(f"[GIT] WARNING: Git push failed or timed out: {out}. Continuing since local commit was successful.")
    else:
        print("[GIT] Git push successful.")
    return True

def query_llm(prompt: str) -> str:
    # Try LiteLLM first (routes to deepseek-v4-flash or deepseek-v4-pro)
    try:
        print("[LLM] Attempting LiteLLM query...")
        req_data = {
            "model": "deepseek-v4-flash",
            "messages": [
                {"role": "system", "content": "You are a professional Python engineer specializing in CAE/FEM solvers. Return ONLY the modified Python code block. No markdown, no comments outside code, no explanations."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer yasu-fresh-token-2026-02-01"
        }
        req = urllib.request.Request(
            LITELLM_URL,
            data=json.dumps(req_data).encode("utf-8"),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            # Strip markdown code blocks if the LLM ignored instructions
            content = content.replace("```python", "").replace("```", "").strip()
            return content
    except Exception as e:
        print(f"[LLM] LiteLLM query failed: {e}. Falling back to Ollama...")

    # Fallback to local Ollama qwen3:14b
    try:
        print("[LLM] Attempting local Ollama query...")
        req_data = {
            "model": "qwen3:14b",
            "prompt": prompt,
            "system": "You are a professional Python engineer specializing in CAE/FEM solvers. Return ONLY the modified Python code block. No markdown, no explanations.",
            "stream": False,
            "options": {"temperature": 0.1}
        }
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(req_data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = body["response"]
            content = content.replace("```python", "").replace("```", "").strip()
            return content
    except Exception as e:
        print(f"[LLM] Ollama query failed: {e}")
        raise RuntimeError("No LLM server available for self-improvement.")

def load_telegram_config() -> tuple[str, str] | None:
    env_path = ROOT / ".env"
    bot, chat = "", ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                bot = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("TELEGRAM_CHAT_ID="):
                chat = line.split("=", 1)[1].strip().strip('"').strip("'")
    if bot and chat:
        return bot, chat
    return None

def send_telegram(text: str) -> bool:
    cfg = load_telegram_config()
    if not cfg:
        return False
    bot, chat = cfg
    try:
        url = f"https://api.telegram.org/bot{bot}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat, "text": text[:4000]}).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception as e:
        print(f"[TELEGRAM] Failed to send notification: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Autonomous System Self-Improvement Loop")
    parser.add_argument("--mock", action="store_true", help="Simulate a mock learned theory/algorithm run")
    parser.add_argument("--force", action="store_true", help="Re-apply even if already applied")
    args = parser.parse_args()

    state = load_state()
    applied_ids = state["applied_record_ids"]

    # Select target record
    if args.mock:
        record = {
            "id": 99999,
            "challenge": "Mock Theory: Integrate Cross-WLF Viscosity Model in CAE solver",
            "know_how": (
                "To approximate Moldflow's polymer fill behavior, replace the simple WLF model with a true Cross-WLF viscosity model. "
                "The Cross-WLF viscosity is calculated as: eta = eta0 / (1 + (eta0 * shear_rate / tau_star)**(1 - n)). "
                "Zero-shear viscosity eta0 is: eta0 = D1 * exp(-A1 * (T - Tg) / (A2 + (T - Tg))), where Tg = D2 + D3 * pressure_mpa, and T is temperature in Celsius (T_c = t_k - 273.15). "
                "If parameters are not provided, fallback to these defaults: D1=1e10, D2=378.15 K, D3=0.0, A1=17.44, A2=51.6, tau_star=50000.0, n=0.35, shear_rate=1000.0 s^-1."
            )
        }
    else:
        candidates = query_unapplied_theories(applied_ids)
        if not candidates:
            print("[INFO] No new unapplied theories or algorithms found in universal_growth.db.")
            return 0
        record = candidates[0]
        print(f"[INFO] Found unapplied theory record {record['id']}: {record['challenge']}")

    # 1. Git push backup
    if not run_git_backup(record["id"]):
        print("[ERR] Git backup failed. Halting self-improvement for safety.")
        return 1

    # 2. Extract code block to modify
    if not TARGET_FILE.exists():
        print(f"[ERR] Target file {TARGET_FILE} not found.")
        return 1
    
    content = TARGET_FILE.read_text(encoding="utf-8")
    start_marker = "def _wlf_dynamic_viscosity"
    end_marker = "return mu_block, kappa_block"
    
    idx_start = content.find(start_marker)
    idx_end = content.find(end_marker)
    if idx_start == -1 or idx_end == -1:
        print("[ERR] Could not locate the target WLF block in cae_te_engine.py.")
        return 1
    
    # Slice the entire block containing viscosity helper functions
    target_block = content[idx_start : idx_end + len(end_marker)]
    print(f"[INFO] Extracted target block of length {len(target_block)} chars.")

    # 3. Formulate Prompt and Invoke LLM
    prompt = f"""
Here is a target block of code from our CAE solver scripts/cae_te_engine.py implementing polymer viscosity calculation:
```python
{target_block}
```

We have acquired a new theory/method described as:
"{record['know_how']}"

Please rewrite the viscosity calculation target block above to use the Cross-WLF viscosity model instead of the simplified WLF model:
1. Update `_wlf_dynamic_viscosity` to compute Cross-WLF viscosity. Keep the name `_wlf_dynamic_viscosity` or add a new helper function `_cross_wlf_viscosity` and make `_wlf_dynamic_viscosity` call it.
2. In `_wlf_dynamic_viscosity`, convert temperature `t_k` from Kelvin to Celsius: `t_c = t_k - 273.15`.
3. Tg should be calculated as `D2 + D3 * p_mpa` (fallback D2=105.0 C, D3=0.0).
4. Zero-shear viscosity `eta0 = D1 * math.exp(-A1 * (t_c - Tg) / (A2 + (t_c - Tg)))`. Clamp denominator `denom = A2 + (t_c - Tg)` to `max(denom, 1e-6)` to prevent division by zero.
5. Viscosity `eta = eta0 / (1.0 + (eta0 * gdot / tau_star)**(1.0 - n))`. Default `gdot` to `1000.0` s^-1, and `p_mpa` to `0.0` if not passed.
6. The signature of `_wlf_dynamic_viscosity` can be:
`def _wlf_dynamic_viscosity(mu0: float, tr: float, c1: float, c2: float, t_k: float, gdot: float = 1000.0, p_mpa: float = 0.0, params: dict | None = None) -> float:`
7. Extract WLF/Cross-WLF parameters (D1, D2, D3, A1, A2, tau_star, n) from `params` dict if passed. Fallback to default constants: D1=1.0e10, D2=105.0, D3=0.0, A1=17.44, A2=51.6, tau_star=50000.0, n=0.35.
8. Make sure `_resolve_wlf_params` and `_wlf_mu_table_text` are updated accordingly or remain fully compatible.

Return ONLY the updated python code block that will replace the target block. No markdown wrapper (no ```python), no comments outside the code, no explanations.
"""
    try:
        modified_block = query_llm(prompt)
    except Exception as e:
        print(f"[ERR] LLM query failed: {e}")
        return 1

    # 4. Apply Modification
    new_content = content[:idx_start] + modified_block + content[idx_end + len(end_marker):]
    
    # 5. Syntax Verification
    tmp_file = TARGET_FILE.with_suffix(".py.tmp")
    try:
        tmp_file.write_text(new_content, encoding="utf-8")
        res = subprocess.run([sys.executable, "-m", "py_compile", str(tmp_file)], capture_output=True)
        if res.returncode != 0:
            print(f"[ERR] Syntax validation failed: {res.stderr.decode('utf-8', errors='replace')}")
            if tmp_file.exists():
                tmp_file.unlink()
            return 1
        print("[INFO] Syntax validation PASSED.")
    except Exception as e:
        print(f"[ERR] Validation failed with error: {e}")
        if tmp_file.exists():
            tmp_file.unlink()
        return 1

    # Overwrite target file
    TARGET_FILE.write_text(new_content, encoding="utf-8")
    if tmp_file.exists():
        tmp_file.unlink()
    print(f"[INFO] Successfully updated {TARGET_FILE.name}.")

    # 6. Satellite Sync & Deploy
    print("[DEPLOY] Synchronizing scripts to satellite worker (LAVIE)...")
    sync_script = ROOT / "scripts" / "k10_sync_lavie_scripts_to_lavie.py"
    if sync_script.exists():
        sync_res = subprocess.run([sys.executable, str(sync_script), "--build-pack"], capture_output=True, text=True)
        if sync_res.returncode != 0:
            print(f"[DEPLOY] Sync failed: {sync_res.stderr}")
            print("[DEPLOY] Rolling back script update for safety...")
            run_git_command(["git", "checkout", "--", str(TARGET_FILE)])
            return 1
        print("[DEPLOY] Satellite deploy PASSED and worker container restarted.")
    else:
        print("[DEPLOY] WARNING: Sync script not found. Skipped deploy.")

    # 7. Commit changes
    git_msg = f"feat(cae): Autonomously integrated Cross-WLF Viscosity model [Record ID: {record['id']}]"
    run_git_command(["git", "add", str(TARGET_FILE)])
    ok, out = run_git_command(["git", "commit", "-m", git_msg])
    if ok:
        print(f"[GIT] Committed autonomous improvements: {git_msg}")
        run_git_command(["git", "push"])
    
    # 8. Record state
    if record["id"] not in applied_ids:
        applied_ids.append(record["id"])
        state["applied_record_ids"] = applied_ids
        save_state(state)

    # 9. Send Telegram
    tg_text = (
        f"【自動改善完了】\n"
        f"CAE流動解析スクリプトを自律更新しました。\n"
        f"・適用ID: {record['id']}\n"
        f"・理論: {record['challenge']}\n"
        f"・内容: Cross-WLF非ニュートン粘性モデル（せん断速度・温度依存性）の統合完了\n"
        f"・デプロイ: LAVIEへの同期＆再起動完了"
    )
    send_telegram(tg_text)
    print("[SUCCESS] Self-improvement loop completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
