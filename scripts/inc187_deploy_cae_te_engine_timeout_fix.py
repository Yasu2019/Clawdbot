#!/usr/bin/env python3
"""Deploy cae_te_engine.py OpenFOAM timeout fix to LAVIE /repo/scripts with backup."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import k10_satellite_dispatch as d  # noqa: E402
import k10_sync_cae_experiments_to_lavie as sync_base  # noqa: E402

SRC = ROOT / "scripts" / "cae_te_engine.py"
REMOTE = "/repo/scripts/cae_te_engine.py"
BACKUP_SUFFIX = ".inc187_pre_r19_20260805"
SERVE_PORT = 5691


def main() -> int:
    data = SRC.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    k10_ip = sync_base.detect_k10_tailscale_ip("")
    with tempfile.TemporaryDirectory(prefix="inc187_engine_") as tmp:
        tmp_path = Path(tmp)
        fname = "cae_te_engine.py"
        local_copy = tmp_path / fname
        shutil.copy2(SRC, local_copy)
        server, _thread = sync_base.serve_zip(local_copy, SERVE_PORT)
        url = f"http://{k10_ip}:{SERVE_PORT}/{fname}"
        cmd = f"""
set -e
TARGET='{REMOTE}'
BACKUP="${{TARGET}}{BACKUP_SUFFIX}"
EXPECTED='{digest}'
URL='{url}'
if [ -f "$TARGET" ] && [ ! -f "$BACKUP" ]; then
  cp -f "$TARGET" "$BACKUP"
fi
python3 - <<'PY'
from urllib.request import urlretrieve
urlretrieve("{url}", "{REMOTE}.tmp")
print("DOWNLOAD_OK")
PY
ACTUAL=$(sha256sum "${{TARGET}}.tmp" | awk '{{print $1}}')
if [ "$ACTUAL" != "$EXPECTED" ]; then
  echo "HASH_MISMATCH expected=$EXPECTED actual=$ACTUAL"
  rm -f "${{TARGET}}.tmp"
  exit 2
fi
mv -f "${{TARGET}}.tmp" "$TARGET"
echo DEPLOY_OK path=$TARGET sha256=$ACTUAL backup=$BACKUP url=$URL
ls -la "$TARGET" "$BACKUP" 2>/dev/null || true
grep -n "timeout -k 30" "$TARGET" | head -n 8
"""
        try:
            token = d.load_token()
            body = sync_base.dispatch_shell("lavie", cmd, 120, token)
        finally:
            server.shutdown()
    out = body.get("stdout") or body.get("stdout_tail") or ""
    err = body.get("stderr") or body.get("stderr_tail") or body.get("error") or ""
    print(out[-4000:])
    if err:
        print("STDERR", str(err)[-2000:])
    print("status", body.get("status"), "exit", body.get("exit_code"))
    ok = body.get("status") == "ok" and "DEPLOY_OK" in out and digest in out
    print("RESULT:", "PASS" if ok else "FAIL", "local_sha", digest)
    out_path = ROOT / "data" / "state" / "lavie_mf_pipeline_monitor" / "inc187_r14_deploy.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "ok": ok,
                "local_sha256": digest,
                "remote_path": REMOTE,
                "backup_suffix": BACKUP_SUFFIX,
                "k10_ip": k10_ip,
                "worker_status": body.get("status"),
                "exit_code": body.get("exit_code"),
                "stdout_tail": out[-2000:],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
