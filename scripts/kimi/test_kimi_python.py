import os
from openai import OpenAI

api_key = os.environ.get("MOONSHOT_API_KEY")
base_url = os.environ.get("KIMI_BASE_URL", "https://api.moonshot.ai/v1")
model = os.environ.get("KIMI_MODEL_PRIMARY", "kimi-k2.6")

if not api_key:
    raise SystemExit("MOONSHOT_API_KEY is not set")

client = OpenAI(api_key=api_key, base_url=base_url)

resp = client.chat.completions.create(
    model=model,
    temperature=0.6,
    messages=[
        {"role": "system", "content": "You are a precise manufacturing QA assistant. Answer in Japanese with structured headings."},
        {"role": "user", "content": "IATF監査の観点で、工程監査チェックリストの重要点を5項目で出してください。"},
    ],
)

print(resp.choices[0].message.content)
