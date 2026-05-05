from pathlib import Path
from datetime import datetime

class FailureLogger:
    def __init__(self, path="failures.log"):
        self.path = Path(path)
    def log(self, query: str, result: str, route: str):
        if "⚠" in result:
            self.path.open("a", encoding="utf-8").write(
                f"{datetime.now().isoformat()}\t{route}\t{query}\t{result[:200]}\n"
            )
