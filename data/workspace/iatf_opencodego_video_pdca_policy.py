from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
CONFIG = ROOT / "data/state/openclaw.json"
STATUS = ROOT / "data/workspace/iatf_opencodego_video_pdca_policy_status.json"


POLICY = {
    "workflow": "OpenCodeGo generates and self-checks IATF video candidates; Codex manages local files and final gate routing.",
    "user_consent": "OpenCodeGo may run without per-call consent unless usage becomes unusually high.",
    "cost_reporting": "Report successful calls, token usage, and JPY estimate to Telegram after each PDCA batch.",
    "cost_rule": "Do not invent yen cost. Use provider/LiteLLM cost when available; otherwise report tokens and cost_unknown.",
    "final_gate": "Only OpenCodeGo self-approved candidates are escalated to Codex/Gemini/Claude final QA.",
    "stop_file": str(ROOT / "data/workspace/iatf_video_pdca_stop.flag"),
    "default_limits": {
        "one_cut_at_a_time": True,
        "diagnostic_frames_before_mp4": 7,
        "max_opencodego_calls_per_batch": 6,
        "max_success_cost_jpy_before_pause": 300,
    },
}


def send_telegram(text: str) -> str:
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        token = cfg["channels"]["telegram"]["botToken"]
        chat_ids = [str(x) for x in cfg["channels"]["telegram"]["allowFrom"]]
        chat_id = "8173025084" if "8173025084" in chat_ids else chat_ids[0]
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as res:
            return f"sent:{res.status}"
    except Exception as exc:
        return f"failed:{exc}"


def write_status(payload: dict) -> None:
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    # Current session summary: OpenCodeGo was attempted for CUT007/CUT009, but
    # LiteLLM/OpenCodeGo returned connection/500 errors before any successful use.
    usage = {
        "batch": "iatf_video_pdca_policy_activation_20260502",
        "opencodego_successful_calls": 0,
        "opencodego_failed_attempts": 2,
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_jpy": 0,
        "cost_note": "No successful OpenCodeGo response in this batch; cost treated as 0 JPY.",
    }
    telegram_text = (
        "IATF動画PDCAをOpenCodeGo主担当方式に切替えました。\n"
        "今回のOpenCodeGo成功API使用: 0回、推定費用: 0円。"
    )
    telegram = send_telegram(telegram_text)
    write_status({"policy": POLICY, "usage": usage, "telegram": telegram})
    print(json.dumps({"ok": True, "usage": usage, "telegram": telegram}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
