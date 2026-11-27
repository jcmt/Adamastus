import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

from analysis.analysis import prepare_observations
from dashboard.common import MONTH_NAMES
from config import DATABASE_PATH
from lotacor.database import initialise_database, load_download_history, load_observations

st.set_page_config(page_title="Cobertura dos dados · Adamastus", page_icon="🧾", layout="wide")
st.title("Cobertura e qualidade dos dados")
st.caption("Verifique a cobertura dos dados antes de interpretar as tendências")

initialise_database()
observations = prepare_observations(load_observations())
history = load_download_history()
report_label = st.selectbox("Relatório", ["Regional (DNA)", "Por ilha (DPI)"])
query_type = "DNA" if report_label == "Regional (DNA)" else "DPI"
df = observations[observations["query_type"] == query_type].copy()
if history.empty:
    st.warning("Não existe histórico de descarregamento.")
    st.stop()

history = history[
    (history["query_type"] == query_type) &
    (history["lota_id"] == "all") &
    (history["ilha_id"] == "all") &
    (history["fao"] == "all")
].copy()
if history.empty:
    st.warning(f"Não existe histórico de descarregamento para o relatório {report_label}.")
    st.stop()
history["period_start"] = pd.to_datetime(history["period_start"])
history["year"] = history["period_start"].dt.year
history["month"] = history["period_start"].dt.month
history["month_name"] = history["month"].map(MONTH_NAMES)
history = history.sort_values("retrieved_at").drop_duplicates(
    ["query_type", "lota_id", "ilha_id", "fao", "year", "month"], keep="last"
)

st.subheader(f"Estado dos descarregamentos mensais · {report_label}")
status = history.pivot_table(index="year", columns="month", values="status",
                             aggfunc="last", fill_value="missing")
status = status.reindex(columns=range(1, 13), fill_value="missing")
status.columns = [MONTH_NAMES[month] for month in status.columns]
status = status.replace({"success": "Sucesso", "failed": "Falha", "missing": "Em falta"})
st.dataframe(status, use_container_width=True)

st.subheader("Meses com sucesso, falha ou em falta")
counts = status.stack().reset_index(name="status").groupby(
    ["year", "status"], as_index=False
).size().rename(columns={"size": "months"})
fig = px.bar(counts, x="year", y="months", color="status", barmode="stack",
             labels={"year": "Ano", "months": "Número de meses", "status": "Estado"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Erros de descarregamento")
failures = history[history["status"] != "success"]
if failures.empty:
    st.success("Não existem pedidos sem sucesso no histórico de descarregamento.")
else:
    failures["status"] = failures["status"].map({"failed": "Falha"}).fillna(failures["status"])
    st.dataframe(
        failures[["period_start", "period_end", "status", "error"]].rename(columns={
            "period_start": "Início do período", "period_end": "Fim do período",
            "status": "Estado", "error": "Erro",
        }),
        use_container_width=True, hide_index=True,
    )

st.subheader("Base de dados")
st.write("Localização da base de dados:", str(DATABASE_PATH.resolve()))
if not df.empty:
    st.write("Observações:", f"{len(df):,}")
    st.write("Intervalo de datas:", f"{df['period_start'].min().date()} a {df['period_end'].max()}")
    st.write("Espécies:", f"{df['species'].nunique():,}")
    st.write("Meses representados nas observações:", f"{df[['year', 'month']].drop_duplicates().shape[0]:,}")

st.info(
    "Um pedido mensal à API concluído com sucesso pode não devolver registos de espécies. Esta "
    "situação é diferente de um pedido em falta ou com falha. Por isso, o histórico de "
    "descarregamento é essencial para interpretar corretamente as lacunas."
)
