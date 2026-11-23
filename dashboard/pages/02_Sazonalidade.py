import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

from analysis.analysis import seasonal_concentration, species_seasonality
from dashboard.common import MONTH_NAMES, get_data, select_period, show_data_status

st.set_page_config(page_title="Sazonalidade · Adamastus", page_icon="📅", layout="wide")
st.title("Sazonalidade")
st.caption("Variação dos desembarques ao longo do ano")

df, history = get_data()
filtered, selected_years, downloaded_months, selected_month_keys = select_period(df, history)
show_data_status(downloaded_months, selected_month_keys)
if filtered.empty:
    st.warning("Não existem observações para esta seleção.")
    st.stop()

st.subheader("Padrão sazonal global")
monthly = seasonal_concentration(filtered)
monthly["weight_tonnes"] = monthly["weight_kg"] / 1000
monthly["month_name"] = monthly["month"].map(MONTH_NAMES)
fig = px.bar(monthly, x="month_name", y="weight_tonnes",
             category_orders={"month_name": list(MONTH_NAMES.values())},
             labels={"month_name": "Mês", "weight_tonnes": "Desembarques (t)"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Comparação dos padrões sazonais entre anos")
yearly_monthly = filtered.groupby(["year", "month"], as_index=False)["weight_kg"].sum()
yearly_monthly["weight_tonnes"] = yearly_monthly["weight_kg"] / 1000
yearly_monthly["month_name"] = yearly_monthly["month"].map(MONTH_NAMES)
fig = px.line(yearly_monthly, x="month_name", y="weight_tonnes", color="year", markers=True,
              category_orders={"month_name": list(MONTH_NAMES.values())},
              labels={"month_name": "Mês", "weight_tonnes": "Desembarques (t)", "year": "Ano"})
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Sazonalidade por espécie")
species = sorted(filtered["species"].dropna().unique().tolist())
selected_species = st.multiselect("Espécies a comparar", species, default=[])
if selected_species:
    seasonal = species_seasonality(filtered, selected_species)
    seasonal["mean_weight_tonnes"] = seasonal["mean_weight_kg"] / 1000
    seasonal["month_name"] = seasonal["month"].map(MONTH_NAMES)
    fig = px.line(seasonal, x="month_name", y="mean_weight_tonnes", color="species", markers=True,
                  category_orders={"month_name": list(MONTH_NAMES.values())},
                  labels={"month_name": "Mês", "mean_weight_tonnes": "Desembarques médios (t)", "species": "Espécie"})
    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "A sazonalidade reflete os desembarques registados. Pode ser influenciada pelos períodos de "
    "reprodução, pelas condições meteorológicas, pela acessibilidade, pelas práticas de pesca, "
    "pela regulamentação e pela procura do mercado."
)
