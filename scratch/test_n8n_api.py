import requests

api_key = 'n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9'
url = 'http://localhost:5679/api/v1/workflows'

headers = {
    'X-N8N-API-KEY': api_key
}

try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("Workflows from API:")
        for wf in data.get('data', []):
            print(f"ID: {wf['id']}, Name: {wf['name']}, Active: {wf['active']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
