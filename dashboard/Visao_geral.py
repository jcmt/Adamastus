import sys
from pathlib import Path
from textwrap import dedent

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from analysis.analysis import annual_diversity_metrics, composition_metrics, summarise_species
from dashboard.common import MONTH_NAMES, get_data, select_period, show_data_status

st.set_page_config(page_title="Visão geral · Adamastus", page_icon="🐟", layout="wide")
st.title("Adamastus")
st.caption("Dados e análise das pescas dos Açores · com base nos dados disponibilizados pela LOTAÇOR")

df, history = get_data()
if df.empty:
    st.warning("Não existem observações regionais. Descarregue primeiro os dados através de main.py.")
    st.stop()

successful = history[history["status"] == "success"].copy() if not history.empty else history
if not successful.empty:
    successful = successful[
        (successful["query_type"] == "DNA") & (successful["lota_id"] == "all") &
        (successful["ilha_id"] == "all") & (successful["fao"] == "all")
    ]
    successful_months = set(zip(successful["year"].astype(int), successful["month"].astype(int)))
else:
    successful_months = set()

available_years = sorted(df["year"].dropna().astype(int).unique())
complete_years = [year for year in available_years
                  if all((year, month) in successful_months for month in range(1, 13))]
annual = df[df["year"].isin(complete_years)].groupby("year", as_index=False).agg(
    weight_kg=("weight_kg", "sum"), value_eur=("value_eur", "sum")
)
annual["weighted_price_eur_kg"] = annual["value_eur"] / annual["weight_kg"].replace(0, np.nan)

latest_year = int(df["year"].max())
latest = df[df["year"] == latest_year]
latest_weight = latest["weight_kg"].sum()
latest_value = latest["value_eur"].sum()
latest_price = latest_value / latest_weight if latest_weight else np.nan
latest_months = sorted(latest["month"].dropna().astype(int).unique())
month_label = ", ".join(MONTH_NAMES[month] for month in latest_months)

st.subheader("Evolução a longo prazo")
if annual.empty:
    st.warning("Ainda não existem anos civis completos. As médias e tendências de longo prazo "
               "serão apresentadas quando os 12 meses de pelo menos um ano tiverem sido "
               "descarregados com sucesso.")
else:
    mean_landings = annual["weight_kg"].mean()
    mean_value = annual["value_eur"].mean()
    pooled_weight = annual["weight_kg"].sum()
    pooled_value = annual["value_eur"].sum()
    pooled_price = pooled_value / pooled_weight if pooled_weight else np.nan
    metrics = st.columns(3, gap="large")
    metrics[0].metric("Desembarques médios anuais", f"{mean_landings / 1_000_000:,.2f} kt")
    metrics[1].metric("Valor económico médio anual", f"€{mean_value / 1_000_000:,.2f}m")
    metrics[2].metric("Preço médio ponderado", f"€{pooled_price:,.2f}/kg" if pd.notna(pooled_price) else "—")
    st.caption(
        f"Anos completos: {', '.join(map(str, complete_years))}. "
        "As médias anuais são médias aritméticas; o preço ponderado é calculado "
        "pela divisão do valor total acumulado pelo peso total acumulado."
    )

st.divider()
st.subheader(f"{latest_year} · último ano com dados disponíveis")
st.caption(
    f"Valores acumulados no ano, com base nos desembarques registados para {month_label or 'nenhum mês'}. "
    "Este ano não é incluído nas médias de longo prazo, a menos que esteja completo."
)
latest_metrics = st.columns(3, gap="large")
latest_metrics[0].metric("Desembarques acumulados", f"{latest_weight / 1_000_000:,.2f} kt")
latest_metrics[1].metric("Valor económico acumulado", f"€{latest_value / 1_000_000:,.2f}m")
latest_metrics[2].metric("Preço médio ponderado acumulado", f"€{latest_price:,.2f}/kg" if pd.notna(latest_price) else "—")

if not annual.empty:
    st.divider()
    st.subheader("Tendências de longo prazo")
    specs = [("weight_kg", "Desembarques", "t/ano", 1000, 1),
             ("value_eur", "Valor económico", "mil €/ano", 1000, 1),
             ("weighted_price_eur_kg", "Preço médio ponderado", "€/kg/ano", 1, 2)]
    trend_cols = st.columns(3, gap="large")
    for col, (field, label, unit, scale, precision) in zip(trend_cols, specs):
        slope = np.polyfit(annual["year"], annual[field], 1)[0] / scale if len(annual) >= 2 else np.nan
        value = f"{slope:+,.{precision}f} {unit}" if pd.notna(slope) else "Anos insuficientes"
        col.metric(label, value, help="Tendência linear ajustada apenas aos anos civis completos.")
    st.caption(
        "As tendências lineares descrevem alterações nos desembarques e no valor registados. "
        "Não são medidas diretas da abundância dos stocks nem da mortalidade por pesca."
    )

    st.subheader("Séries anuais")
    chart_cols = st.columns(3, gap="medium")
    charts = [("weight_kg", "Desembarques", "Desembarques (toneladas)", 1000),
              ("value_eur", "Valor económico", "Valor económico (milhões de €)", 1_000_000),
              ("weighted_price_eur_kg", "Preço médio ponderado", "Preço (€/kg)", 1)]
    for col, (field, title, axis_title, divisor) in zip(chart_cols, charts):
        series = annual[field] / divisor
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=annual["year"], y=series, mode="lines+markers", name=title,
                                 line=dict(width=2), marker=dict(size=6)))
        if len(annual) >= 2:
            x = annual["year"].to_numpy(dtype=float)
            slope, intercept = np.polyfit(x, series.to_numpy(dtype=float), 1)
            fig.add_trace(go.Scatter(x=x, y=slope * x + intercept, mode="lines", name="Tendência linear",
                                     line=dict(dash="dash", width=1.5)))
        fig.update_layout(title=title, height=300, margin=dict(l=8, r=8, t=45, b=8),
                          xaxis_title=None, yaxis_title=axis_title, hovermode="x unified",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
        col.plotly_chart(fig, use_container_width=True)

st.divider()
with st.expander("Composição por espécie e análise detalhada", expanded=False):
    filtered, selected_years, downloaded_months, selected_month_keys = select_period(df, history, "Análise detalhada")
    if not filtered.empty:
        show_data_status(downloaded_months, selected_month_keys)
        summary = summarise_species(filtered)
        composition = composition_metrics(summary)
        c1, c2, c3 = st.columns(3)
        c1.metric("Peso das cinco principais espécies", f"{composition['top5_share']:.1%}" if pd.notna(composition['top5_share']) else "—")
        c2.metric("Concentração por espécie (HHI)", f"{composition['hhi']:.3f}" if pd.notna(composition['hhi']) else "—")
        c3.metric("Número efetivo de espécies", f"{composition['effective_species']:.1f}" if pd.notna(composition['effective_species']) else "—")
        summary_table = summary.copy()
        summary_table["weight_tonnes"] = summary_table["weight_kg"] / 1000
        summary_table["value_million_eur"] = summary_table["value_eur"] / 1_000_000
        summary_table = summary_table.rename(columns={
            "species": "Espécie", "weight_tonnes": "Quantidade (t)",
            "value_million_eur": "Valor (milhões €)", "average_price_eur": "Preço médio (€/kg)",
        })
        st.dataframe(
            summary_table[["Espécie", "Quantidade (t)", "Valor (milhões €)", "Preço médio (€/kg)"]],
            use_container_width=True, hide_index=True,
            column_config={
                "Quantidade (t)": st.column_config.NumberColumn(format="%.1f"),
                "Valor (milhões €)": st.column_config.NumberColumn(format="€%.3f"),
                "Preço médio (€/kg)": st.column_config.NumberColumn(format="€%.2f"),
            },
        )
    else:
        st.info("Não existem observações para o período selecionado.")

st.divider()
st.subheader("Diversidade e composição das espécies")
st.caption(
    "Indicadores anuais calculados a partir da proporção do peso desembarcado por espécie. "
    "São apresentados apenas anos civis completos, para garantir comparabilidade temporal."
)

if annual.empty:
    st.info("Os indicadores serão apresentados quando existirem anos civis completos.")
else:
    diversity = annual_diversity_metrics(df, complete_years)
    if diversity.empty:
        st.info("Não existem dados de peso válidos para calcular os indicadores de composição.")
    else:
        latest_diversity = diversity.iloc[-1]
        dominant_share = latest_diversity["dominant_species_share"]
        diversity_metrics = st.columns(4, gap="medium")
        diversity_metrics[0].metric(
            "Riqueza de espécies", f"{latest_diversity['species_richness']:,}",
            help="Número de espécies com peso desembarcado superior a zero no ano.",
        )
        diversity_metrics[1].metric(
            "Diversidade de Shannon (H′)", f"{latest_diversity['shannon_diversity']:.2f}",
            help="Índice calculado com a proporção do peso total correspondente a cada espécie.",
        )
        evenness = latest_diversity["pielou_evenness"]
        diversity_metrics[2].metric(
            "Equitabilidade de Pielou (J′)", f"{evenness:.2f}" if pd.notna(evenness) else "—",
            help="Varia entre 0 e 1; valores mais elevados indicam uma distribuição mais uniforme do peso.",
        )
        diversity_metrics[3].metric(
            "Dominância da espécie principal",
            f"{dominant_share:.1%}" if pd.notna(dominant_share) else "—",
            help=f"Proporção do peso total correspondente a {latest_diversity['dominant_species']}.",
        )
        st.caption(
            f"Último ano completo: {int(latest_diversity['year'])}. "
            f"Espécie com maior peso desembarcado: {latest_diversity['dominant_species']}."
        )

        chart_specs = [
            ("species_richness", "Riqueza de espécies", "Número de espécies", ".0f"),
            ("shannon_diversity", "Diversidade de Shannon (H′)", "Índice H′", ".2f"),
            ("pielou_evenness", "Equitabilidade de Pielou (J′)", "Índice J′", ".2f"),
            ("dominant_species_share", "Dominância da espécie principal", "Proporção do peso total", ".0%"),
        ]
        for row_start in (0, 2):
            chart_cols = st.columns(2, gap="medium")
            for col, (field, title, axis_title, value_format) in zip(
                chart_cols, chart_specs[row_start:row_start + 2]
            ):
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=diversity["year"], y=diversity[field], mode="lines+markers",
                    name=title, line=dict(width=2), marker=dict(size=6),
                ))
                fig.update_layout(
                    title=title, height=290, margin=dict(l=8, r=8, t=45, b=8),
                    xaxis_title=None, yaxis_title=axis_title, hovermode="x unified",
                )
                fig.update_yaxes(tickformat=value_format)
                col.plotly_chart(fig, use_container_width=True)

with st.expander("Como são calculados estes indicadores", expanded=False):
    st.markdown(
        dedent(r"""
        Os cálculos utilizam o peso desembarcado por espécie em cada ano civil completo.
        A proporção de cada espécie é o seu peso desembarcado dividido pelo peso total
        desembarcado nesse ano. Apenas espécies com peso superior a zero são incluídas.

        - **Riqueza de espécies (S):** número de espécies com desembarques registados.

        - **Diversidade de Shannon (H′):** \(H' = -\sum_{i=1}^{S} p_i \ln(p_i)\),
          em que \(p_i\) é a proporção do peso total atribuída à espécie \(i\).
          O índice aumenta com a riqueza e com uma distribuição mais uniforme do peso.

        - **Equitabilidade de Pielou (J′):** \(J' = H'/\ln(S)\). Varia entre 0 e 1;
          valores próximos de 1 indicam pesos mais uniformemente distribuídos pelas espécies.
          Para apenas uma espécie, o índice não está definido.

        - **Dominância da espécie principal:** proporção do peso total correspondente à
          espécie com maior peso desembarcado.

        Os indicadores descrevem a **composição dos desembarques**. Não medem diretamente
        a biodiversidade do ecossistema, a abundância dos stocks ou a pressão de pesca.
        Os desembarques também dependem do esforço de pesca, da regulamentação, das
        condições de mercado e dos registos disponíveis.
        """)
    )

st.caption(
    "Os desembarques correspondem às capturas registadas quando são trazidas para terra. "
    "São influenciados pelo esforço de pesca, pela regulamentação, pelas condições de mercado "
    "e pelo processo de registo, não constituindo uma medida direta da abundância dos stocks."
)
st.info("Explore as páginas Análise por espécie, Sazonalidade, Desembarques por ilha e Cobertura dos dados.")
