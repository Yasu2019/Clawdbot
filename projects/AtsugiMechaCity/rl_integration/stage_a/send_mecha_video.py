# -*- coding: utf-8 -*-
"""Send a mecha video to Telegram — ONLY after a human-or-Claude visual check.

The user has repeatedly received FAILED / false-success videos on Telegram (an
outbox message literally named ..._cae_false_success.json exists). This sender
therefore REFUSES to run unless --i-visually-checked is passed, which the caller
must only supply after actually inspecting the frames and confirming the robot is
upright, performing the intended motion, limbs connected, no crawl/slide/tumble.

  python send_mecha_video.py --video walk.mp4 --caption "flat walk (verified)" \
      --i-visually-checked
"""
import argparse, json, mimetypes, os, sys, urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8173025084")


def send_video(path, caption):
    boundary = "----mechaBoundary7bd3"
    with open(path, "rb") as f:
        data = f.read()
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{CHAT_ID}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode())
    parts.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"video\"; "
                  f"filename=\"{os.path.basename(path)}\"\r\n"
                  f"Content-Type: {mimetypes.guess_type(path)[0] or 'video/mp4'}\r\n\r\n").encode())
    parts.append(data)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendVideo", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.loads(r.read().decode())
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--caption", default="mecha")
    ap.add_argument("--i-visually-checked", action="store_true",
                    help="REQUIRED. Confirms the caller inspected the frames and the "
                         "robot is upright / doing the intended motion / no defect.")
    args = ap.parse_args()
    if not args.i_visually_checked:
        print("REFUSED: --i-visually-checked not set. Inspect the frames first; "
              "never send an unverified mecha video (false-success incidents).")
        sys.exit(2)
    if not os.path.exists(args.video):
        print(f"REFUSED: video not found: {args.video}")
        sys.exit(2)
    res = send_video(args.video, args.caption)
    print("SENT OK" if res.get("ok") else f"SEND FAILED: {res}")


if __name__ == "__main__":
    main()
