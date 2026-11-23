from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta

from config import START_DATE, END_DATE, MAX_WORKERS, LOTA_ID, FAO, ILHA_ID
from lotacor.api import query_lotacor
from lotacor.database import month_is_downloaded, save_month, record_failure


def monthly_intervals(start_date, end_date):
    """Generate full monthly intervals and an optional current partial month."""

    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    if start > end:
        raise ValueError("Start date must be before or equal to end date.")
    if start.day != 1:
        raise ValueError("Start date must be the first day of a month for monthly data.")
    next_month = date(end.year + (end.month == 12), end.month % 12 + 1, 1)
    end_of_month = next_month - timedelta(days=1)
    if end != end_of_month and end != date.today():
        raise ValueError("End date must be the last day of a month or today for monthly data.")

    intervals = []
    current = start.replace(day=1)
    while current <= end:
        next_month = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
        month_end = next_month - timedelta(days=1)
        intervals.append((max(current, start).isoformat(), min(month_end, end).isoformat()))
        current = next_month
    return intervals


def download_data(start_date=START_DATE, end_date=END_DATE, workers=MAX_WORKERS,
                  refresh=False, query_type="DNA"):
    """Download missing monthly intervals for one LOTAÇOR report type."""

    intervals = monthly_intervals(start_date, end_date)
    pending = [
        (period_start, period_end) for period_start, period_end in intervals
        if refresh or not month_is_downloaded(period_start, period_end, query_type, LOTA_ID, ILHA_ID, FAO)
    ]

    print("\n{} · months requested: {} · to download: {} · workers: {}".format(
        query_type, len(intervals), len(pending), workers
    ))
    if not pending:
        print("All requested {} months are already in the database.".format(query_type))
        return {"downloaded": 0, "failed": 0, "skipped": len(intervals)}

    completed = failed = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(query_lotacor, start, end, query_type, LOTA_ID, FAO, ILHA_ID): (start, end)
            for start, end in pending
        }
        for index, future in enumerate(as_completed(futures), start=1):
            start, end = futures[future]
            try:
                records = future.result()
                save_month(start, end, records, query_type, LOTA_ID, ILHA_ID, FAO)
                completed += 1
                print("[{}/{}] {} {}: {} records".format(index, len(pending), query_type, start, len(records)))
            except Exception as error:
                failed += 1
                record_failure(start, end, error, query_type, LOTA_ID, ILHA_ID, FAO)
                print("[{}/{}] FAILED {} {}: {}".format(index, len(pending), query_type, start, error))

    skipped = len(intervals) - len(pending)
    print("{} summary: successful {}, failed {}, skipped {}".format(query_type, completed, failed, skipped))
    return {"downloaded": completed, "failed": failed, "skipped": skipped}
