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
