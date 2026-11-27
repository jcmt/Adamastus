# Adamastus dashboard

The Streamlit dashboard interface is written in Portuguese (Portugal).

Run it from the project root:

```bash
uv run streamlit run dashboard/Visao_geral.py
```

The sidebar navigation is ordered as follows: Visão geral, Análise por espécie, Sazonalidade, Desembarques por ilha, Quotas and, last, Cobertura dos dados. The dashboard reads the local SQLite database configured in `config.py`; run the downloader first if the database has not yet been created.
