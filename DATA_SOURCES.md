# Data sources and reuse

## Source

The project currently retrieves fisheries landings data from the LOTAÇOR website:

- Landing page: <https://www.lotacor.pt/pescado-descarregado>
- API endpoint observed by the project: <https://www.lotacor.pt/api/testQuery>

The reports currently used are:

- `DNA` — `Descargas nos Açores`
- `DPI` — `Descargas por Ilha`

The API requests are made for monthly date intervals. The responses inspected by the project contain aggregates by species; the `DPI` response also includes the island. The database stores the report type, query filters and island labels alongside the returned observations.

## Attribution

Adamastus is an independent project and is not an official LOTAÇOR or Regional Government of the Azores product. LOTAÇOR is identified as the source of the downloaded data. Users should consult the original source for authoritative information and any updates to its terms.

## Fishing quota reference data

Quota information is maintained as a source-traceable register rather than a single list of
species and values:

- `data/quota_register.csv` stores one record per year, stock, source level and limit type.
  It distinguishes regional limits, national allocations, and EU-level references, and records
  the geographic and fleet scope, period, verification status and source.
- `data/quota_events.csv` stores dated 80% warnings, closures and reopenings separately from
  the initial quota values.
- `data/quota_history_status.csv` records the reconstruction status for earlier years. Years
  are not populated until the applicable legislation and amendments have been checked.

The 2026 regional baseline is Portaria n.º 112/2023, as republished by Portaria n.º 115/2026,
including its annual commercial limits (Annex I), quarterly limits (Annex II) and annual
accessory-catch limits (Annex III):
<https://diariodarepublica.pt/dr/detalhe/portaria/115-2026-1185276275>

The 2026 national baseline is the DGRM document *Avisos 80% de utilização da quota e fechos
de pesca*, dated 23 November 2026. It records initial Portuguese quotas by species and stock,
including large migrators:
<https://www.dgrm.pt/documents/20143/46478/AVISOS%2B80%25%2BE%2BFECHOS%2B23-11-2026.pdf/a1c585bc-60d6-4a7e-e2b8-c813be21a0a9>

The DGRM TAC and quota page identifies the EU regulations that establish and amend fishing
opportunities. For 2026, the register must account for Regulation (EU) 2026/249 and its
subsequent amendments, including Regulations (EU) 2026/786 and 2026/1547:
<https://dgrm.pt/tac-e-quotas>

A Portuguese national quota is not automatically an allocation to the Azores fleet. EU TACs,
Portuguese allocations, Azores-specific allocations, regional limits, quarterly limits, vessel
limits, trip limits and accessory-catch limits are distinct regimes. They are not added together
or compared with LOTAÇOR landings unless their scope is demonstrably aligned.

The dedicated `Quotas` page contains the single-species annual chart and the quota/event tables.
The chart shows LOTAÇOR landings alongside verified national, regional and EU annual quota
records where available. National and EU values are shown as published, with their fleet and
geographic scope visible in the table; they must not be interpreted as Azores-only allocations
unless the source explicitly establishes that scope. The chart includes incomplete years and
shows only the landings recorded so far, without annualising them.

The regional annual comparison currently includes verified records for 2024 (Portaria n.º
112/2023), 2025 (Portaria n.º 113-A/2025) and 2026 (Portaria n.º 115/2026). The 2025 limit
was revised on 14 October 2025; its chart tooltip and source table retain that provenance. The
Mero limit is not plotted for 2024 or 2025 because fishing was prohibited during those years;
the prohibition was revoked with effect from 1 January 2026. Missing years are left blank rather
than interpolated or carried forward.

The historical register remains incomplete. Further national, EU and regional regimes, including
separate Goraz and Imperadores rules and older annual legislation, still require reconciliation.
Official legal acts and notices always take precedence over this research dataset.


## DGRM annual quota snapshots (2023–2026)

The quota register includes DGRM annual 80% warning and fishery-closure snapshots for 2023, 2024, 2025 and 2026. Historical entries are retained by species and stock code. These are Portuguese quota/stock records and must not automatically be interpreted as Azores-fleet allocations. Only explicitly Azores-specific records with a compatible full-year scope are marked eligible for direct comparison with LOTAÇOR annual landings. The 2025 Goraz (Açores) entry is time-limited to 30 June and is not chart-eligible. The snapshots do not by themselves reconstruct every in-year revision, transfer or closure event.


## Historical quota register (2023–2026)

The regional 2023 annual commercial and accessory-catch limits are transcribed from Portaria n.º 105/2022, Anexos I–III (effective for the 2023 management year). The 2024 regional limits are based on Portaria n.º 112/2023, effective 1 January 2024. The 2025 and 2026 regional records follow the respective amended/re-published regional framework.

National snapshots are taken from dated DGRM “Avisos 80% de utilização da quota e fechos de pesca” documents. These are snapshots of initial quotas and management events, not a complete ledger of all subsequent revisions or transfers. Stock, area, fleet and reference period must be retained; national totals are not automatically allocations to the Azores fleet.

The 2023 DGRM snapshot is dated 1 June 2023, the 2024 snapshot 7 November 2024, and the 2025 snapshot 14 April 2025. Historical records should not be interpreted as final annual quotas unless subsequent amendments and transfers have also been reconciled.


The 2022 regional records are transcribed from Portaria n.º 75-A/2022, which republishes the Portaria n.º 130/2021 regime as amended. The amended regime entered into force on 1 April 2022; the August republication also changes the management of Veja and is accompanied by later transfers between islands. The annual 2022 limits are therefore retained in the register but deliberately excluded from a full-calendar-year chart comparison.


## Historical fisheries quota and catch-limit data

The quota register includes the DRP historical series *Evolução dos totais admissíveis de captura atribuídos aos Açores* for 2008–2022. The regional environmental report identifies DRP (Direção Regional das Pescas) as the source and publishes ten annual series in tonnes: Patudo, Voador, Chicharro, Goraz, Imperador, Abrótea, Tamboril, Espadarte, Rabilo and Espada-preto. Blank cells in the published table are omitted from the register and are not interpreted as zero. The original source labels are preserved in each record's notes.

Source: https://rea.azores.gov.pt/reaa/7/aguas-costeiras-oceano-e-recursos-halieuticos/1355/recursos-marinhos

The register separately records the annual commercial limits in Annex I and accessory-catch limits in Annex II of the corrected republication of Portaria 92/2019. That regime entered into force on 1 January 2020. Its eleven commercial species are Abrótea, Badejo, Boca-negra, Cântaro, Caranguejo-real, Congro, Melga, Mero, Raia, Sapateira-dentada and Veja. Cação and Tintureira are accessory-catch limits, with directed fishing prohibited. These figures are recorded for 2020 and 2021 only; they are not extrapolated into the 2022 regime.

Source: https://jo.azores.gov.pt/api/public/anexo/-80436366?filename=Anexo.pdf

The DRP historical TAC series and the Portaria commercial limits are different management datasets. They are kept as separate chart series and must not be added together. Likewise, species-specific regimes such as Imperadores (Portaria 93/2017 and amendments) and Goraz are documented separately where a single comparable annual regional total has not been verified.
