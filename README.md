# Adamastus

**Azores Fisheries Data & Analysis**

Adamastus is an independent Python project for collecting, storing and exploring fisheries landings data published by [LOTAÇOR](https://www.lotacor.pt/). It currently retrieves the monthly aggregated reports `Descargas nos Açores` (`DNA`) and `Descargas por Ilha` (`DPI`), and provides a multi-page Streamlit dashboard.

The application and dashboard interface are in **Portuguese (Portugal)**. Project documentation and code comments are in English.

> **Data-use notice:** The software is released under the BSD 3-Clause licence. This licence does not cover LOTAÇOR data. Permission and applicable reuse conditions for redistribution of downloaded data have not yet been confirmed. The repository therefore excludes the local database and CSV exports by default. See [DATA_SOURCES.md](DATA_SOURCES.md).

## Features

- Retrieve LOTAÇOR data by calendar month for `DNA` and `DPI` reports.
- Store observations and download history in a local SQLite database.
- Skip successfully downloaded months on subsequent runs, or refresh a selected period.
- Export stored observations to CSV.
- Explore long-term patterns, species, seasonality, island-level landings and data coverage in a Streamlit dashboard.

The API responses examined so far contain species-level aggregates for the requested date interval. The monthly records are therefore **monthly aggregates, not daily observations**.

## Requirements

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)

## Installation

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd Adamastus
uv sync
```

`uv sync` creates the project environment and installs the dependencies declared in `pyproject.toml`.

## Download data

Download both report types from January 2020 to the current date (the defaults in `config.py`):

```bash
uv run python main.py
```

The start date must be the first day of a month. The end date must be the last day of a month,
or today when downloading the current partial month. This keeps monthly aggregates consistent.
The current month is refreshed as the end date advances, rather than being treated as complete
after its first successful download.

For a smaller initial test:

```bash
uv run python main.py --start-date 2020-01-01 --end-date 2020-03-31 --workers 2
```

Useful options:

```bash
# Download only one report type
uv run python main.py --query-types DNA
uv run python main.py --query-types DPI

# Re-download and replace data for the selected months
uv run python main.py --start-date 2020-01-01 --end-date 2020-03-31 --refresh

# Export the existing database without contacting the API
uv run python main.py --export-only
```

The command exits with a non-zero status if any monthly request fails, which is useful for
scheduled runs and GitHub Actions.

The downloader writes the SQLite database to `data/lotacor.db` and the CSV export to `data/exports/lotacor_monthly.csv`. These generated files are ignored by Git. Run the downloader locally before launching the dashboard if you do not already have a database.

## Run the dashboard

```bash
uv run streamlit run dashboard/Visao_geral.py
```

The dashboard contains five pages:

1. **Visão geral** — long-term averages, annual trends, latest-year-to-date metrics and species composition.
2. **Análise por espécie** — annual species comparisons, trends and exploratory composition indicators.
3. **Sazonalidade** — monthly patterns overall and by species.
4. **Desembarques por ilha** — island-level landed quantity, economic value, weighted average price and leading species.
5. **Cobertura dos dados** — monthly API request coverage for both regional (`DNA`) and island (`DPI`) reports.

The dashboard interface is in Portuguese. The page filenames use ASCII characters to avoid filename-encoding issues across operating systems.

## Data interpretation

- `DNA` represents the regional report, `Descargas nos Açores`.
- `DPI` represents the island report, `Descargas por Ilha`.
- The database retains report type, query filters, island labels and download history.
- A successful response containing no species records is recorded as a successful download with zero observation rows. Failed requests are recorded separately and can be retried on a later run.
- Island-level average prices are weighted, calculated as total economic value divided by total landed weight.
- Landings data alone do not measure stock abundance, fishing mortality or ecological biodiversity. Interpret trends and composition indicators with care.

## Tests

Run the automated unit tests from the project root:

```bash
uv run python -m unittest discover -s tests -v
```

The tests cover analysis calculations, SQLite storage and migration, monthly date handling,
and command-line failure reporting. The Streamlit pages should also be checked visually with
representative local data after installation.

## Project layout

```text
Adamastus/
├── analysis/             # Analysis and derived indicators
├── dashboard/            # Portuguese Streamlit dashboard
│   └── pages/            # Additional dashboard pages
├── lotacor/              # API client, downloader, database and exports
├── tests/                # Automated unit tests
├── data/                 # Local SQLite database and CSV exports (not committed)
├── figures/              # Locally generated figures (not committed)
├── config.py             # Paths and download settings
├── main.py               # Downloader command-line entry point
├── pyproject.toml        # Project metadata and dependencies
├── requirements.txt      # Dependencies for hosts that use pip
└── DATA_SOURCES.md       # Data provenance and reuse notes
```

## Configuration and network notes

Settings such as the date range, worker count, API URL and TLS verification are in `config.py`.

TLS certificate verification is enabled by default. If certificate verification fails, first update the local certificate bundle and check the network configuration:

```bash
uv pip install --upgrade certifi
```

`VERIFY_TLS = False` is available only as a temporary diagnostic workaround. Do not use it as a permanent setting.

## Licence

The Adamastus source code is distributed under the [BSD 3-Clause licence](LICENSE). Third-party packages retain their own licences. LOTAÇOR data are not covered by the software licence; see [DATA_SOURCES.md](DATA_SOURCES.md).

## AI-assisted development

Development of Adamastus involved assistance from ChatGPT (OpenAI). See [AI_ASSISTANCE.md](AI_ASSISTANCE.md) for details of how AI was used and the maintainer's responsibilities.

