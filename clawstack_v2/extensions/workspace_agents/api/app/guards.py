import re

FORBIDDEN_SQL = ["UPDATE", "DELETE", "INSERT", "MERGE", "DROP", "ALTER", "TRUNCATE", "EXEC", "CREATE"]

def assert_read_only_sql(sql: str) -> None:
    normalized = re.sub(r"\s+", " ", sql.upper()).strip()
    if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
        raise ValueError("Only SELECT/WITH queries are allowed")
    for keyword in FORBIDDEN_SQL:
        if re.search(rf"\b{keyword}\b", normalized):
            raise ValueError(f"Forbidden SQL keyword detected: {keyword}")

def require_hitl(action: str, approved: bool) -> None:
    if not approved:
        raise PermissionError(f"HITL approval required before action: {action}")
