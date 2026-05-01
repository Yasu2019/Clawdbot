import requests, os
from pathlib import Path

LITELLM_URL = "http://localhost:4001"
LITELLM_KEY = os.getenv("LITELLM_MASTER_KEY", "local-dev-key")
OUTPUT_PATH = Path("d:/Clawdbot_Docker_20260125/data/workspace/blender_mode_design_deepseek.md")

PROMPT = (
    "IATFビデオファクトリーBlenderモード設計書の続き（セクション6〜9）を日本語・Markdownで出力してください。\n\n"
    "## 6. 字幕焼き込み方法\n"
    "BlenderテキストオブジェクトとFFmpegどちらが良いか（実用性・保守性・処理速度で比較）、推奨方法のコード例。\n\n"
    "## 7. フェードイン/アウト（シーン切り替え）\n"
    "Blender PythonでCompositorノードを使ったフェード実装コード。\n\n"
    "## 8. QAスクリプト統合\n"
    "レンダリング完了後にcinema_motion_qa.pyをsubprocessで自動実行し、"
    "ボーンジャンプ検出結果をJSONレポートとして保存するコード。\n\n"
    "## 9. 優先度と実装順序\n"
    "セクション1〜8の優先度・推奨実装順序・工数目安・効果・前提条件をテーブル形式で。"
)

headers = {
    "Authorization": f"Bearer {LITELLM_KEY}",
    "Content-Type": "application/json",
}
payload = {
    "model": "google/gemini-2.5-flash",
    "messages": [
        {"role": "system", "content": "あなたはBlender Python専門エンジニアです。コードスニペットを含む具体的な設計書を日本語で出力してください。"},
        {"role": "user", "content": PROMPT},
    ],
    "max_tokens": 5000,
    "temperature": 0.3,
}

resp = requests.post(f"{LITELLM_URL}/v1/chat/completions", headers=headers, json=payload, timeout=300)
resp.raise_for_status()
content = resp.json()["choices"][0]["message"]["content"]
print(f"受信完了 ({len(content)}文字)", flush=True)

with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
    f.write("\n\n---\n\n" + content)
print("追記完了:", OUTPUT_PATH)
