import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from analysis.analysis import prepare_observations
from dashboard.common import MONTH_NAMES
from lotacor.database import initialise_database, load_observations, load_download_history

st.set_page_config(page_title="Desembarques por ilha · Adamastus", page_icon="🏝️", layout="wide")
st.title("Desembarques por ilha")
st.caption("LOTAÇOR · Descargas por Ilha (DPI) · Quantidade, valor económico e preço médio")


@st.cache_data(ttl=60)
def get_island_data():
    initialise_database()
    observations = prepare_observations(load_observations())
    history = load_download_history()
    return observations[observations["query_type"] == "DPI"].copy(), history


df, history = get_island_data()
if not history.empty:
    history = history.copy()
    history["period_start"] = pd.to_datetime(history["period_start"])
    history["year"] = history["period_start"].dt.year
    history["month"] = history["period_start"].dt.month
if df.empty:
    st.warning("Ainda não existem dados por ilha. Execute `uv run python main.py` para obter o relatório DPI.")
    st.stop()

if "island" not in df or df["island"].fillna("").eq("").all():
    st.error("Os registos DPI não contêm o nome da ilha. Verifique a resposta da API antes de interpretar esta página.")
    st.stop()

df = df[df["island"].fillna("").ne("")].copy()
years = sorted(df["year"].dropna().astype(int).unique())
with st.sidebar:
    st.header("Desembarques por ilha")
    selected_years = st.multiselect("Anos", years, default=years)
    selected_months = st.select_slider("Meses", options=list(range(1, 13)), value=(1, 12),
                                       format_func=lambda month: MONTH_NAMES[month])

if not selected_years:
    st.info("Selecione pelo menos um ano.")
    st.stop()

first_month, last_month = selected_months
filtered = df[df["year"].isin(selected_years) & df["month"].between(first_month, last_month)].copy()
if filtered.empty:
    st.warning("Não existem registos por ilha para o período selecionado.")
    st.stop()

successful_history = history[
    (history["query_type"] == "DPI") & (history["lota_id"] == "all") &
    (history["ilha_id"] == "all") & (history["fao"] == "all") &
    (history["status"] == "success")
] if not history.empty else history
successful_months = {
    (int(row.year), int(row.month))
    for row in successful_history[["year", "month"]].drop_duplicates().itertuples(index=False)
} if not successful_history.empty else set()
selected_month_keys = {
    (year, month)
    for year in selected_years
    for month in range(first_month, last_month + 1)
}
missing_months = selected_month_keys - successful_months
if missing_months:
    st.warning(
        f"Faltam registos de descarregamento DPI para {len(missing_months)} mês(es) do período selecionado. "
        "Os totais por ilha podem estar incompletos."
    )
else:
    st.caption("Todos os meses do período selecionado têm pedidos DPI concluídos com sucesso.")

summary = filtered.groupby("island", as_index=False).agg(
    weight_kg=("weight_kg", "sum"), value_eur=("value_eur", "sum")
)
summary["weight_tonnes"] = summary["weight_kg"] / 1000
summary["value_thousand_eur"] = summary["value_eur"] / 1000
summary["average_price_eur_kg"] = summary["value_eur"] / summary["weight_kg"]
summary["weight_share"] = summary["weight_kg"] / summary["weight_kg"].sum() * 100
summary["value_share"] = summary["value_eur"] / summary["value_eur"].sum() * 100

st.subheader("Distribuição por ilha")
with st.expander("Como são calculados estes valores?"):
    st.markdown(
        """
        - **Quantidade por ilha:** soma do peso dos registos associados a cada ilha, convertida
          de kg para toneladas (t).
        - **Valor económico por ilha:** soma do valor dos registos associados a cada ilha,
          apresentado em milhares de euros (mil €) nos gráficos e na tabela.
        - **Preço médio por ilha:** valor económico total dividido pela quantidade total
          desembarcada nessa ilha (€/kg). É uma média ponderada pelo peso, não a média simples
          dos preços médios de cada registo.
        - **Percentagem da quantidade:** quantidade de cada ilha dividida pela quantidade total
          das ilhas no período, apresentada em percentagem.
        - **Percentagem do valor:** valor de cada ilha dividido pelo valor total das ilhas,
          apresentado em percentagem.

        Os valores respeitam os filtros de ano e mês selecionados.
        """
    )

left, right = st.columns(2)
with left:
    st.markdown("**Quantidade desembarcada por ilha**")
    quantity = summary.sort_values("weight_tonnes")
    st.plotly_chart(px.bar(quantity, x="weight_tonnes", y="island", orientation="h",
                           labels={"weight_tonnes": "Quantidade desembarcada (t)", "island": "Ilha"}),
                    use_container_width=True)
with right:
    st.markdown("**Valor económico por ilha**")
    value = summary.sort_values("value_thousand_eur")
    st.plotly_chart(px.bar(value, x="value_thousand_eur", y="island", orientation="h",
                           labels={"value_thousand_eur": "Valor económico (mil €)", "island": "Ilha"}),
                    use_container_width=True)


st.markdown("**Preço médio por ilha**")
price = summary.sort_values("average_price_eur_kg")
st.plotly_chart(px.bar(price, x="average_price_eur_kg", y="island", orientation="h",
                       labels={"average_price_eur_kg": "Preço médio (€/kg)", "island": "Ilha"}),
                use_container_width=True)

st.subheader("Peso relativo de cada ilha")
shares = summary.melt(id_vars="island", value_vars=["weight_share", "value_share"],
                      var_name="measure", value_name="share")
shares["measure"] = shares["measure"].map({"weight_share": "Quantidade", "value_share": "Valor"})
share_fig = px.bar(shares, x="island", y="share", color="measure", barmode="group",
                   labels={"island": "Ilha", "share": "Percentagem do total regional (%)", "measure": "Indicador"})
share_fig.update_yaxes(ticksuffix="%")
st.plotly_chart(share_fig, use_container_width=True)

st.subheader("Evolução temporal")
monthly = filtered.groupby(["period", "island"], as_index=False).agg(
    weight_kg=("weight_kg", "sum"), value_eur=("value_eur", "sum")
)
measure = st.radio("Indicador mensal", ["Quantidade (t)", "Valor económico (mil €)"], horizontal=True)
if measure == "Quantidade (t)":
    monthly["metric"] = monthly["weight_kg"] / 1000
    y_label = "Quantidade desembarcada (t)"
else:
    monthly["metric"] = monthly["value_eur"] / 1000
    y_label = "Valor económico (mil €)"
st.plotly_chart(px.line(monthly, x="period", y="metric", color="island", markers=False,
                        labels={"period": "Mês", "metric": y_label, "island": "Ilha"}),
                use_container_width=True)

st.subheader("Análise de uma ilha")
selected_island = st.selectbox("Selecionar ilha", sorted(summary["island"].unique()))
island_monthly = monthly[monthly["island"] == selected_island].sort_values("period")
c1, c2 = st.columns(2)
selected_summary = summary[summary["island"] == selected_island].iloc[0]
c1.metric(f"{selected_island} · quantidade desembarcada", f"{selected_summary['weight_tonnes']:,.1f} t")
c2.metric(f"{selected_island} · valor económico", f"€{selected_summary['value_eur'] / 1000:,.1f} mil")
island_monthly["weight_tonnes"] = island_monthly["weight_kg"] / 1000
island_monthly["value_thousand_eur"] = island_monthly["value_eur"] / 1000
st.plotly_chart(px.line(island_monthly, x="period", y="weight_tonnes", markers=True,
                        labels={"period": "Mês", "weight_tonnes": "Quantidade desembarcada (t)"}),
                use_container_width=True)
st.plotly_chart(px.line(island_monthly, x="period", y="value_thousand_eur", markers=True,
                        labels={"period": "Mês", "value_thousand_eur": "Valor económico (mil €)"}),
                use_container_width=True)


st.subheader("Principais espécies por ilha")
st.caption(
    "As cinco espécies com maior quantidade desembarcada e as cinco com maior valor económico "
    "são identificadas separadamente para cada ilha, respeitando os filtros de ano e mês."
)

with st.expander("Como é feita a seleção das principais espécies?"):
    st.markdown(
        """
        Para cada ilha, as espécies são ordenadas de forma independente:
        - **Por quantidade:** as cinco espécies com maior peso total desembarcado (t).
        - **Por valor económico:** as cinco espécies com maior valor total (mil €).

        Uma espécie pode surgir num dos gráficos e não no outro, porque a classificação é feita
        separadamente. Os valores correspondem ao período selecionado.
        """
    )

island_tabs = st.tabs(sorted(filtered["island"].unique()))
for island_tab, island_name in zip(island_tabs, sorted(filtered["island"].unique())):
    with island_tab:
        island_species = filtered[filtered["island"] == island_name].groupby(
            "species", as_index=False
        ).agg(weight_kg=("weight_kg", "sum"), value_eur=("value_eur", "sum"))
        island_species["weight_tonnes"] = island_species["weight_kg"] / 1000
        island_species["value_thousand_eur"] = island_species["value_eur"] / 1000

        top_weight = island_species.nlargest(5, "weight_tonnes").sort_values("weight_tonnes")
        top_value = island_species.nlargest(5, "value_thousand_eur").sort_values("value_thousand_eur")

        quantity_col, value_col = st.columns(2)
        with quantity_col:
            st.markdown("**Cinco principais · Quantidade desembarcada**")
            st.plotly_chart(
                px.bar(
                    top_weight, x="weight_tonnes", y="species", orientation="h",
                    labels={"weight_tonnes": "Quantidade desembarcada (t)", "species": "Espécie"},
                ),
                use_container_width=True,
            )
        with value_col:
            st.markdown("**Cinco principais · Valor económico**")
            st.plotly_chart(
                px.bar(
                    top_value, x="value_thousand_eur", y="species", orientation="h",
                    labels={"value_thousand_eur": "Valor económico (mil €)", "species": "Espécie"},
                ),
                use_container_width=True,
            )


st.subheader("Tabela-resumo por ilha")
st.dataframe(summary[["island", "weight_tonnes", "value_thousand_eur", "average_price_eur_kg", "weight_share", "value_share"]].sort_values(
    "weight_tonnes", ascending=False).rename(columns={"island": "Ilha", "weight_tonnes": "Quantidade (t)",
    "value_thousand_eur": "Valor (mil €)", "average_price_eur_kg": "Preço médio (€/kg)",
    "weight_share": "Percentagem da quantidade", "value_share": "Percentagem do valor"}),
    use_container_width=True, hide_index=True, column_config={
        "Percentagem da quantidade": st.column_config.NumberColumn(format="%.1f%%"),
        "Percentagem do valor": st.column_config.NumberColumn(format="%.1f%%"),
    })

st.info("Os dados provêm do relatório DPI da LOTAÇOR. A ilha identifica a atribuição do desembarque e não necessariamente o local geográfico da captura.")
