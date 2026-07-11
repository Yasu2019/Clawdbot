import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import unittest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from data.workspace import email_search_index as module


def response(status_code, payload=None):
    item = Mock()
    item.status_code = status_code
    item.json.return_value = payload or {"ok": True}
    item.raise_for_status.side_effect = (
        requests.HTTPError(str(status_code)) if status_code >= 400 else None
    )
    return item


class GmailRequestRetryTests(unittest.TestCase):
    def test_save_json_replaces_file_and_cleans_temp_file(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "state.json"
            path.write_text('{"old": true}', encoding="utf-8")
            module.save_json(path, {"new": True})
            self.assertEqual(module.load_json(path), {"new": True})
            self.assertEqual(list(Path(tempdir).glob("*.tmp")), [])

    @patch.object(module, "refresh_gmail_token")
    def test_refresh_session_adopts_newer_disk_token(self, refresh_token):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            token_path = root / "token.json"
            creds_path = root / "credentials.json"
            module.save_json(token_path, {
                "access_token": "newer-token",
                "refresh_token": "refresh-token",
                "expiry_date": int((time.time() + 3600) * 1000),
            })
            module.save_json(creds_path, {"installed": {}})
            session = requests.Session()
            session.headers["Authorization"] = "Bearer older-token"
            session._gmail_token_path = token_path
            session._gmail_creds_path = creds_path

            module.refresh_gmail_session(session)

            self.assertEqual(session.headers["Authorization"], "Bearer newer-token")
            refresh_token.assert_not_called()

    @patch.object(module, "refresh_gmail_session")
    def test_refreshes_once_and_replays_after_401(self, refresh):
        session = Mock()
        session.request.side_effect = [response(401), response(200, {"id": "message"})]

        result = module.gmail_request(session, "GET", "https://example.invalid/message")

        self.assertEqual(result, {"id": "message"})
        refresh.assert_called_once_with(session)
        self.assertEqual(session.request.call_count, 2)

    @patch.object(module.time, "sleep")
    def test_retries_transient_connection_errors_with_upper_bound(self, sleep):
        session = Mock()
        session.request.side_effect = [
            requests.ConnectionError("closed"),
            requests.ConnectionError("closed"),
            response(200),
        ]

        self.assertEqual(
            module.gmail_request(session, "GET", "https://example.invalid/message"),
            {"ok": True},
        )
        self.assertEqual(session.request.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch.object(module.time, "sleep")
    def test_does_not_retry_non_idempotent_transient_failure(self, sleep):
        session = Mock()
        session.request.return_value = response(503)

        with self.assertRaises(requests.HTTPError):
            module.gmail_request(session, "POST", "https://example.invalid/action")

        self.assertEqual(session.request.call_count, 1)
        sleep.assert_not_called()

    @patch.object(module, "refresh_gmail_session")
    def test_fails_after_second_401(self, refresh):
        session = Mock()
        session.request.side_effect = [response(401), response(401)]

        with self.assertRaisesRegex(RuntimeError, "after refresh"):
            module.gmail_request(session, "GET", "https://example.invalid/message")

        refresh.assert_called_once_with(session)


if __name__ == "__main__":
    unittest.main()
