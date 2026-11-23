import unittest
from datetime import date
from unittest.mock import patch

from lotacor.downloader import monthly_intervals


class DownloaderTests(unittest.TestCase):
    def test_monthly_intervals_include_full_months(self):
        self.assertEqual(
            monthly_intervals("2020-01-01", "2020-03-31"),
            [("2020-01-01", "2020-01-31"),
             ("2020-02-01", "2020-02-29"),
             ("2020-03-01", "2020-03-31")],
        )

    def test_current_month_can_end_today(self):
        today = date.today().isoformat()
        intervals = monthly_intervals(today[:8] + "01", today)
        self.assertEqual(intervals[-1][1], today)

    def test_rejects_partial_start_month(self):
        with self.assertRaisesRegex(ValueError, "first day"):
            monthly_intervals("2020-01-02", "2020-01-31")

    def test_rejects_historical_partial_end_month(self):
        with self.assertRaisesRegex(ValueError, "last day"):
            monthly_intervals("2020-01-01", "2020-02-15")

    def test_rejects_reversed_dates(self):
        with self.assertRaisesRegex(ValueError, "before or equal"):
            monthly_intervals("2020-02-01", "2020-01-31")


if __name__ == "__main__":
    unittest.main()
