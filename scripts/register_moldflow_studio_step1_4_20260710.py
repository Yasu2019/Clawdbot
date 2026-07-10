# -*- coding: utf-8 -*-
"""2026-07-10セッション(Moldflow Studio STEP1-4 + T055)のTurso growth_records登録。

ホスト実行: python scripts/register_moldflow_studio_step1_4_20260710.py
必要env: TURSO_DATABASE_URL / TURSO_AUTH_TOKEN (無ければskip応答・冪等)
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RECORDS = [
    {
        "domain": "MOLDFLOW_STUDIO",
        "challenge": "moldflow_cae_studio STEP1-4: baseline commit / cgi removal / maturity+golden panels / Gate Advisor",
        "know_how": (
            "STEP1: ChatGPT改造(solver-landscape/learned-params/readiness)含む未追跡アプリをベースラインcommit。"
            "STEP2: import cgi(Py3.13削除)→自前_parse_multipart(512MB上限・応答スキーマ不変)。"
            "STEP3: /api/maturity(26h鮮度)+/api/golden-error-trend(壊れ行スキップ)。maturity_latest.json 7/8から更新停止を発見。"
            "STEP4: Gate Advisor=7組合せ決定論スコア(最大流動長/L/t限界/ウェルド/バランスCV)。"
            "充填不成立候補は常に下位(テストが順位欠陥を暴いた)。平板近似・L/t未校正=L3級。テスト計22件PASS"
        ),
        "artifact": "docs/handover/MOLDFLOW_STUDIO_REFACTOR_STEP4_20260710.md",
    },
    {
        "domain": "INFRA_GIT",
        "challenge": "T055: Coworkマウント経由のgit/バッチ3重罠(lockゴースト/index破損/プロセス毎内容不整合)",
        "know_how": (
            "①GIT_INDEX_FILE=/tmp方式でindex.lock非依存commit ②rm .git/index→git resetで再構築 "
            "③git hash-object -w + update-index --cacheinfoでFS迂回 ④デーモン再起動はkill-by-port方式 "
            "⑤実行中バッチ上書き禁止。マウント経由gitは信用しない"
        ),
        "artifact": ".brv/context-tree/t055-cowork-mount-git-traps-20260710.md",
    },
]


def sync_turso(domain: str, challenge: str, know_how: str, artifact: str) -> str:
    try:
        import libsql_client
    except ImportError:
        return "skip_no_libsql_client"
    url = os.environ.get("TURSO_DATABASE_URL", "").strip()
    token = os.environ.get("TURSO_AUTH_TOKEN", "").strip()
    if not url or not token:
        return "skip_no_turso_credentials"
    try:
        client = libsql_client.create_client_sync(url=url, auth_token=token)
        exists = client.execute(
            "SELECT COUNT(*) FROM growth_records WHERE domain = ? AND challenge = ?",
            [domain, challenge],
        )
        if exists.rows and int(exists.rows[0][0]) > 0:
            client.close()
            return "skip_already_registered"
        client.execute(
            "INSERT INTO growth_records (domain, challenge, status, know_how, artifact_path) VALUES (?, ?, ?, ?, ?)",
            [domain, challenge, "LESSON_LEARNED", know_how[:8000], artifact],
        )
        client.close()
        return "ok"
    except Exception as exc:
        return f"error:{exc}"[:200]


def main() -> int:
    for r in RECORDS:
        status = sync_turso(r["domain"], r["challenge"], r["know_how"], r["artifact"])
        print(f"[turso] {r['domain']}: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
