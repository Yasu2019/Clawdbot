import os
import json
from pathlib import Path

from .surgical_security_guard import SurgicalSecurityGuard

# V10 Intelligence Data
PSYCHOLOGY_TRIGGERS = {
    "1": "バーナム効果: 自分ごと化 (例: 「〇〇で悩んでいませんか？」)",
    "2": "ハロー効果: 肩書で信頼 (例: 「現場で検証済」)",
    "3": "バンドワゴン: 人気で拡散 (例: 「多くの現場で使われている」)",
    "4": "カリギュラ: 禁止で興味 (例: 「注意：初心者向けではありません」)",
    "5": "吊り橋効果: 苦労→成功ストーリー",
    "6": "フォルスコンセンサス: 他人成功で信じる",
    "7": "スリーパー: 中身重視の継続評価",
    "8": "初頭効果: 1行目勝負 (フック)",
    "9": "新近効果: 最後重要 (好印象)",
    "10": "カクテルパーティー: 個別呼びかけ (例: 「製造業の方」)",
    "11": "ベビーフェイス: 親しみやすい表現",
    "12": "ツァイガルニック: 未完で引き (続きは...)",
    "13": "宣言効果: 明日やる/行動促進",
    "14": "エスカレーター: 反常識/予想外",
    "15": "リフレーミング: 言い換え (高い→投資)",
    "16": "テンションリダクション: ついで買い/追記",
    "17": "クーリッジ: 新しさ/最新版",
    "18": "暗黙強化: 間接権威",
    "19": "エピソード記憶: 共感ストーリー",
    "20": "両面提示: 信頼 (デメリット＋対策)"
}

PLATFORMS = ["X", "Instagram", "Threads", "note", "YouTube", "TikTok", "Qiita", "GitHub", "Blog"]

SAFETY_RULES = [
    "禁止：100%改善、必ず稼げる等の誇大表現",
    "必須：機密情報の除外（図面番号、顧客名など）",
    "必須：人間による最終確認"
]

MASTER_PROMPT_TEMPLATE = """
あなたは究極のSNS戦略家です。以下の「種データ」と「現在のトレンド」を元に、集客を最大化する投稿を生成してください。

【現在のトレンド】
{current_trend}

【種データ (実務知見)】
{seed_data}

【心理トリガー設定】
{selected_triggers}

【必須構造】
1. カリギュラ
2. バーナム
3. ハロー
4. 両面提示
5. リフレーミング

【媒体別ガイドライン】
- X/Threads: 短文、フック重視
- Instagram: 視覚的描写、ハッシュタグ
- Qiita: 技術的な正確性、コードやTips
- GitHub: READMEやIssue形式の技術共有
- Blog: 網羅的な解説、ストーリー形式

【安全性ルール】
{safety_rules}

出力は指定されたすべての媒体について行ってください。
"""

class BuzzV10Engine:
    def __init__(self):
        self.guard = SurgicalSecurityGuard()

    def generate_prompt(self, seed_data, trigger_indices=None, current_trend="特になし"):
        if trigger_indices is None:
            trigger_indices = ["1", "2", "3", "4", "5"]
        
        selected = [PSYCHOLOGY_TRIGGERS.get(i, "") for i in trigger_indices]
        trigger_text = "\n".join([t for t in selected if t])
        
        # Pre-scrub seed data just in case
        safe_seed = self.guard.scrub(seed_data)
        
        prompt = MASTER_PROMPT_TEMPLATE.format(
            current_trend=current_trend,
            seed_data=safe_seed,
            selected_triggers=trigger_text,
            safety_rules="\n".join(SAFETY_RULES)
        )
        return prompt

    def final_check(self, generated_content):
        """
        Final safety check before returning to UI.
        """
        return self.guard.scrub(generated_content)

if __name__ == "__main__":
    # Test execution
    engine = BuzzV10Engine()
    test_data = "Gmailから抽出：新しい金型の冷却効率が15%向上したが、最初は設計ミスで水漏れが発生した。"
    print(engine.generate_prompt(test_data))
