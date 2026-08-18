import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/local_agent/text_quality.py"


def load_module():
    spec = importlib.util.spec_from_file_location("text_quality", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_valid_japanese_passes():
    module = load_module()
    text = "日本語の品質確認を行い、取得した根拠だけを保存します。"
    assert module.validate_text(text) == text


@pytest.mark.parametrize("bad", [
    "<think>hidden reasoning</think>結果",
    "文字化け\ufffdを含む結果",
    "## 讎りｦ・\n## 遒ｺ隱阪〒縺阪◆莠句ｮ・",
])
def test_bad_text_fails_closed(bad):
    module = load_module()
    with pytest.raises(module.TextQualityError):
        module.validate_text(bad)


def test_decode_http_text_recovers_cp1252_publisher():
    module = load_module()
    raw = "Universit\xe0 degli Studi di Milano".encode("cp1252")
    assert module.decode_http_text(raw) == "Universit\u00e0 degli Studi di Milano"


def test_replace_replacement_chars_uses_ascii_marker():
    module = load_module()
    cleaned = module.replace_replacement_chars({"publisher": "Universit\ufffd IUAV"})
    assert cleaned["publisher"] == "[encoding-loss]".join(["Universit", " IUAV"]).replace("[encoding-loss] IUAV", "[encoding-loss] IUAV")
    assert "\ufffd" not in cleaned["publisher"]
    assert cleaned["publisher"] == "Universit[encoding-loss] IUAV"
