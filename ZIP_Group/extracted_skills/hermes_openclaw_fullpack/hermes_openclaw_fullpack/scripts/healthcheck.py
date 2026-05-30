import requests

url = "http://localhost:8791/health"
print(requests.get(url, timeout=5).json())
