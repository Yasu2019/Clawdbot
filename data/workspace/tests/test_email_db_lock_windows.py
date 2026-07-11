import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from data.workspace import email_db_lock as module


class EmailDbLockWindowsTests(unittest.TestCase):
    def test_live_owner_is_not_cleared(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "ops.lock"
            path.write_text("first|pid=12345\n", encoding="utf-8")
            contender = module.EmailDbLock("second", path=path)
            with patch.object(module, "process_exists", return_value=True):
                self.assertFalse(contender.acquire())
            self.assertEqual(path.read_text(encoding="utf-8").strip(), "first|pid=12345")

    def test_dead_owner_is_replaced(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "ops.lock"
            path.write_text("old|pid=12345\n", encoding="utf-8")
            contender = module.EmailDbLock("new", path=path)
            with patch.object(module, "process_exists", return_value=False):
                self.assertTrue(contender.acquire())
            contender.release()
            self.assertFalse(path.exists())

    def test_non_owner_cannot_release_replaced_lock(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "ops.lock"
            owner = module.EmailDbLock("owner", path=path)
            self.assertTrue(owner.acquire())
            path.write_text("replacement|pid=99999\n", encoding="utf-8")
            owner.release()
            self.assertTrue(path.exists())

    def test_windows_process_check_closes_valid_handle(self):
        kernel = Mock()
        kernel.OpenProcess.return_value = 42
        fake_ctypes = Mock()
        fake_ctypes.windll.kernel32 = kernel
        with patch.object(module, "ctypes", fake_ctypes):
            self.assertTrue(module._windows_process_exists(12345))
        kernel.CloseHandle.assert_called_once_with(42)


if __name__ == "__main__":
    unittest.main()
