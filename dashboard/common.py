import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from analysis.analysis import prepare_observations
from lotacor.database import initialise_database, load_download_history, load_observations


MONTH_NAMES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}


@st.cache_data(ttl=60)
def get_data():
    initialise_database()
    observations = prepare_observations(load_observations())
    observations = observations[observations["query_type"] == "DNA"].copy()
    history = load_download_history()
    if not history.empty:
        history["period_start"] = pd.to_datetime(history["period_start"])
        history["year"] = history["period_start"].dt.year
        history["month"] = history["period_start"].dt.month
    return observations, history


def select_period(df, history, page_label="Período"):
    """Apply shared year and month filters and return data plus coverage metadata."""

    if df.empty:
        return df, [], set(), set()

    years = sorted(df["year"].dropna().astype(int).unique().tolist())
    successful = history[history["status"] == "success"].copy() if not history.empty else history
    if not successful.empty:
        successful = successful[
            (successful["query_type"] == "DNA") &
            (successful["lota_id"] == "all") &
            (successful["ilha_id"] == "all") &
            (successful["fao"] == "all")
        ]

    downloaded_months = set()
    if not successful.empty:
        downloaded_months = {
            (int(row.year), int(row.month))
            for row in successful[["year", "month"]].drop_duplicates().itertuples(index=False)
        }

    complete_years = [
        year for year in years
        if year < pd.Timestamp.today().year and all((year, month) in downloaded_months for month in range(1, 13))
    ]
    default_years = complete_years if complete_years else years

    with st.sidebar:
        st.header(page_label)
        selected_years = st.multiselect("Anos", years, default=default_years, key=f"{page_label}_years")
        selected_months = st.select_slider(
            "Meses", options=list(MONTH_NAMES), value=(1, 12),
            format_func=lambda month: MONTH_NAMES[month], key=f"{page_label}_months",
        )
        st.caption("Selecione anos completos ou um intervalo de meses nos anos escolhidos.")

    if not selected_years:
        st.info("Selecione pelo menos um ano.")
        st.stop()

    first_month, last_month = selected_months
    filtered = df[
        df["year"].isin(selected_years) & df["month"].between(first_month, last_month)
    ].copy()
    selected_month_keys = {
        (year, month)
        for year in selected_years
        for month in range(first_month, last_month + 1)
    }
    return filtered, selected_years, downloaded_months, selected_month_keys


def show_data_status(downloaded_months, selected_month_keys):
    missing = sorted(selected_month_keys - downloaded_months)
    if missing:
        st.warning(
            f"Faltam registos no histórico de descarregamento para {len(missing)} mês(es) selecionado(s). "
            "As tendências e as comparações mensais com preenchimento de zeros devem ser interpretadas com precaução."
        )
    else:
        st.success("Verificação concluída: todos os meses selecionados têm registos de descarregamento bem-sucedidos.")
