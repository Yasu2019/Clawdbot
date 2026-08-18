# -*- coding: utf-8 -*-
"""Fail-closed text quality checks shared by all local-agent writers."""
from __future__ import annotations

import re

HIDDEN_REASONING = re.compile(r"<\s*(?:think|thinking|analysis)\b", re.IGNORECASE)
MOJIBAKE_TOKENS = (
    "縺", "繝", "繧", "蜿", "譁", "讎", "遒", "莠", "譛", "蛻",
    "逕ｨ", "閭ｽ", "諤ｧ", "隱阪", "矩", "窶", "迚ｩ", "荳",
)


class TextQualityError(ValueError):
    pass


def quality_issues(text: str) -> list[str]:
    issues: list[str] = []
    if not text or not text.strip():
        issues.append("empty_text")
        return issues
    if HIDDEN_REASONING.search(text):
        issues.append("hidden_reasoning_tag")
    if "\ufffd" in text:
        issues.append("unicode_replacement_character")
    if "\uf8f0" in text or "\uf8f1" in text or "\uf8f2" in text or "\uf8f3" in text:
        issues.append("private_use_character")
    controls = [c for c in text if 0x80 <= ord(c) <= 0x9F]
    if controls:
        issues.append("c1_control_character")
    hits = sum(text.count(token) for token in MOJIBAKE_TOKENS)
    if hits >= 2:
        issues.append(f"mojibake_signature:{hits}")
    return issues


def decode_http_text(raw: bytes, *, label: str = "http body") -> str:
    """Decode API/HTTP bytes without inserting U+FFFD.

    UTF-8 is tried first. If that fails, cp1252 is used so Latin-1 publisher
    names such as Universita remain recoverable. Replacement characters are
    never introduced here; callers must not use errors='replace'.
    """
    if raw is None:
        raise TextQualityError(f"{label} rejected: empty_bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    if "\ufffd" in text:
        raise TextQualityError(f"{label} rejected: unicode_replacement_character")
    return text


def replace_replacement_chars(value):
    """Replace U+FFFD with an ASCII marker so stored harvest notes stay valid."""
    mark = "[encoding-loss]"
    if isinstance(value, str):
        return value.replace("\ufffd", mark)
    if isinstance(value, dict):
        return {key: replace_replacement_chars(item) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_replacement_chars(item) for item in value]
    return value


def validate_text(text: str, *, label: str = "text") -> str:
    issues = quality_issues(text)
    if issues:
        raise TextQualityError(f"{label} rejected: {', '.join(issues)}")
    # Encoding/readback invariant used by every caller before persistence.
    if text.encode("utf-8").decode("utf-8") != text:
        raise TextQualityError(f"{label} rejected: utf8_roundtrip_failed")
    return text
