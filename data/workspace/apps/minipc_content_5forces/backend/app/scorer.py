from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .schemas import ContentIdea, ForceScore, EvaluationResult

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / "configs").exists():
    # Docker container fallback (/app/app/scorer.py -> /app)
    ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalize_text(*parts: str) -> str:
    return " ".join([p or "" for p in parts]).lower()


def contains_any(text: str, keywords: list[str]) -> list[str]:
    hits = []
    lower = text.lower()
    for kw in keywords:
        if kw.lower() in lower:
            hits.append(kw)
    return hits


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))


class ContentFiveForcesScorer:
    """MiniPC/Portal向けのコンテンツ採用判定器。

    外部APIを呼ばず、ローカルで簡易判定します。
    実運用ではここに検索結果、過去記事データ、閲覧数、販売数などを足す想定です。
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or CONFIG_DIR
        self.rules = load_yaml(self.config_dir / "scoring_rules.yaml")
        self.platform_rules = load_yaml(self.config_dir / "platform_rules.yaml")

    def evaluate(self, idea: ContentIdea) -> EvaluationResult:
        text = normalize_text(
            idea.title,
            idea.target_audience,
            idea.pain,
            idea.proof,
            idea.unique_angle,
            idea.preferred_platform,
        )

        domain_hits = contains_any(text, self.rules["domain_boost_keywords"])
        weak_hits = contains_any(text, self.rules["weak_keywords"])
        external_hits = contains_any(text, self.rules["external_dependency_keywords"])

        buyer_pain = self._score_buyer_pain(idea, domain_hits)
        user_moat = self._score_user_moat(idea, domain_hits, weak_hits)
        competition_weakness = self._score_competition_weakness(idea, weak_hits, domain_hits)
        substitute_resistance = self._score_substitute_resistance(idea, domain_hits, weak_hits)
        low_supplier_dependency = self._score_supplier_dependency(external_hits, idea)
        platform_fit = self._score_platform_fit(idea, domain_hits)
        production_feasibility = self._score_production_feasibility(idea)

        force_scores = [
            ForceScore(name="buyer_pain", score=buyer_pain, max_score=25, reason="読者・購入者の困りごとの強さ"),
            ForceScore(name="user_moat", score=user_moat, max_score=20, reason="鈴木様の実務経験で差別化できる度合い"),
            ForceScore(name="competition_weakness", score=competition_weakness, max_score=15, reason="競合が強すぎない、または専門性で避けられる度合い"),
            ForceScore(name="substitute_resistance", score=substitute_resistance, max_score=15, reason="無料情報や一般AI回答で代替されにくい度合い"),
            ForceScore(name="low_supplier_dependency", score=low_supplier_dependency, max_score=10, reason="外部API・素材・クラウド依存の低さ"),
            ForceScore(name="platform_fit", score=platform_fit, max_score=10, reason="媒体との相性"),
            ForceScore(name="production_feasibility", score=production_feasibility, max_score=5, reason="ミニパソコンで制作しやすい度合い"),
        ]

        total = sum(s.score for s in force_scores)
        decision = self._decision(total)
        platform = self._recommend_platform(idea, total, domain_hits)
        risks = self._risks(idea, weak_hits, external_hits, domain_hits)
        next_actions = self._next_actions(idea, total, platform, risks)
        outline = self._outline(idea, platform)
        notes = self._safe_publication_notes(idea)

        return EvaluationResult(
            title=idea.title,
            total_score=clamp(total),
            decision=decision,
            recommended_platform=platform,
            force_scores=force_scores,
            risks=risks,
            next_actions=next_actions,
            outline=outline,
            safe_publication_notes=notes,
            raw_features={
                "domain_hits": domain_hits,
                "weak_hits": weak_hits,
                "external_dependency_hits": external_hits,
                "text_length": len(text),
            },
        )

    def _score_buyer_pain(self, idea: ContentIdea, domain_hits: list[str]) -> int:
        score = 8
        if len(idea.pain) >= 10:
            score += 7
        if any(w in idea.pain for w in ["ミス", "工数", "時間", "属人", "監査", "不良", "損失", "自動"]):
            score += 6
        if domain_hits:
            score += 4
        return min(score, 25)

    def _score_user_moat(self, idea: ContentIdea, domain_hits: list[str], weak_hits: list[str]) -> int:
        score = 5
        if len(idea.proof) >= 10:
            score += 5
        if len(idea.unique_angle) >= 10:
            score += 4
        score += min(len(domain_hits), 5)
        if weak_hits:
            score -= min(len(weak_hits) * 2, 6)
        return clamp(score, 0, 20)

    def _score_competition_weakness(self, idea: ContentIdea, weak_hits: list[str], domain_hits: list[str]) -> int:
        score = 8
        if domain_hits:
            score += 5
        if weak_hits:
            score -= min(len(weak_hits) * 3, 9)
        if any(w in idea.title for w in ["誰でも", "簡単", "稼ぐ", "ニュース"]):
            score -= 4
        return clamp(score, 0, 15)

    def _score_substitute_resistance(self, idea: ContentIdea, domain_hits: list[str], weak_hits: list[str]) -> int:
        score = 7
        if any(w in normalize_text(idea.title, idea.pain, idea.unique_angle) for w in ["実装", "テンプレ", "コード", "VBA", "帳票", "監査", "データ"]):
            score += 5
        if domain_hits:
            score += 3
        if weak_hits:
            score -= min(len(weak_hits) * 2, 8)
        return clamp(score, 0, 15)

    def _score_supplier_dependency(self, external_hits: list[str], idea: ContentIdea) -> int:
        score = 10
        score -= min(len(external_hits) * 2, 8)
        if idea.preferred_platform in ["youtube", "tiktok"]:
            # 動画は素材・BGM・編集ツール依存が出やすい
            score -= 1
        return clamp(score, 0, 10)

    def _score_platform_fit(self, idea: ContentIdea, domain_hits: list[str]) -> int:
        platform = idea.preferred_platform
        text = normalize_text(idea.title, idea.pain, idea.unique_angle)
        if platform == "auto":
            return 7

        score = 5
        if platform == "note" and any(w in text for w in ["方法", "テンプレ", "vba", "excel", "チェック"]):
            score += 4
        if platform == "kindle" and any(w in text for w in ["ガイド", "入門", "体系", "実践"]):
            score += 4
        if platform == "youtube" and any(w in text for w in ["画面", "実演", "グラフ", "excel", "portal"]):
            score += 4
        if platform == "tiktok" and any(w in text for w in ["3選", "小技", "ng", "注意"]):
            score += 4
        if platform == "minigame" and any(w in text for w in ["ゲーム", "教育", "訓練", "発見"]):
            score += 4
        if domain_hits:
            score += 1
        return clamp(score, 0, 10)

    def _score_production_feasibility(self, idea: ContentIdea) -> int:
        platform = idea.preferred_platform
        if platform in ["note", "kindle", "auto"]:
            return 5
        if platform == "youtube":
            return 4
        if platform == "tiktok":
            return 4
        if platform == "minigame":
            return 3
        return 3

    def _decision(self, total: int) -> str:
        th = self.rules["decision_thresholds"]
        if total >= th["full_build"]:
            return "本気実装・有料化候補"
        if total >= th["validate_first"]:
            return "小さく検証してから本実装"
        if total >= th["free_or_lead_magnet"]:
            return "無料記事・集客用なら可"
        if total >= th["hold"]:
            return "保留"
        return "捨てる"

    def _recommend_platform(self, idea: ContentIdea, total: int, domain_hits: list[str]) -> str:
        if idea.preferred_platform != "auto":
            return idea.preferred_platform

        text = normalize_text(idea.title, idea.pain, idea.unique_angle)
        if "ゲーム" in text or "訓練" in text:
            return "minigame"
        if "入門" in text or "ガイド" in text or "体系" in text:
            return "kindle"
        if "画面" in text or "実演" in text or "グラフ" in text:
            return "youtube"
        if "3選" in text or "小技" in text:
            return "tiktok"
        if domain_hits:
            return "note"
        return "note"

    def _risks(self, idea: ContentIdea, weak_hits: list[str], external_hits: list[str], domain_hits: list[str]) -> list[str]:
        risks: list[str] = []
        if weak_hits:
            risks.append(f"一般的・競合過多になりやすい語が含まれます: {', '.join(weak_hits)}")
        if external_hits:
            risks.append(f"外部依存・権利確認が必要な要素があります: {', '.join(external_hits)}")
        if not domain_hits:
            risks.append("鈴木様の製造業・品質保証・VBA・OpenClaw経験との接続が弱い可能性があります。")
        if idea.confidential_level != "public_sample":
            risks.append("社内情報・機密情報の可能性があるため、公開用に匿名化・ダミー化が必要です。")
        if not risks:
            risks.append("大きな初期リスクは少ないですが、公開前に機密・著作権・最新規約を確認してください。")
        return risks

    def _next_actions(self, idea: ContentIdea, total: int, platform: str, risks: list[str]) -> list[str]:
        actions = [
            "公開可能なサンプルデータだけで小さな試作品を作る。",
            "同じテーマで既存記事・動画・Kindleが多すぎないか確認する。",
            "読者の困りごとを1文で明確化する。",
        ]

        if total >= 80:
            actions.insert(0, "有料noteまたはKindle化を前提に、章立てとサンプルコードを作る。")
        elif total >= 65:
            actions.insert(0, "無料記事または短いnoteで反応を見てから有料化する。")
        else:
            actions.insert(0, "テーマを製造業・品質保証・Excel/VBA寄りに絞り直す。")

        if platform == "youtube":
            actions.append("画面録画で見せられるBefore/Afterを準備する。")
        elif platform == "tiktok":
            actions.append("1本1結論のショート台本に分解する。")
        elif platform == "minigame":
            actions.append("まず2Dの診断ゲームとして作り、3D化は後回しにする。")
        elif platform == "kindle":
            actions.append("note記事3〜5本分を章立てに再編集する。")
        else:
            actions.append("note無料記事 → 有料記事の2段階で検証する。")
        return actions


    def _safe_publication_notes(self, idea: ContentIdea) -> list[str]:
        notes = [
            "公開前に、会社名・顧客名・品番・図面・寸法・原価・個人情報を必ず削除またはダミー化してください。",
            "他者の動画・記事・有料教材の丸写しではなく、自分の実務経験と公開可能なサンプルで再構成してください。",
            "YouTube、TikTok、note、KDPなどの最新規約は変わるため、公開直前に確認してください。",
        ]
        if idea.confidential_level == "secret":
            notes.insert(0, "この企画は secret 扱いです。外部API送信・公開・クラウドアップロードは禁止にしてください。")
        elif idea.confidential_level == "internal_only":
            notes.insert(0, "この企画は internal_only 扱いです。公開用には匿名化とダミーデータ化が必要です。")
        return notes

    def _outline(self, idea: ContentIdea, platform: str) -> list[str]:
        base = [
            f"タイトル: {idea.title}",
            f"対象読者: {idea.target_audience or '未設定'}",
            f"読者の痛み: {idea.pain or '未設定'}",
            "結論: 何がどれだけ楽になるかを最初に書く。",
            "現状の問題: 手作業、ミス、属人化、判断遅れを整理する。",
            "解決方法: 手順、コード、テンプレート、Portal連携を示す。",
            "サンプル: 公開可能なダミーデータで動作例を見せる。",
            "注意点: 機密情報、著作権、最新規約、社内確認。",
            "次の行動: テンプレ入手、チェックリスト、関連記事への導線。",
        ]
        if platform == "youtube":
            return [
                "冒頭10秒: この作業が何分短縮できるかを見せる。",
                "Before画面: 手作業の問題を見せる。",
                "After画面: 自動生成結果を見せる。",
                *base[4:],
                "最後: note/Kindle/テンプレへの導線。",
            ]
        if platform == "tiktok":
            return [
                "0〜3秒: 品質保証でまだ手入力していませんか？",
                "3〜20秒: よくあるミスを1つ見せる。",
                "20〜45秒: 自動化後の結果を見せる。",
                "45〜60秒: 詳細はnote/YouTubeへ誘導。",
            ]
        if platform == "minigame":
            return [
                "ゲーム目的: 監査・検査・異常検出の観点を学ぶ。",
                "プレイヤー操作: NG箇所をクリックまたは選択する。",
                "ステージ1: 明らかなミスを見つける。",
                "ステージ2: 根拠不足を見つける。",
                "ステージ3: 是正処置の弱点を見つける。",
                "結果画面: 点数、解説、学習リンク。",
            ]
        if platform == "kindle":
            return [
                "第1章: なぜこの業務が属人化するのか",
                "第2章: 必要なデータと帳票の整理",
                "第3章: Excel/VBAまたはPortalでの自動化設計",
                "第4章: サンプルコード",
                "第5章: 現場導入時の注意点",
                "第6章: 応用例とチェックリスト",
            ]
        return base
