import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import pandas as pd

from config import DATABASE_PATH, DATA_DIR


@contextmanager
def get_connection():
    """Open a SQLite connection and always commit and close it."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(DATABASE_PATH), timeout=30)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _create_observations_table(connection, table_name="observations"):
    connection.execute(f"""
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_type TEXT NOT NULL,
            lota_id TEXT NOT NULL,
            ilha_id TEXT NOT NULL,
            fao TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            island TEXT NOT NULL DEFAULT '',
            species TEXT NOT NULL,
            weight_kg REAL,
            value_eur REAL,
            average_price_eur REAL,
            retrieved_at TEXT NOT NULL,
            raw_json TEXT,
            UNIQUE (query_type, lota_id, ilha_id, fao, period_start, island, species)
        )
    """)


def initialise_database():
    """Create tables and migrate older observation schemas without losing data."""

    with get_connection() as connection:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='observations'"
        ).fetchone()
        if not table_exists:
            _create_observations_table(connection)
        else:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(observations)")}
            unique_indexes = connection.execute("PRAGMA index_list(observations)").fetchall()
            unique_columns = [
                [item[2] for item in connection.execute(f"PRAGMA index_info('{index[1]}')")]
                for index in unique_indexes if index[2]
            ]
            needs_rebuild = "island" not in columns or not any(
                {"island", "species"}.issubset(set(index_columns)) for index_columns in unique_columns
            )
            if needs_rebuild:
                connection.execute("DROP TABLE IF EXISTS observations_new")
                _create_observations_table(connection, "observations_new")
                island_expression = "island" if "island" in columns else "''"
                connection.execute(f"""
                    INSERT OR IGNORE INTO observations_new (
                        id, query_type, lota_id, ilha_id, fao, period_start, period_end,
                        island, species, weight_kg, value_eur, average_price_eur, retrieved_at, raw_json
                    )
                    SELECT id, query_type, lota_id, ilha_id, fao, period_start, period_end,
                           {island_expression}, species, weight_kg, value_eur, average_price_eur,
                           retrieved_at, raw_json
                    FROM observations
                """)
                connection.execute("DROP TABLE observations")
                connection.execute("ALTER TABLE observations_new RENAME TO observations")

        connection.execute("""
            CREATE TABLE IF NOT EXISTS download_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_type TEXT NOT NULL,
                lota_id TEXT NOT NULL,
                ilha_id TEXT NOT NULL,
                fao TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                status TEXT NOT NULL,
                record_count INTEGER NOT NULL DEFAULT 0,
                retrieved_at TEXT NOT NULL,
                error TEXT,
                UNIQUE (query_type, lota_id, ilha_id, fao, period_start)
            )
        """)
        # Collapse legacy duplicate requests within the same calendar month and scope.
        connection.execute("""
            DELETE FROM observations
            WHERE id NOT IN (
                SELECT MAX(id) FROM observations
                GROUP BY query_type, lota_id, ilha_id, fao, substr(period_start, 1, 7), island, species
            )
        """)
        connection.execute("""
            DELETE FROM download_history
            WHERE id NOT IN (
                SELECT MAX(id) FROM download_history
                GROUP BY query_type, lota_id, ilha_id, fao, substr(period_start, 1, 7)
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_obs_period ON observations(period_start)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_obs_species ON observations(species)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_obs_island ON observations(island)")


def month_is_downloaded(start_date, end_date, query_type, lota_id, ilha_id, fao):
    """Check whether a successful request covers the requested dates and query scope."""

    with get_connection() as connection:
        row = connection.execute("""
            SELECT 1 FROM download_history
            WHERE query_type = ? AND lota_id = ? AND ilha_id = ? AND fao = ?
              AND substr(period_start, 1, 7) = substr(?, 1, 7)
              AND period_start <= ? AND period_end >= ? AND status = 'success'
            LIMIT 1
        """, (query_type, lota_id, ilha_id, fao, start_date, start_date, end_date)).fetchone()
    return row is not None


def _to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _aggregate_records(records):
    """Combine repeated species rows within each island, preserving totals."""

    grouped = {}
    for record in records:
        island = record.get("Ilha", "") or ""
        species = record.get("Espécie", "") or "Espécie não identificada"
        key = (island, species)
        item = grouped.setdefault(key, {"weight": 0.0, "value": 0.0, "raw": []})
        item["weight"] += _to_float(record.get("Peso (Kg)")) or 0.0
        item["value"] += _to_float(record.get("Valor (€)")) or 0.0
        item["raw"].append(record)

    return [
        {
            "island": island,
            "species": species,
            "weight_kg": values["weight"],
            "value_eur": values["value"],
            "average_price_eur": values["value"] / values["weight"] if values["weight"] else None,
            "raw_json": json.dumps(values["raw"], ensure_ascii=False),
        }
        for (island, species), values in grouped.items()
    ]


def save_month(start_date, end_date, records, query_type="DNA",
               lota_id="all", ilha_id="all", fao="all"):
    """Replace one calendar month's observations and mark the request successful."""

    retrieved_at = datetime.now(timezone.utc).isoformat()
    rows = [(
        query_type, lota_id, ilha_id, fao, start_date, end_date, item["island"], item["species"],
        item["weight_kg"], item["value_eur"], item["average_price_eur"], retrieved_at, item["raw_json"],
    ) for item in _aggregate_records(records)]

    with get_connection() as connection:
        connection.execute("""
            DELETE FROM observations
            WHERE query_type = ? AND lota_id = ? AND ilha_id = ? AND fao = ?
              AND substr(period_start, 1, 7) = substr(?, 1, 7)
        """, (query_type, lota_id, ilha_id, fao, start_date))
        connection.execute("""
            DELETE FROM download_history
            WHERE query_type = ? AND lota_id = ? AND ilha_id = ? AND fao = ?
              AND substr(period_start, 1, 7) = substr(?, 1, 7)
        """, (query_type, lota_id, ilha_id, fao, start_date))

        if rows:
            connection.executemany("""
                INSERT INTO observations (
                    query_type, lota_id, ilha_id, fao, period_start, period_end, island, species,
                    weight_kg, value_eur, average_price_eur, retrieved_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

        connection.execute("""
            INSERT INTO download_history (
                query_type, lota_id, ilha_id, fao, period_start, period_end,
                status, record_count, retrieved_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, 'success', ?, ?, NULL)
        """, (query_type, lota_id, ilha_id, fao, start_date, end_date, len(records), retrieved_at))


def record_failure(start_date, end_date, error, query_type="DNA",
                   lota_id="all", ilha_id="all", fao="all"):
    """Record a failed request, replacing any previous record for that calendar month."""

    retrieved_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        connection.execute("""
            DELETE FROM download_history
            WHERE query_type = ? AND lota_id = ? AND ilha_id = ? AND fao = ?
              AND substr(period_start, 1, 7) = substr(?, 1, 7)
        """, (query_type, lota_id, ilha_id, fao, start_date))
        connection.execute("""
            INSERT INTO download_history (
                query_type, lota_id, ilha_id, fao, period_start, period_end,
                status, record_count, retrieved_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, 'failed', 0, ?, ?)
        """, (query_type, lota_id, ilha_id, fao, start_date, end_date, retrieved_at, str(error)))


def load_observations():
    """Load all stored observations into a DataFrame."""

    with get_connection() as connection:
        return pd.read_sql_query("""
            SELECT period_start, period_end, query_type, lota_id, ilha_id, fao, island,
                   species, weight_kg, value_eur, average_price_eur, retrieved_at
            FROM observations ORDER BY period_start, island, species
        """, connection)


def load_download_history():
    """Load monthly download status records for checking data coverage."""

    with get_connection() as connection:
        return pd.read_sql_query("""
            SELECT query_type, lota_id, ilha_id, fao, period_start, period_end,
                   status, record_count, retrieved_at, error
            FROM download_history ORDER BY period_start
        """, connection)
