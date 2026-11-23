import argparse

from config import START_DATE, END_DATE, MAX_WORKERS
from lotacor.database import initialise_database
from lotacor.downloader import download_data
from lotacor.exports import export_csv


def parse_arguments():
    """Read command-line options."""

    parser = argparse.ArgumentParser(
        description="Download and maintain the LOTAÇOR monthly landings database."
    )
    parser.add_argument("--start-date", default=START_DATE, help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end-date", default=END_DATE, help="End date (YYYY-MM-DD).")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--refresh", action="store_true", help="Re-download stored months.")
    parser.add_argument("--query-types", nargs="+", choices=["DNA", "DPI"], default=["DNA", "DPI"],
                        help="LOTAÇOR reports to download (default: DNA DPI).")
    parser.add_argument("--export-only", action="store_true",
                        help="Export the database without contacting LOTAÇOR.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    if args.workers < 1:
        raise ValueError("Number of workers must be at least 1.")

    initialise_database()
    failed_downloads = 0
    if not args.export_only:
        for query_type in args.query_types:
            result = download_data(args.start_date, args.end_date, args.workers, args.refresh, query_type)
            failed_downloads += result["failed"]
    export_csv()
    return 1 if failed_downloads else 0


if __name__ == "__main__":
    raise SystemExit(main())
