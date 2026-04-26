
import requests
import json

def debug_login():
    login_url = "http://127.0.0.1:5679/rest/login"
    email = "y.suzuki.hk@gmail.com"
    password = "Foxconnjpn75"
    
    resp = requests.post(login_url, json={"emailOrLdapLoginId": email, "password": password}, headers={"browser-id": "clawstack-patrol"}, timeout=8)
    print(f"Login Status: {resp.status_code}")
    print(f"Cookies: {resp.cookies.get_dict()}")
    
    if resp.ok:
        cookie = resp.cookies.get("n8n-auth")
        # Try /rest/workflows
        workflows_url = "http://127.0.0.1:5679/rest/workflows"
        resp2 = requests.get(workflows_url, cookies={"n8n-auth": cookie}, headers={"browser-id": "clawstack-patrol"}, timeout=8)
        print(f"Workflows (/rest/): {resp2.status_code}")
        # print(f"Body: {resp2.text[:100]}")

if __name__ == "__main__":
    debug_login()
