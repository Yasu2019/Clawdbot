import argparse
import subprocess

import _bootstrap
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.utils import compact_timestamp


def run_command(args: list[str]) -> str:
    result = subprocess.run(args, cwd=_bootstrap.ROOT, capture_output=True, text=True, check=False)
    return (result.stdout + result.stderr).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--purpose", default="定期技術監査")
    args = parser.parse_args()
    config = AppConfig()
    db = Database(config.paths.database)
    output = config.paths.reports / f"audit_packet_{compact_timestamp()}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    tests = run_command(["python", "-m", "pytest", "-q"])
    git_diff = run_command(["git", "diff", "--stat"]) if (_bootstrap.ROOT / ".git").exists() else "Git未初期化"
    metrics = db.query_all("SELECT product_id,decision,COUNT(*) AS count FROM inspections GROUP BY product_id,decision")
    text = (
        "# Fable5監査パケット\n\n"
        f"## 目的\n{args.purpose}\n\n"
        f"## 変更統計\n```\n{git_diff}\n```\n\n"
        f"## テスト\n```\n{tests}\n```\n\n"
        f"## 稼働集計\n```\n{metrics}\n```\n\n"
        "## 判断依頼\n"
        "- 要求漏れ\n- 見逃し/過検出リスク\n- 寸法測定の妥当性\n"
        "- 学習・昇格の安全性\n- 本番候補可否\n"
    )
    output.write_text(text, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
