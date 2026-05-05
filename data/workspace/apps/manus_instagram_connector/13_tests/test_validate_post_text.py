from pathlib import Path
import subprocess
import sys
import tempfile

def test_blocked_expression_rejected():
    script = Path(__file__).resolve().parents[1] / "10_scripts" / "validate_post_text.py"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "post.txt"
        p.write_text("誰でも簡単に絶対に稼げる方法です", encoding="utf-8")
        result = subprocess.run([sys.executable, str(script), str(p)], capture_output=True, text=True)
        assert result.returncode == 1
        assert "rejected" in result.stdout

def test_safe_text_needs_human_approval_or_ok():
    script = Path(__file__).resolve().parents[1] / "10_scripts" / "validate_post_text.py"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "post.txt"
        p.write_text("品質保証の現場で、AIを安全に使うための確認ポイントを紹介します。", encoding="utf-8")
        result = subprocess.run([sys.executable, str(script), str(p)], capture_output=True, text=True)
        assert result.returncode == 0
