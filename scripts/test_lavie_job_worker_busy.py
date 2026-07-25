# -*- coding: utf-8 -*-
"""Regression test: a running satellite job must not create a hidden queue."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import lavie_job_worker as worker


class WorkerBusyTest(unittest.TestCase):
    def test_second_job_returns_busy_without_waiting(self) -> None:
        entered = threading.Event()
        release = threading.Event()

        def slow_job(_job, _jobs_root, _state):
            entered.set()
            release.wait(timeout=5)
            return {"status": "ok"}

        with tempfile.TemporaryDirectory() as temp_dir:
            state = worker.WorkerState("test-token", Path(temp_dir), "test")
            server = ThreadingHTTPServer(("127.0.0.1", 0), worker.make_handler(state))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}/jobs"
            payload = json.dumps({"job_id": "test", "type": "shell"}).encode("utf-8")

            def post() -> None:
                request = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json", "X-Satellite-Token": "test-token"},
                    method="POST",
                )
                urllib.request.urlopen(request, timeout=5).read()

            with patch.object(worker, "execute_job", side_effect=slow_job):
                first = threading.Thread(target=post, daemon=True)
                first.start()
                self.assertTrue(entered.wait(timeout=2))
                started = time.monotonic()
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    post()
                self.assertEqual(caught.exception.code, 409)
                body = json.loads(caught.exception.read().decode("utf-8"))
                self.assertEqual(body["error"], "worker_busy")
                self.assertLess(time.monotonic() - started, 1.0)
                release.set()
                first.join(timeout=2)

            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
