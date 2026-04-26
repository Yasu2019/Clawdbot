
import urllib.request
import json
import os

url = "http://127.0.0.1:5679/api/v1/workflows?limit=1"
api_key = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"

def test_api_key(key):
    print(f"Testing API key: {key[:15]}...")
    req = urllib.request.Request(url, headers={"X-N8N-API-KEY": key})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"SUCCESS (X-N8N-API-KEY): {resp.status}")
            return True
    except Exception as e:
        print(f"FAILED (X-N8N-API-KEY): {e}")
    
    req = urllib.request.Request(url, headers={"N8N-API-KEY": key})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"SUCCESS (N8N-API-KEY): {resp.status}")
            return True
    except Exception as e:
        print(f"FAILED (N8N-API-KEY): {e}")
    return False

def test_login():
    login_url = "http://127.0.0.1:5679/rest/login"
    payload = {"emailOrLdapLoginId": "y.suzuki.hk@gmail.com", "password": "Foxconnjpn75"}
    print(f"Testing Login: {payload['emailOrLdapLoginId']}")
    req = urllib.request.Request(
        login_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "browser-id": "clawstack001"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"SUCCESS Login: {resp.status}")
            cookies = resp.headers.get_all("Set-Cookie")
            print(f"Cookies: {cookies}")
            return True
    except Exception as e:
        print(f"FAILED Login: {e}")
        if hasattr(e, 'read'):
            print(f"Error Body: {e.read().decode()}")
    return False

if __name__ == "__main__":
    test_api_key(api_key)
    print("-" * 20)
    test_login()
