import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from analysis.quotas import (
    annual_landings_for_species,
    load_quota_events,
    load_quota_limits,
    quota_chart_records,
    quota_source_colours,
    quota_chart_species,
)
from dashboard.common import get_data

st.set_page_config(page_title="Quotas · Adamastus", page_icon="🐟", layout="wide")
st.title("Quotas")
st.caption(
    "Desembarques registados pela LOTAÇOR e limites de captura publicados pelas entidades oficiais"
)

df, history = get_data()
if df.empty:
    st.warning("Não existem observações regionais. Descarregue primeiro os dados através de main.py.")
    st.stop()

quota_limits = load_quota_limits()
quota_events = load_quota_events()

# The chart deliberately includes every year with landings, including incomplete years.
# Only offer species with at least one verified, scope-compatible annual
# quota/allocation record. Species with no chartable quota stay out of this page.
species_list = quota_chart_species(df["species"].dropna().unique())
if not species_list:
    st.info("Não existem espécies com desembarques no conjunto de dados.")
    st.stop()

selected_species = st.selectbox("Espécie", species_list)
species_landings = annual_landings_for_species(df, selected_species)
species_quotas = quota_chart_records(selected_species)

fig = go.Figure()
fig.add_trace(go.Bar(
    x=species_landings["year"],
    y=species_landings["landings_tonnes"],
    name="Desembarques LOTAÇOR",
    marker_color="#70BFFF",
    customdata=species_landings[["weight_kg"]],
    hovertemplate="Ano: %{x}<br>Desembarques: %{y:,.2f} t<extra></extra>",
))

source_colours = quota_source_colours()
if not species_quotas.empty:
    # Keep distinct stock codes/limit types separate rather than silently adding
    # different stocks or management regimes together.
    def quota_series_label(row):
        if row["stock_code"] == "DRP-AZORES-TAC":
            detail = "TAC histórico atribuído aos Açores (DRP)"
        elif row["stock_code"] == "PORTARIA-92-2019":
            detail = "Limite regional — Portaria 92/2019"
        elif row["stock_code"] == "PORTARIA-92-2019-ACESSORIA":
            detail = "Captura acessória — Portaria 92/2019"
        else:
            detail = row["stock_code"] or row["limit_type"]
        return row["source_level"] + " — " + str(detail)

    species_quotas["chart_series"] = species_quotas.apply(quota_series_label, axis=1)
    for series_name, records in species_quotas.groupby("chart_series", sort=True):
        source_level = records["source_level"].iloc[0]
        fig.add_trace(go.Bar(
            x=records["year"].astype(int),
            y=records["limit_tonnes"],
            name=series_name,
            marker_color=source_colours.get(source_level, "#888888"),
            customdata=records[["source_name", "source_url", "period", "fleet_scope"]].to_numpy(),
            hovertemplate=(
                "Ano: %{x}<br>Limite: %{y:,.2f} t"
                "<br>Fonte: %{customdata[0]}"
                "<br>Período: %{customdata[2]}"
                "<br>Frota: %{customdata[3]}<extra></extra>"
            ),
        ))

fig.update_layout(
    barmode="group",
    height=520,
    hovermode="x unified",
    xaxis_title="Ano",
    yaxis_title="Toneladas",
    legend_title="Série",
    margin=dict(l=10, r=10, t=25, b=10),
)
fig.update_xaxes(dtick=1)
st.plotly_chart(fig, use_container_width=True)

# Coverage is descriptive: partial-year landings are shown as recorded, not annualised.
if not history.empty:
    successful = history[
        (history["status"] == "success")
        & (history["query_type"] == "DNA")
        & (history["lota_id"] == "all")
        & (history["ilha_id"] == "all")
        & (history["fao"] == "all")
    ].copy()
    successful["period_start"] = pd.to_datetime(successful["period_start"])
    successful["year"] = successful["period_start"].dt.year
    successful["month"] = successful["period_start"].dt.month
    months_by_year = successful.groupby("year")["month"].nunique().to_dict()
    partial_years = [
        int(year) for year in species_landings["year"].unique()
        if months_by_year.get(int(year), 0) < 12
    ]
    if partial_years:
        st.warning(
            "Os desembarques podem estar incompletos nos seguintes anos: "
            + ", ".join(map(str, sorted(partial_years)))
            + ". São apresentados apenas os registos disponíveis; não são anualizados."
        )
else:
    st.warning(
        "Não existe histórico de descarregamentos suficiente para confirmar a cobertura mensal. "
        "Os totais anuais devem ser interpretados com precaução."
    )

if species_quotas.empty:
    st.info(
        "Não existem limites anuais verificados no registo para esta espécie. "
        "Consulte a tabela de enquadramento abaixo para verificar se existem outros tipos de limite."
    )
else:
    st.caption(
        "As barras distinguem os limites legais regionais, a série histórica de TAC atribuídos "
        "aos Açores pela DRP e as quotas nacionais/UE. A série DRP é uma referência histórica "
        "regional publicada, mas não é o mesmo regime jurídico dos limites comerciais por Portaria. "
        "Valores nacionais ou europeus não devem ser interpretados como quotas exclusivas dos "
        "Açores sem confirmação do respetivo âmbito."
    )

st.divider()
st.header("Registo de limites de captura")
quota_years = sorted(quota_limits["year"].dropna().astype(int).unique()) if not quota_limits.empty else []
if quota_years:
    default_year = max(quota_years)
    selected_quota_year = st.selectbox(
        "Ano do registo", quota_years, index=quota_years.index(default_year)
    )
    year_limits = quota_limits[quota_limits["year"] == selected_quota_year].copy()
    verified_count = int((year_limits["verification_status"] == "Verificado").sum())
    st.caption(
        f"Registo de {selected_quota_year}: {verified_count} registos verificados e "
        f"{len(year_limits) - verified_count} por confirmar. Valores em toneladas."
    )
    display = year_limits.rename(columns={
        "species": "Espécie", "scientific_name": "Nome científico", "stock_code": "Stock",
        "source_level": "Nível da fonte", "limit_type": "Tipo de limite",
        "limit_tonnes": "Limite (t)", "geographic_scope": "Âmbito geográfico",
        "fleet_scope": "Âmbito da frota", "period": "Período", "status_as_of": "Vigente desde",
        "source_name": "Fonte", "source_url": "Ligação à fonte", "source_date": "Data da fonte",
        "verification_status": "Verificação", "notes": "Notas",
    })
    st.dataframe(
        display[[
            "Espécie", "Nome científico", "Stock", "Nível da fonte", "Tipo de limite",
            "Limite (t)", "Âmbito geográfico", "Âmbito da frota", "Período",
            "Verificação", "Fonte", "Data da fonte", "Ligação à fonte", "Notas",
        ]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Limite (t)": st.column_config.NumberColumn(format="%.2f"),
            "Ligação à fonte": st.column_config.LinkColumn(display_text="Consultar fonte"),
        },
    )

    year_events = quota_events[quota_events["year"] == selected_quota_year] if not quota_events.empty else quota_events
    if not year_events.empty:
        st.subheader("Avisos, encerramentos e reaberturas")
        event_display = year_events.rename(columns={
            "species": "Espécie", "stock_code": "Stock", "event_type": "Evento",
            "event_date": "Data", "source_name": "Fonte", "source_url": "Ligação à fonte",
            "notes": "Notas",
        })
        st.dataframe(
            event_display[[
                "Espécie", "Stock", "Evento", "Data", "Fonte", "Ligação à fonte", "Notas"
            ]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ligação à fonte": st.column_config.LinkColumn(display_text="Consultar fonte")
            },
        )

st.warning(
    "Este registo é uma compilação de fontes oficiais e pode não refletir alterações "
    "publicadas após a data indicada em cada fonte. Para efeitos legais e de gestão das "
    "pescas, prevalecem sempre os atos e avisos oficiais das entidades competentes."
)
with st.expander("Metodologia e limitações do registo de quotas", expanded=False):
    st.markdown(
        """
        O registo separa limites regionais, quotas nacionais atribuídas a Portugal e referências
        de TAC/quotas da União Europeia. Cada linha identifica o stock, a área, a frota, o tipo
        de limite, o período e a fonte legal ou administrativa. Limites anuais, trimestrais,
        por embarcação, por viagem e de captura acessória são regimes distintos e não devem
        ser somados.

        A quota inicial é preservada. Revisões, transferências, avisos de 80%, encerramentos
        e reaberturas são registados separadamente, com a respetiva data e fonte. Uma quota
        nacional ou um TAC da UE pode abranger uma área ou frota mais ampla do que os Açores.
        Os desembarques da LOTAÇOR não são automaticamente equivalentes ao consumo oficial
        de uma quota.

        A série histórica DRP (2008–2022) representa os totais admissíveis de captura
        atribuídos aos Açores, conforme publicados no Relatório do Estado do Ambiente dos
        Açores. É uma série estatística regional distinta dos limites comerciais definidos
        por Portaria; não deve ser somada a estes nem confundida com quota consumida.

        A Portaria 92/2019 entrou em vigor em 1 de janeiro de 2020 e estabeleceu limites
        anuais para 11 espécies, além de limites de captura acessória. O regime foi
        posteriormente substituído para 2022. Os valores só são apresentados nos anos e
        períodos sustentados pelas fontes consultadas; células sem valor na fonte não são
        interpretadas como zero. Valores nacionais ou da UE não são automaticamente
        atribuídos à frota açoriana.
        """
    )
