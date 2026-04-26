
import urllib.request
import json

def test_login(email, password):
    login_url = "http://127.0.0.1:5679/rest/login"
    payload = {"emailOrLdapLoginId": email, "password": password}
    print(f"Testing Login: {email} / {password}")
    req = urllib.request.Request(
        login_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "browser-id": "clawstack001"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"SUCCESS Login: {resp.status}")
            return True
    except Exception as e:
        print(f"FAILED Login: {e}")
    return False

if __name__ == "__main__":
    test_login("admin@clawstack.local", "clawstack2026")
    test_login("admin@clawstack.local", "Foxconnjpn75")
    test_login("admin", "clawstack2026")
