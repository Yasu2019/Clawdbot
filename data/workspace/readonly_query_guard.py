import re
from dataclasses import dataclass

BLOCKED = [
    r"\bUPDATE\b", r"\bDELETE\b", r"\bINSERT\b", r"\bDROP\b", r"\bTRUNCATE\b",
    r"\bALTER\b", r"\bMERGE\b", r"\bCREATE\b", r"\bGRANT\b", r"\bREVOKE\b",
    r"\bEXEC\b", r"\bEXECUTE\b"
]
ALLOWED_START = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE | re.DOTALL)

@dataclass
class QueryCheckResult:
    ok: bool
    reason: str


def check_sql_readonly(sql: str) -> QueryCheckResult:
    if not ALLOWED_START.search(sql):
        return QueryCheckResult(False, "SQL must start with SELECT or WITH")
    for pat in BLOCKED:
        if re.search(pat, sql, re.IGNORECASE):
            return QueryCheckResult(False, f"Blocked SQL keyword detected: {pat}")
    if ";" in sql.strip().rstrip(";"):
        return QueryCheckResult(False, "Multiple statements are not allowed")
    return QueryCheckResult(True, "read-only query accepted")


if __name__ == "__main__":
    samples = [
        "SELECT * FROM Inspection WHERE ProductNo='NT3621-P50'",
        "UPDATE Inspection SET x=1",
        "WITH a AS (SELECT 1 AS x) SELECT * FROM a",
    ]
    for s in samples:
        print(s, "=>", check_sql_readonly(s))
