from pathlib import Path
import yaml

class QueryRouter:
    def __init__(self, rule_path="config/routing_rules.yaml"):
        path = Path(rule_path)
        if path.exists():
            self.rules = yaml.safe_load(path.read_text(encoding="utf-8"))["rules"]
        else:
            self.rules = []

    def route(self, query: str) -> str:
        for rule in self.rules:
            for kw in rule.get("keyword", []):
                if kw.lower() in query.lower():
                    return rule.get("engine", "light")
        return "light"
