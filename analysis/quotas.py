"""Verified fisheries quota and catch-limit reference data."""

from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
QUOTA_DATA_PATH = PROJECT_DIR / "data" / "quota_register.csv"
QUOTA_EVENTS_PATH = PROJECT_DIR / "data" / "quota_events.csv"

QUOTA_COLUMNS = [
    "year", "species", "scientific_name", "stock_code", "source_level",
    "limit_type", "limit_tonnes", "geographic_scope", "fleet_scope", "period",
    "status_as_of", "source_name", "source_url", "source_date",
    "verification_status", "notes", "chart_eligible",
]
EVENT_COLUMNS = [
    "year", "species", "stock_code", "event_type", "event_date",
    "source_name", "source_url", "source_date", "notes",
]


def _load_csv(path, columns):
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=columns)
    return pd.read_csv(path, keep_default_na=False)


def load_quota_limits(path=QUOTA_DATA_PATH):
    """Load quota records, retaining zero and unresolved textual values."""

    quotas = _load_csv(path, QUOTA_COLUMNS)
    if quotas.empty:
        return quotas
    quotas["year"] = pd.to_numeric(quotas["year"], errors="coerce").astype("Int64")
    quotas["limit_tonnes"] = pd.to_numeric(quotas["limit_tonnes"], errors="coerce")
    return quotas.dropna(subset=["year", "species"]).copy()


def load_quota_events(path=QUOTA_EVENTS_PATH):
    """Load dated official quota warnings, closures and reopenings."""

    events = _load_csv(path, EVENT_COLUMNS)
    if not events.empty:
        events["year"] = pd.to_numeric(events["year"], errors="coerce").astype("Int64")
    return events


def quota_source_colours():
    """Stable source-level colours for quota charts."""

    return {
        "Regional": "#2E8B57",
        "Nacional": "#2878B5",
        "UE": "#8A63B8",
    }


def annual_quotas_for_chart(species, years, path=QUOTA_DATA_PATH):
    """Return verified annual limits explicitly approved for landings comparison.

    Eligibility is recorded in the register after checking the legal scope against
    the LOTAÇOR first-sale landings series. Other national/EU stock allocations,
    quarterly limits and accessory-catch limits are deliberately excluded.
    """

    quotas = load_quota_limits(path)
    if quotas.empty or not species or not years:
        return pd.DataFrame(columns=QUOTA_COLUMNS)

    eligible = quotas[
        (quotas["limit_type"] == "Anual")
        & (quotas["verification_status"] == "Verificado")
        & (quotas["chart_eligible"] == "Sim")
        & (quotas["species"].isin(species))
        & (quotas["year"].isin(years))
        & quotas["limit_tonnes"].notna()
    ].copy()
    return eligible.sort_values(["species", "year", "source_level"])


def quota_records_for_species(species, years, path=QUOTA_DATA_PATH):
    """Return annual quota records for context, including non-comparable scopes."""

    quotas = load_quota_limits(path)
    if quotas.empty or not species or not years:
        return pd.DataFrame(columns=QUOTA_COLUMNS)

    return quotas[
        quotas["species"].isin(species)
        & quotas["year"].isin(years)
        & quotas["limit_type"].isin([
            "Anual", "Quota inicial", "Quota inicial com período parcial",
            "TAC atribuído aos Açores (série DRP)",
        ])
    ].copy().sort_values(["species", "year", "source_level"])


def quota_chart_records(species, path=QUOTA_DATA_PATH):
    """Return only verified, chart-approved annual quota records.

    Quarterly limits, accessory-catch limits, partial-period limits and
    national/EU allocations with incompatible scope are never plotted.
    Historical DRP allocations are retained as a distinct series because
    the source explicitly identifies them as allocations attributed to the
    Azores; they must not be combined with Portaria limits.
    """

    quotas = load_quota_limits(path)
    if quotas.empty or not species:
        return pd.DataFrame(columns=QUOTA_COLUMNS)

    allowed_types = [
        "Anual",
        "Quota inicial",
        "TAC atribuído aos Açores (série DRP)",
    ]
    eligible = quotas[
        (quotas["species"] == species)
        & (quotas["verification_status"] == "Verificado")
        & (quotas["chart_eligible"] == "Sim")
        & (quotas["limit_type"].isin(allowed_types))
        & quotas["limit_tonnes"].notna()
        & (quotas["limit_tonnes"] > 0)
    ].copy()
    return eligible.sort_values(["year", "source_level", "stock_code"])


def quota_chart_species(landings_species, path=QUOTA_DATA_PATH):
    """Return landings species with at least one verified chartable quota."""

    quotas = load_quota_limits(path)
    if quotas.empty:
        return []

    chartable = quotas[
        (quotas["verification_status"] == "Verificado")
        & (quotas["chart_eligible"] == "Sim")
        & quotas["limit_type"].isin([
            "Anual", "Quota inicial", "TAC atribuído aos Açores (série DRP)"
        ])
        & quotas["limit_tonnes"].notna()
        & (quotas["limit_tonnes"] > 0)
    ]["species"].dropna().unique()
    return sorted(set(landings_species) & set(chartable))


def annual_landings_for_species(observations, species):
    """Aggregate all available landings by year, without requiring complete years."""

    if observations.empty:
        return pd.DataFrame(columns=["year", "weight_kg", "landings_tonnes"])

    annual = (
        observations[observations["species"] == species]
        .groupby("year", as_index=False)
        .agg(weight_kg=("weight_kg", "sum"))
    )
    annual["landings_tonnes"] = annual["weight_kg"] / 1000
    return annual.sort_values("year")
