class EvidenceVerifier:
    def verify(self, result: str) -> str:
        if not result or len(result.strip()) < 10:
            return "⚠ 情報不足：回答を保留し、人間確認してください。"
        risky = ["推測", "不明", "根拠なし", "maybe", "probably"]
        if any(w in result for w in risky):
            return "⚠ 根拠不足（要確認）\n" + result
        return "✔ 検証済\n" + result
