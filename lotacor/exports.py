from config import CSV_PATH, EXPORT_DIR
from lotacor.database import load_observations


def export_csv():
    """Export all stored observations to CSV."""

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_observations()
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    print("\nCSV exported: {}".format(CSV_PATH))
    print("Rows: {}".format(len(df)))

    return df
