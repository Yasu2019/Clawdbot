"""台本生成 — Kimi K2.6 (256K ctx) 優先、Gemini 2.5 Flash フォールバック。
PDF全文を省略なく読み込み、7キャラ対話台本JSONを生成する。"""
import json, requests, os
from pathlib import Path

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4001")
LITELLM_KEY = os.getenv("LITELLM_MASTER_KEY", "local-dev-key")

# モデル優先順位 (OpenCode GO API接続確認後に kimi-k2.6 を最優先に)
SCRIPT_MODELS = [
    "opencode-go/kimi-k2.6",
    "google/gemini-2.5-flash",
    "local_fast",
]

CHARACTERS = {
    "bulma":   {"name": "ブルマ",   "role": "MC・司会",          "voicevox_id": 2},
    "goku":    {"name": "悟空",     "role": "内部監査員（質問）",  "voicevox_id": 8},
    "gohan":   {"name": "御飯",     "role": "被監査者（回答）",    "voicevox_id": 3},
    "android17":{"name": "17号",   "role": "不適合・問題点指摘",  "voicevox_id": 9},
    "android18":{"name": "18号",   "role": "改善対策・是正処置",  "voicevox_id": 10},
    "roshi":   {"name": "亀仙人",   "role": "クローズまとめ",      "voicevox_id": 11},
    "trunks":  {"name": "トランクス","role": "追加被監査者",        "voicevox_id": 7},
}

SYSTEM_PROMPT = """あなたはIATF 16949内部監査教育動画の台本作家です。
以下のキャラクターが登場します：
- ブルマ（MC・司会）
- 悟空（内部監査員、質問役）
- 御飯（被監査者、回答役）
- 17号（不適合・問題点の指摘役）
- 18号（改善対策・是正処置の提示役）
- 亀仙人（クローズミーティングのまとめ役）
- トランクス（追加の被監査者・観察者）

【絶対ルール】
1. 提供されたPDFの内容を一切省略せず、全てのポイントを台本に盛り込む
2. 各シーンの会話は自然な対話形式にする
3. 専門用語はキャラクターが解説しながら進める
4. 出力は必ず指定のJSON形式のみ（他のテキスト不要）"""

SCENE_STRUCTURE = [
    ("opening",       "オープニング",         ["bulma"]),
    ("requirements",  "要求事項の全体説明",   ["bulma", "roshi"]),
    ("site_audit",    "現場監査（対話）",      ["goku", "gohan", "trunks"]),
    ("findings",      "問題点・不適合の指摘", ["android17", "android18"]),
    ("close_meeting", "クローズミーティング", ["roshi", "bulma"]),
    ("improvement",   "改善対策",             ["gohan", "trunks", "android18"]),
    ("closing",       "エンディング",         ["bulma"]),
]


def _call_llm(model: str, messages: list, max_tokens: int = 8000) -> str | None:
    try:
        resp = requests.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  [{model}] failed: {e}")
        return None


def generate_script(pdf_text: str, clause: str, topic: str) -> dict:
    scene_list = "\n".join(
        f"{i+1}. {s[1]} (登場: {', '.join(CHARACTERS[c]['name'] for c in s[2])})"
        for i, s in enumerate(SCENE_STRUCTURE)
    )

    user_msg = f"""以下はIATF 16949 箇条{clause}「{topic}」の内部監査資料の全文です。
この内容を省略なく使用して、7場面の教育動画台本をJSONで生成してください。

【場面構成】
{scene_list}

【出力JSON形式】
{{
  "clause": "{clause}",
  "topic": "{topic}",
  "scenes": [
    {{
      "scene_id": "opening",
      "scene_name": "オープニング",
      "duration_sec": 30,
      "lines": [
        {{
          "character": "bulma",
          "text": "セリフテキスト",
          "emotion": "normal|happy|serious|explain",
          "pose": "neutral|point|bow|arms_crossed|nod",
          "duration_sec": 5
        }}
      ]
    }}
  ],
  "total_duration_sec": 600
}}

【PDF全文】
{pdf_text}
"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    for model in SCRIPT_MODELS:
        print(f"  Trying model: {model}")
        raw = _call_llm(model, messages)
        if not raw:
            continue
        # JSON抽出
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            script = json.loads(raw)
            script["model_used"] = model
            return script
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            continue

    raise RuntimeError("全モデルで台本生成失敗")


if __name__ == "__main__":
    from pdf_extractor import extract_pdf, list_audit_pdfs
    pdfs = list_audit_pdfs()
    text = extract_pdf(pdfs[0])
    print(f"PDF chars: {len(text)}")
    script = generate_script(text, "8.5.4", "梱包工程")
    print(json.dumps(script, ensure_ascii=False, indent=2)[:1000])
