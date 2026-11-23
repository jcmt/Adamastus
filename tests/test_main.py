import sys
import unittest
from unittest.mock import patch

import main


class MainTests(unittest.TestCase):
    @patch("main.export_csv")
    @patch("main.download_data")
    @patch("main.initialise_database")
    def test_returns_nonzero_when_any_download_fails(self, initialise, download, export):
        download.side_effect = [
            {"downloaded": 2, "failed": 0, "skipped": 0},
            {"downloaded": 1, "failed": 1, "skipped": 0},
        ]
        with patch.object(sys, "argv", ["main.py"]):
            result = main.main()
        self.assertEqual(result, 1)
        initialise.assert_called_once()
        self.assertEqual(download.call_count, 2)
        export.assert_called_once()

    @patch("main.export_csv")
    @patch("main.download_data")
    @patch("main.initialise_database")
    def test_export_only_does_not_download(self, initialise, download, export):
        with patch.object(sys, "argv", ["main.py", "--export-only"]):
            result = main.main()
        self.assertEqual(result, 0)
        download.assert_not_called()
        export.assert_called_once()


if __name__ == "__main__":
    unittest.main()
