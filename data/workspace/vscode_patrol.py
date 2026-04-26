"""
VS Code拡張エラー パトロールスクリプト
対象: CSV / YAML(GitHub Actions, docker-compose) / JSON
実行: 毎日自動 (CronCreate経由)
通知: Telegram
"""
import csv
import json
import os
import sys
import yaml
import requests
from pathlib import Path

# Windows端末のUTF-8対応
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime
from collections import defaultdict

ROOT = Path("D:/Clawdbot_Docker_20260125")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SCAN_TARGETS = {
    "csv":  [
        ROOT / "iatf_system/db/record",
        ROOT / "data/workspace",
    ],
    "yaml": [
        ROOT / ".github/workflows",
        ROOT,  # docker-compose.yml など
    ],
    "json": [
        ROOT / "data/workspace",
    ],
}

# カラム数・重複チェックを除外するCSVパターン（構造が混在する正常ファイル）
CSV_SKIP_COLUMN_CHECK = [
    "testmondai", "mondai", "cleaned", "mojibake",
    "chatGPT", "summary", "サマリー",
]
# 1列目重複チェックを実施するパターン（IDが一意であるべきファイルのみ）
CSV_APPLY_DUPLICATE_CHECK = [
    "login", "user", "account", "member", "employee",
]

issues   = []   # (severity, file, line, message)
fixed    = []   # (file, what)


# ── CSV 検証 & 自動修復 ────────────────────────────────────────────────
def check_csv(path: Path):
    try:
        raw = path.read_bytes()
        enc = "utf-8-sig" if raw[:3] == b"\xef\xbb\xbf" else "utf-8"
        text = raw.decode(enc, errors="replace")
    except Exception as e:
        issues.append(("ERROR", str(path), 0, f"読み込み失敗: {e}"))
        return

    lines = text.splitlines()

    # 末尾空行の自動修復
    stripped = [l for l in lines]
    while stripped and stripped[-1].strip() == "":
        stripped.pop()
    if len(stripped) < len(lines):
        path.write_text("\n".join(stripped) + "\n", encoding=enc)
        fixed.append((str(path), f"末尾空行 {len(lines)-len(stripped)}行 削除"))
        lines = stripped

    # カラム数チェック（除外パターン対象外のみ）
    skip_col = any(pat in path.name for pat in CSV_SKIP_COLUMN_CHECK)
    if not skip_col:
        reader = csv.reader(lines)
        col_counts = defaultdict(list)
        for i, row in enumerate(reader, 1):
            if row:  # 空行除外
                col_counts[len(row)].append(i)
        if len(col_counts) > 1:
            majority = max(col_counts, key=lambda k: len(col_counts[k]))
            if majority > 0:
                for cnt, rows in col_counts.items():
                    if cnt != majority:
                        issues.append(("WARN", str(path), rows[0],
                                       f"カラム数不一致: {cnt}列 (多数派={majority}列) 行={rows[:5]}"))

    # 1列目重複チェック（ログイン・マスタ系ファイルのみ）
    apply_dup = any(pat in path.name.lower() for pat in CSV_APPLY_DUPLICATE_CHECK)
    if apply_dup:
        reader2 = csv.reader(lines)
        seen = defaultdict(list)
        for i, row in enumerate(reader2, 1):
            if row:
                seen[row[0]].append(i)
        for val, rows in seen.items():
            if len(rows) > 1 and val.strip():
                issues.append(("WARN", str(path), rows[0],
                               f"1列目重複: '{val}' が行 {rows} に存在"))

    # メール列の重複チェック（2列目がメールっぽい場合）
    reader3 = csv.reader(lines)
    emails = defaultdict(list)
    for i, row in enumerate(reader3, 1):
        if len(row) >= 2 and "@" in row[1]:
            emails[row[1].strip()].append(i)
    for email, rows in emails.items():
        if len(rows) > 1:
            issues.append(("WARN", str(path), rows[0],
                           f"メール重複: '{email}' が行 {rows} に存在"))


# ── YAML 検証 ────────────────────────────────────────────────────────
def check_yaml(path: Path):
    try:
        yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        line = mark.line + 1 if mark else 0
        issues.append(("ERROR", str(path), line, f"YAML構文エラー: {e.problem if hasattr(e,'problem') else e}"))
    except Exception as e:
        issues.append(("ERROR", str(path), 0, f"読み込み失敗: {e}"))


# ── JSON 検証 ────────────────────────────────────────────────────────
def check_json(path: Path):
    try:
        raw = path.read_bytes()
        # UTF-8 BOM自動修復
        if raw.startswith(b"\xef\xbb\xbf"):
            path.write_bytes(raw[3:])
            fixed.append((str(path), "UTF-8 BOM 除去"))
            raw = raw[3:]
        json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        issues.append(("ERROR", str(path), e.lineno, f"JSON構文エラー: {e.msg}"))
    except Exception as e:
        issues.append(("ERROR", str(path), 0, f"読み込み失敗: {e}"))


# ── スキャン実行 ──────────────────────────────────────────────────────
def scan():
    for base in SCAN_TARGETS["csv"]:
        for p in Path(base).rglob("*.csv") if Path(base).is_dir() else []:
            check_csv(p)

    for base in SCAN_TARGETS["yaml"]:
        bp = Path(base)
        if bp.is_dir():
            for p in bp.glob("*.yml"):
                check_yaml(p)
            for p in bp.glob("*.yaml"):
                check_yaml(p)
        elif bp.exists():
            check_yaml(bp)

    for base in SCAN_TARGETS["json"]:
        for p in Path(base).glob("*.json") if Path(base).is_dir() else []:
            check_json(p)


# ── Telegram 通知 ────────────────────────────────────────────────────
def notify(token: str, chat_id: str, text: str):
    if not token or not chat_id:
        print(text)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"Telegram送信失敗: {e}")


# ── メイン ────────────────────────────────────────────────────────────
def main():
    scan()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines_out = [f"🔍 <b>VS Code パトロール結果</b> {now}"]

    if fixed:
        lines_out.append(f"\n✅ <b>自動修復 {len(fixed)}件</b>")
        for f_path, what in fixed:
            short = f_path.replace(str(ROOT), "").lstrip("/\\")
            lines_out.append(f"  • {short}: {what}")

    errors = [i for i in issues if i[0] == "ERROR"]
    warns  = [i for i in issues if i[0] == "WARN"]

    if errors:
        lines_out.append(f"\n🚨 <b>エラー {len(errors)}件（要対応）</b>")
        for _, path, line, msg in errors[:10]:
            short = path.replace(str(ROOT), "").lstrip("/\\")
            lines_out.append(f"  • {short}:{line} {msg}")

    if warns:
        lines_out.append(f"\n⚠️ <b>警告 {len(warns)}件</b>")
        for _, path, line, msg in warns[:10]:
            short = path.replace(str(ROOT), "").lstrip("/\\")
            lines_out.append(f"  • {short}:{line} {msg}")

    if not errors and not warns and not fixed:
        lines_out.append("\n✅ 問題なし")

    msg = "\n".join(lines_out)
    notify(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

    # 結果をDBに記録 (docker exec経由でpsql呼び出し)
    try:
        import subprocess, json as _json
        detail = _json.dumps({"issues": issues[:50], "fixed": fixed},
                             ensure_ascii=False).replace("'", "''")
        sql = (
            "CREATE TABLE IF NOT EXISTS vscode_patrol_log ("
            "id SERIAL PRIMARY KEY, run_at TIMESTAMP DEFAULT NOW(), "
            "errors INT, warnings INT, fixed INT, detail JSONB);"
            f"INSERT INTO vscode_patrol_log (errors,warnings,fixed,detail) "
            f"VALUES ({len(errors)},{len(warns)},{len(fixed)},'{detail}');"
        )
        subprocess.run(
            ["docker", "exec", "clawstack-unified-postgres-1",
             "psql", "-U", "postgres", "-d", "sim_trials", "-c", sql],
            capture_output=True, timeout=10
        )
    except Exception as e:
        print(f"DB記録失敗: {e}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
