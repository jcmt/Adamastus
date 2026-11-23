from pathlib import Path
from datetime import date


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
EXPORT_DIR = DATA_DIR / "exports"
FIGURES_DIR = PROJECT_DIR / "figures"

DATABASE_PATH = DATA_DIR / "lotacor.db"
CSV_PATH = EXPORT_DIR / "lotacor_monthly.csv"


# ============================================================
# DOWNLOAD SETTINGS
# ============================================================

START_DATE = "2020-01-01"
END_DATE = date.today().isoformat()

QUERY_TYPE = "DNA"       # Descargas nos Açores
LOTA_ID = "all"
FAO = "all"
ILHA_ID = "all"

MAX_WORKERS = 4
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 2

VERIFY_TLS = True

API_URL = "https://www.lotacor.pt/api/testQuery"
PAGE_URL = "https://www.lotacor.pt/pescado-descarregado"
