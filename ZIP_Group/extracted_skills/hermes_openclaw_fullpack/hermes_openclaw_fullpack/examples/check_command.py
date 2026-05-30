import requests

for command in [
    "python scripts/analyze.py",
    "git reset --hard HEAD",
    "docker compose down",
    "rm -rf /"
]:
    r = requests.post(
        "http://127.0.0.1:28791/guard/check-command",
        json={"command": command, "reason": "sample"},
        timeout=10,
    )
    print(command, "=>", r.json())
