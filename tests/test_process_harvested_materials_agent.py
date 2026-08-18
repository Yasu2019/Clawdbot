import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "process_harvested_materials_agent.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harvest_processor", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_materials_project_json_is_parsed_and_invalid_elasticity_flagged(tmp_path):
    module = load_module()
    source = tmp_path / "materials.json"
    source.write_text(json.dumps([
        {"material_id": "mp-good", "formula": "W", "space_group": "Im-3m",
         "energy_above_hull": 0.0, "density_g_cm3": 19.16,
         "bulk_modulus_GPa": 302.26, "shear_modulus_GPa": 148.15,
         "youngs_modulus_GPa": 382.03, "poissons_ratio": 0.2893},
        {"material_id": "mp-bad", "formula": "W", "space_group": "Fm-3m",
         "energy_above_hull": 0.47, "density_g_cm3": 19.19,
         "bulk_modulus_GPa": 285.9, "shear_modulus_GPa": -177.4,
         "youngs_modulus_GPa": None, "poissons_ratio": None},
    ]), encoding="utf-8")
    old_root = module.ROOT
    module.ROOT = tmp_path
    try:
        summary, know_how = module.summarize_materials_project(source)
    finally:
        module.ROOT = old_root
    assert "mp-good" in summary
    assert "負のせん断弾性率" in summary
    assert "安定候補1件" in know_how


def test_hidden_reasoning_is_removed():
    module = load_module()
    cleaned = module._clean_llm_response("<think>secret</think>## 概要\n確認済みです。")
    assert "secret" not in cleaned
    assert "確認済み" in cleaned


def test_mojibake_is_rejected():
    module = load_module()
    with pytest.raises(ValueError, match="文字化け|mojibake"):
        module._clean_llm_response("縺縺縺繧繧蜿 謚譁")


def test_real_observed_mojibake_variant_is_rejected():
    module = load_module()
    with pytest.raises(ValueError, match="mojibake"):
        module._clean_llm_response("## 讎りｦ・\n## 遒ｺ隱阪〒縺阪◆莠句ｮ・\n繝悶Ο繝・け")


def test_db_retry_retries_sqlite_lock_until_success():
    module = load_module()
    calls = {"count": 0}

    def operation():
        calls["count"] += 1
        if calls["count"] < 3:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    assert module._db_retry(operation, "unit-test") == "ok"
    assert calls["count"] == 3


def _row(con, **fields):
    con.row_factory = sqlite3.Row
    cols = "source, title, url, domain_tags, metadata_json, local_path, sha256, external_id"
    con.execute("CREATE TABLE IF NOT EXISTS t (" + cols.replace(", ", " TEXT, ") + " TEXT)")
    keys = ["source", "title", "url", "domain_tags", "metadata_json", "local_path", "sha256", "external_id"]
    vals = [fields.get(k) for k in keys]
    con.execute("INSERT INTO t VALUES (?,?,?,?,?,?,?,?)", vals)
    return con.execute("SELECT * FROM t").fetchone()


def test_empty_materials_json_is_permanent_failure(tmp_path):
    module = load_module()
    source = tmp_path / "empty.json"
    source.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="Materials Project JSON"):
        module.summarize_materials_project(source)
    assert module.is_permanent_source_failure(ValueError("Materials Project JSON\u304c\u7a7a\u3067\u3059"))


def test_empty_array_materials_json_is_permanent_failure(tmp_path):
    module = load_module()
    source = tmp_path / "none.json"
    source.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="\u6750\u6599\u30ec\u30b3\u30fc\u30c9"):
        module.summarize_materials_project(source)


def test_fffd_in_datacite_metadata_is_sanitized_not_rejected():
    module = load_module()
    con = sqlite3.connect(":memory:")
    row = _row(
        con,
        source="datacite",
        title="MICROORGANISMS VS. SYNTHETIC POLYMERS",
        url="https://doi.org/example",
        domain_tags="dataset,research",
        metadata_json=json.dumps({"publisher": "Universit\ufffd degli Studi di Milano"}, ensure_ascii=False),
        local_path=None,
        sha256=None,
        external_id="10.example/fffd",
    )
    body, know_how = module.summarize_metadata_deterministic(row)
    assert "\ufffd" not in body
    assert "[encoding-loss]" in body
    assert "datacite" in know_how
