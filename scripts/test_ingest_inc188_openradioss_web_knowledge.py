# -*- coding: utf-8 -*-
"""UTF-8 and schema regression tests for INC-188 knowledge ingestion."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ingest_inc188_openradioss_web_knowledge as ingest_module


class Inc188KnowledgeIngestTest(unittest.TestCase):
    def test_utf8_round_trip_and_mojibake_rejection(self) -> None:
        self.assertEqual(ingest_module.validate_utf8("延性破断").decode("utf-8"), "延性破断")
        with self.assertRaises(ValueError):
            ingest_module.validate_utf8("縺薙ｌは破損")

    @patch.object(ingest_module, "fetch_metadata", return_value=(200, "https://example.test", "公式", "説明"))
    def test_ingest_has_no_replacement_characters(self, _fetch) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            db = Path(temporary) / "knowledge.db"
            result = ingest_module.ingest(db)
            self.assertEqual(result["replacement_character_rows"], 0)
            connection = sqlite3.connect(db)
            count = connection.execute("SELECT COUNT(*) FROM inc188_web_knowledge").fetchone()[0]
            connection.close()
            self.assertEqual(count, len(ingest_module.SOURCES))


if __name__ == "__main__":
    unittest.main()
