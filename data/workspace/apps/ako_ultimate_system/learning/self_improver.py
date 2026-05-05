from pathlib import Path

class SelfImprover:
    def __init__(self, failure_path="failures.log"):
        self.failure_path = Path(failure_path)
    def learn(self):
        if not self.failure_path.exists():
            return
        failures = self.failure_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(failures) >= 10:
            Path("improvement_suggestions.md").write_text(
                "# Improvement Suggestions\n\n- 失敗ログが10件以上です。routing_rules.yaml と根拠検証ルールを見直してください。\n",
                encoding="utf-8"
            )
