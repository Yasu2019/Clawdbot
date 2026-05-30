import requests

payload = {
    "category": "IATF16949",
    "title": "プロセスオーナー設定",
    "body": "プロセスオーナーは役職名ではなく、対象プロセスの有効性・KPI・課題・改善を把握し管理できる責任権限が重要。",
    "source": "manual_sample"
}

r = requests.post("http://127.0.0.1:28791/memory/add", json=payload, timeout=10)
print(r.json())
