import requests
import json

email_data = {
    'from': 'test@example.com',
    'to': 'me@example.com',
    'date': '2026-03-05',
    'subject': '図面承認の依頼',
    'attachments': [],
    'body': 'ミツイ担当者です。金曜日までに図面の承認をお願いします。'
}

prompt = f"""あなたは製造・営業支援の専門アナリストです。以下のメールを解析し、依頼事項とステータスを日本語で抽出してください。

[Email情報]
差出人: {email_data['from']}
受取人: {email_data['to']}
日付: {email_data['date']}
件名: {email_data['subject']}
添付: なし

[本文]
{email_data['body']}

以下の JSON 形式でのみ出力してください：
{{"依頼事項": "string", "納期": "string", "回答": "string", "重要度": "string", "改善状況": "string", "要約": "string"}}"""

print("Prompt length:", len(prompt))
print("Calling Ollama...")
try:
    resp = requests.post('http://ollama:11434/api/generate', 
                         json={'model': 'deepseek-r1:7b', 'prompt': prompt, 'stream': False, 'format': 'json'}, 
                         timeout=60)
    print("Status:", resp.status_code)
    if resp.status_code == 200:
        print("Response JSON:", resp.json().get('response', ''))
    else:
        print("Error response:", resp.text)
except Exception as e:
    print("Error:", e)
