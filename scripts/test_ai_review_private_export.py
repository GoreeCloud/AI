"""Private review export file-system regression tests."""
import os
import stat
import tempfile
import unittest
from pathlib import Path
from ai_review_local import _private_export


class PrivateExportTests(unittest.TestCase):
    def test_private_file_is_created_once(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "review.html"
            _private_export(str(path), "Private example")
            self.assertEqual(path.read_text(), "Private example")
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                _private_export(str(path), "Forbidden replacement")
            self.assertEqual(path.read_text(), "Private example")
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()),
                             ["review.html"])

    def test_missing_directory_fails_without_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            invalid = Path(folder) / "missing" / "review.html"
            with self.assertRaises(OSError):
                _private_export(str(invalid), "Private")
            self.assertFalse(invalid.exists())


if __name__ == "__main__":
    unittest.main()
