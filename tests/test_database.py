import tempfile
import unittest
from pathlib import Path

import lotacor.database as database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.original_database_path = database.DATABASE_PATH
        self.original_data_dir = database.DATA_DIR
        database.DATABASE_PATH = root / "test.db"
        database.DATA_DIR = root / "data"
        database.initialise_database()

    def tearDown(self):
        database.DATABASE_PATH = self.original_database_path
        database.DATA_DIR = self.original_data_dir
        self.temp_dir.cleanup()

    def test_save_month_aggregates_species_by_island_and_records_history(self):
        records = [
            {"Ilha": "São Miguel", "Espécie": "Atum", "Peso (Kg)": "100", "Valor (€)": "500"},
            {"Ilha": "São Miguel", "Espécie": "Atum", "Peso (Kg)": "50", "Valor (€)": "300"},
            {"Ilha": "Terceira", "Espécie": "Atum", "Peso (Kg)": "25", "Valor (€)": "150"},
        ]
        database.save_month("2020-01-01", "2020-01-31", records, query_type="DPI")
        observations = database.load_observations()
        self.assertEqual(len(observations), 2)
        sao_miguel = observations[observations["island"] == "São Miguel"].iloc[0]
        self.assertEqual(sao_miguel["weight_kg"], 150)
        self.assertEqual(sao_miguel["value_eur"], 800)
        self.assertAlmostEqual(sao_miguel["average_price_eur"], 800 / 150)
        history = database.load_download_history()
        self.assertEqual(history.iloc[0]["status"], "success")
        self.assertEqual(history.iloc[0]["record_count"], 3)

    def test_empty_response_is_a_successful_download(self):
        database.save_month("2020-02-01", "2020-02-29", [], query_type="DNA")
        self.assertTrue(database.load_observations().empty)
        history = database.load_download_history()
        self.assertEqual(history.iloc[0]["status"], "success")
        self.assertEqual(history.iloc[0]["record_count"], 0)

    def test_refresh_replaces_month_instead_of_duplicating(self):
        first = [{"Espécie": "Atum", "Peso (Kg)": 100, "Valor (€)": 500}]
        second = [{"Espécie": "Atum", "Peso (Kg)": 200, "Valor (€)": 1200}]
        database.save_month("2020-03-01", "2020-03-31", first)
        database.save_month("2020-03-01", "2020-03-31", second)
        observations = database.load_observations()
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations.iloc[0]["weight_kg"], 200)



    def test_initialise_database_migrates_legacy_schema_without_island(self):
        import sqlite3

        connection = sqlite3.connect(database.DATABASE_PATH)
        connection.execute("DROP TABLE observations")
        connection.execute("DROP TABLE download_history")
        connection.execute("""
            CREATE TABLE observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_type TEXT NOT NULL, lota_id TEXT NOT NULL, ilha_id TEXT NOT NULL,
                fao TEXT NOT NULL, period_start TEXT NOT NULL, period_end TEXT NOT NULL,
                species TEXT NOT NULL, weight_kg REAL, value_eur REAL,
                average_price_eur REAL, retrieved_at TEXT NOT NULL, raw_json TEXT,
                UNIQUE (query_type, lota_id, ilha_id, fao, period_start, species)
            )
        """)
        connection.execute("""
            INSERT INTO observations (
                query_type, lota_id, ilha_id, fao, period_start, period_end, species,
                weight_kg, value_eur, average_price_eur, retrieved_at, raw_json
            ) VALUES ('DNA', 'all', 'all', 'all', '2020-01-01', '2020-01-31',
                      'Atum', 100, 500, 5, '2020-02-01T00:00:00+00:00', '{}')
        """)
        connection.commit()
        connection.close()

        database.initialise_database()
        observations = database.load_observations()
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations.iloc[0]["species"], "Atum")
        self.assertEqual(observations.iloc[0]["island"], "")

    def test_successful_month_must_cover_requested_end_date(self):
        database.save_month("2026-11-01", "2026-11-23", [], query_type="DNA")
        self.assertTrue(database.month_is_downloaded(
            "2026-11-01", "2026-11-23", "DNA", "all", "all", "all"
        ))
        self.assertFalse(database.month_is_downloaded(
            "2026-11-01", "2026-11-24", "DNA", "all", "all", "all"
        ))

    def test_missing_species_name_gets_portuguese_fallback(self):
        database.save_month("2020-04-01", "2020-04-30", [{"Peso (Kg)": 10, "Valor (€)": 20}])
        observations = database.load_observations()
        self.assertEqual(observations.iloc[0]["species"], "Espécie não identificada")


if __name__ == "__main__":
    unittest.main()
