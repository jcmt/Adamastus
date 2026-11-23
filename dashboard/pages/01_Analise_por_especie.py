import sys
from pathlib import Path

import numpy as np
import plotly.express as px
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

from analysis.analysis import (
    annual_species_trends, composition_metrics, summarise_species, trend_statistics,
)
from dashboard.common import get_data, select_period, show_data_status

st.set_page_config(page_title="Análise por espécie · Adamastus", page_icon="🐟", layout="wide")
st.title("Análise por espécie")
st.caption("Tendências dos desembarques, composição por espécie e indicadores exploratórios")

df, history = get_data()
filtered, selected_years, downloaded_months, selected_month_keys = select_period(df, history)
show_data_status(downloaded_months, selected_month_keys)
if filtered.empty:
    st.warning("Não existem observações para o período selecionado.")
    st.stop()

# Tendências das espécies
st.header("Tendências das espécies")
successful_years = sorted({
    year for year in selected_years
    if all((year, month) in downloaded_months for month in range(1, 13))
})
if len(successful_years) < 2:
    st.info("Selecione pelo menos dois anos com os 12 meses descarregados com sucesso "
            "para analisar as tendências anuais por espécie.")
else:
    annual = annual_species_trends(df[df["month"].between(1, 12)], successful_years)
    st.subheader("Explorar tendências por espécie")
    species_list = sorted(annual["species"].unique().tolist())
    default_species = annual.groupby("species")["weight_kg"].sum().nlargest(5).index.tolist()
    selected_species = st.multiselect("Espécies", species_list, default=default_species)
    metric = st.radio("Variável", ["Quantidade desembarcada (t)", "Valor económico (mil €)"], horizontal=True)
    column = "weight_kg" if metric == "Quantidade desembarcada (t)" else "value_eur"
    chart_data = annual[annual["species"].isin(selected_species)].copy()
    chart_data["metric_value"] = chart_data[column] / (1000 if column == "weight_kg" else 1000)

    if selected_species:
        fig = px.line(chart_data, x="year", y="metric_value", color="species", markers=True,
                      labels={"year": "Ano", "metric_value": metric, "species": "Espécie"})
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tendências lineares estimadas")
        trends = trend_statistics(annual[annual["species"].isin(selected_species)], column)
        if not trends.empty:
            slope_scale = 1000
            slope_unit = "t/ano" if column == "weight_kg" else "mil €/ano"
            display_trends = trends.copy()
            display_trends["slope_per_year"] = display_trends["slope_per_year"] / slope_scale
            display_trends = display_trends.rename(columns={
                "species": "Espécie", "years": "Anos", "slope_per_year": f"Variação ({slope_unit})",
                "change_percent": "Variação ajustada (%)", "r_squared": "R²",
                "first_year": "Ano inicial", "last_year": "Ano final",
            })
            st.dataframe(display_trends, use_container_width=True, hide_index=True, column_config={
                f"Variação ({slope_unit})": st.column_config.NumberColumn(format="%.2f"),
                "Variação ajustada (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "R²": st.column_config.NumberColumn(format="%.3f"),
            })
        else:
            st.info("São necessários pelo menos quatro anos completos para calcular as estatísticas de tendência.")
    else:
        st.info("Selecione espécies para comparar.")

    st.caption(
        "Estas tendências dizem respeito aos desembarques registados, não constituindo estimativas "
        "da abundância, biomassa ou mortalidade por pesca. A variação percentual ajustada é descritiva "
        "e pode ser sensível ao número de anos considerado."
    )

st.divider()

# Indicadores de composição
st.header("Indicadores de composição")
st.caption("Indicadores exploratórios da composição dos desembarques")
summary = summarise_species(filtered)
composition = composition_metrics(summary)
c1, c2, c3 = st.columns(3)
c1.metric("Peso das cinco principais espécies", f"{composition['top5_share']:.1%}" if np.isfinite(composition["top5_share"]) else "—")
c2.metric("Índice HHI", f"{composition['hhi']:.3f}" if np.isfinite(composition["hhi"]) else "—")
c3.metric("Número efetivo de espécies", f"{composition['effective_species']:.1f}" if np.isfinite(composition["effective_species"]) else "—")
st.write(
    "O Índice Herfindahl–Hirschman (HHI) corresponde à soma dos quadrados das proporções "
    "de cada espécie. Um valor mais elevado indica maior concentração dos desembarques num "
    "número reduzido de espécies. Descreve a composição da pesca, não a biodiversidade "
    "ecológica nem o estado dos stocks."
)

share_data = summary.nlargest(12, "weight_kg").copy()
share_data["share"] = share_data["weight_kg"] / summary["weight_kg"].sum()
fig = px.bar(share_data.sort_values("share"), x="share", y="species", orientation="h",
             labels={"share": "Proporção do peso desembarcado", "species": "Espécie"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Espécies com tendências decrescentes ou crescentes nos desembarques")
full_years = sorted([
    year for year in selected_years
    if all((year, month) in downloaded_months for month in range(1, 13))
])
if len(full_years) < 4:
    st.info("São necessários pelo menos quatro anos completos para estimar tendências lineares exploratórias.")
else:
    annual_composition_trends = annual_species_trends(df, full_years)
    trends = trend_statistics(annual_composition_trends)
    if trends.empty:
        st.info("Não existem registos suficientes para estimar tendências por espécie.")
    else:
        st.caption("Ordenação pela inclinação da reta ajustada (t/ano). Uma tendência decrescente "
                   "é um sinal para investigação, não uma prova de declínio do stock.")
        declining = trends.nsmallest(10, "slope_per_year")
        increasing = trends.nlargest(10, "slope_per_year")
        left, right = st.columns(2)
        with left:
            st.markdown("**Tendências negativas mais acentuadas**")
            declining_display = declining.assign(slope_tonnes=declining["slope_per_year"] / 1000)
            fig = px.bar(declining_display.sort_values("slope_tonnes"), x="slope_tonnes", y="species",
                         orientation="h", labels={"slope_tonnes": "Inclinação (t/ano)", "species": "Espécie"})
            st.plotly_chart(fig, use_container_width=True)
        with right:
            st.markdown("**Tendências positivas mais acentuadas**")
            increasing_display = increasing.assign(slope_tonnes=increasing["slope_per_year"] / 1000)
            fig = px.bar(increasing_display.sort_values("slope_tonnes"), x="slope_tonnes", y="species",
                         orientation="h", labels={"slope_tonnes": "Inclinação (t/ano)", "species": "Espécie"})
            st.plotly_chart(fig, use_container_width=True)
        with st.expander("Estatísticas completas das tendências"):
            display_trends = trends.copy()
            display_trends["slope_per_year"] = display_trends["slope_per_year"] / 1000
            display_trends = display_trends.rename(columns={
                "species": "Espécie", "years": "Anos", "slope_per_year": "Variação (t/ano)",
                "change_percent": "Variação ajustada (%)", "r_squared": "R²",
                "first_year": "Ano inicial", "last_year": "Ano final",
            })
            st.dataframe(display_trends, use_container_width=True, hide_index=True, column_config={
                "Variação (t/ano)": st.column_config.NumberColumn(format="%.2f"),
                "Variação ajustada (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "R²": st.column_config.NumberColumn(format="%.3f"),
            })

st.divider()
st.subheader("Como são calculados os indicadores")
st.markdown(
    r"""
    **Proporção das cinco principais espécies**

    Soma das proporções do peso desembarcado correspondente às cinco espécies com maior
    quantidade no período selecionado, relativamente ao peso total desembarcado.

    **Índice Herfindahl–Hirschman (HHI)**

    Soma dos quadrados das proporções de cada espécie no peso total:
    \\(HHI = \sum_i s_i^2\\), em que \\(s_i\\) é a proporção do peso atribuída à espécie \\(i\\).
    Quanto maior o índice, maior a concentração dos desembarques.

    **Número efetivo de espécies**

    Inverso do HHI: \\(N_{efetivo} = 1 / HHI\\). Corresponde ao número de espécies
    igualmente representadas que produziria a mesma concentração.

    **Tendência linear dos desembarques por espécie**

    Para cada espécie, ajusta-se uma regressão linear por mínimos quadrados ordinários
    aos totais anuais (kg) dos anos completos selecionados. A inclinação é apresentada
    em toneladas por ano nos gráficos e tabelas. São exigidos pelo menos quatro anos completos.

    **Nota de interpretação**

    Estes indicadores descrevem a composição e a evolução dos desembarques registados.
    Não medem diretamente a abundância dos stocks nem a mortalidade por pesca. As
    alterações podem também refletir esforço de pesca, regras de gestão, condições de
    mercado ou diferenças no registo dos dados.
    """
)
