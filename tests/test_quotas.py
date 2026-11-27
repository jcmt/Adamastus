import unittest

import pandas as pd

from analysis.quotas import (
    annual_quotas_for_chart,
    quota_records_for_species,
    load_quota_events,
    load_quota_limits,
    quota_source_colours,
    quota_chart_records,
    annual_landings_for_species,
    quota_chart_species,
)


class QuotaTests(unittest.TestCase):
    def test_register_contains_regional_annual_limits(self):
        quotas = load_quota_limits()
        regional = quotas[
            (quotas["year"] == 2026)
            & (quotas["source_level"] == "Regional")
            & (quotas["limit_type"] == "Anual")
        ]
        self.assertEqual(len(regional), 8)
        self.assertAlmostEqual(
            regional.loc[regional["species"] == "Veja", "limit_tonnes"].iloc[0],
            240.0056,
        )

    def test_2022_regional_limits_are_verified_but_not_full_year_charted(self):
        quotas = load_quota_limits()
        regional = quotas[
            (quotas["year"] == 2022)
            & (quotas["source_level"] == "Regional")
            & quotas["limit_type"].str.startswith("Anual")
        ]
        self.assertEqual(len(regional), 8)
        self.assertTrue((regional["chart_eligible"] == "Não").all())
        self.assertAlmostEqual(
            regional.loc[regional["species"] == "Garoupa", "limit_tonnes"].iloc[0],
            40.0,
        )

    def test_2023_regional_limits_match_portaria_105_2022_annex_i(self):
        quotas = load_quota_limits()
        regional = quotas[
            (quotas["year"] == 2023)
            & (quotas["source_level"] == "Regional")
            & (quotas["limit_type"] == "Anual")
        ].set_index("species")
        self.assertEqual(len(regional), 8)
        self.assertAlmostEqual(regional.loc["Boca-negra", "limit_tonnes"], 250.0)
        self.assertAlmostEqual(regional.loc["Raia", "limit_tonnes"], 100.0)

    def test_quarterly_and_accessory_limits_are_separate(self):
        quotas = load_quota_limits()
        quarterly = quotas[quotas["limit_type"] == "Trimestral"]
        accessory = quotas[quotas["limit_type"] == "Captura acessória anual"]
        self.assertEqual(len(quarterly), 63)
        self.assertEqual(len(accessory), 10)
        self.assertFalse((quarterly["species"] == "Cação").any())

    def test_national_tuna_stocks_are_included(self):
        quotas = load_quota_limits()
        tuna = quotas[quotas["species"].str.contains("Atum|Espadarte|Espadim", regex=True)]
        current_bigeye = tuna[
            (tuna["year"] == 2026) & (tuna["species"] == "Atum-patudo")
        ].iloc[0]
        self.assertAlmostEqual(current_bigeye["limit_tonnes"], 2856.45)
        self.assertEqual(current_bigeye["source_level"], "Nacional")
        self.assertTrue({2023, 2024, 2025, 2026}.issubset(set(tuna["year"])))

    def test_zero_and_unresolved_values_are_retained(self):
        quotas = load_quota_limits()
        zero = quotas[(quotas["species"] == "Arinca") & (quotas["source_level"] == "Nacional")]
        unresolved = quotas[(quotas["species"] == "Carapau (Açores)") & (quotas["year"] == 2025)]
        self.assertEqual(zero.iloc[0]["limit_tonnes"], 0)
        self.assertTrue(pd.isna(unresolved.iloc[0]["limit_tonnes"]))
        self.assertEqual(unresolved.iloc[0]["verification_status"], "Pendente")

    def test_historical_regional_annual_limits_are_available_for_chart(self):
        quotas = annual_quotas_for_chart(
            ["Abrótea", "Garoupa", "Mero"], [2024, 2025, 2026]
        )
        abrotea = quotas[quotas["species"] == "Abrótea"].set_index("year")
        garoupa = quotas[quotas["species"] == "Garoupa"].set_index("year")
        self.assertAlmostEqual(abrotea.loc[2024, "limit_tonnes"], 210.0)
        self.assertAlmostEqual(abrotea.loc[2025, "limit_tonnes"], 230.0)
        self.assertAlmostEqual(abrotea.loc[2026, "limit_tonnes"], 240.0)
        self.assertAlmostEqual(garoupa.loc[2025, "limit_tonnes"], 43.75)
        mero = quotas[quotas["species"] == "Mero"]
        self.assertEqual(mero["year"].tolist(), [2026])

    def test_national_stock_totals_are_not_plotted_against_lotacor(self):
        quotas = annual_quotas_for_chart(["Atum-patudo"], [2023, 2024, 2025, 2026])
        self.assertTrue(quotas.empty)

    def test_non_comparable_national_tuna_limits_remain_visible_as_context(self):
        records = quota_records_for_species(
            ["Atum-patudo"], [2023, 2024, 2025, 2026]
        )
        self.assertEqual(records["year"].tolist(), [2023, 2024, 2025, 2026])
        self.assertTrue((records["source_level"] == "Nacional").all())
        self.assertTrue((records["chart_eligible"] == "Não").all())

    def test_azores_specific_goraz_records_are_scope_checked(self):
        quotas = annual_quotas_for_chart(["Goraz"], [2023, 2024, 2025, 2026])
        # The 2025 DGRM value only applies until 30 June and is not comparable
        # with annual landings. Full-year Azores-specific snapshots are retained.
        self.assertEqual(quotas["year"].tolist(), [2023, 2024, 2026])
        self.assertEqual(quotas["limit_tonnes"].tolist(), [600.0, 600.0, 376.0])
        chart_records = quota_chart_records("Goraz")
        self.assertNotIn(2025, chart_records["year"].astype(int).tolist())

    def test_events_are_loaded_with_dates(self):
        events = load_quota_events()
        self.assertGreaterEqual(len(events), 10)
        self.assertIn("Reabertura da pesca", set(events["event_type"]))

    def test_source_colours_are_stable(self):
        colours = quota_source_colours()
        self.assertEqual(set(colours), {"Regional", "Nacional", "UE"})

    def test_quota_chart_excludes_non_comparable_national_records(self):
        tuna = quota_chart_records("Atum-patudo")
        national_tuna = tuna[tuna["source_level"] == "Nacional"]
        drp_tuna = tuna[tuna["stock_code"] == "DRP-AZORES-TAC"]
        self.assertTrue(national_tuna.empty)
        self.assertEqual(drp_tuna["year"].astype(int).tolist(), list(range(2008, 2023)))

    def test_chart_uses_annual_not_quarterly_limits(self):
        abrotea = quota_chart_records("Abrótea")
        current = abrotea[abrotea["year"] == 2026]
        self.assertEqual(len(current), 1)
        self.assertEqual(current.iloc[0]["limit_type"], "Anual")
        self.assertAlmostEqual(current.iloc[0]["limit_tonnes"], 240.0)
        self.assertNotIn(70.0, current["limit_tonnes"].tolist())

    def test_chart_species_excludes_species_without_verified_quotas(self):
        species = quota_chart_species([
            "Abrótea", "Atum-patudo", "Arinca", "Bromcom", "Veja"
        ])
        self.assertIn("Abrótea", species)
        self.assertIn("Atum-patudo", species)
        self.assertIn("Veja", species)
        self.assertNotIn("Arinca", species)
        self.assertNotIn("Bromcom", species)

    def test_quota_chart_keeps_regional_and_historical_drp_series(self):
        abrotea = quota_chart_records("Abrótea")
        drp = abrotea[abrotea["stock_code"] == "DRP-AZORES-TAC"]
        portaria = abrotea[abrotea["stock_code"] == "PORTARIA-92-2019"]
        self.assertEqual(drp["year"].astype(int).tolist(), list(range(2008, 2020)))
        self.assertEqual(portaria["year"].astype(int).tolist(), [2020, 2021])


    def test_drp_historical_azores_allocations_cover_2008_to_2022(self):
        quotas = load_quota_limits()
        drp = quotas[quotas["stock_code"] == "DRP-AZORES-TAC"]
        self.assertEqual(set(drp["year"].astype(int)), set(range(2008, 2023)))
        self.assertEqual(drp["species"].nunique(), 10)
        patudo_2010 = drp[(drp["species"] == "Atum-patudo") & (drp["year"] == 2010)]
        self.assertAlmostEqual(patudo_2010["limit_tonnes"].iloc[0], 6160.0)
        self.assertTrue((drp["verification_status"] == "Verificado").all())

    def test_portaria_92_limits_start_in_2020_not_2019(self):
        quotas = load_quota_limits()
        legal = quotas[quotas["stock_code"] == "PORTARIA-92-2019"]
        self.assertEqual(set(legal["year"].astype(int)), {2020, 2021})
        self.assertEqual(legal["species"].nunique(), 11)
        self.assertAlmostEqual(
            legal[(legal["species"] == "Congro") & (legal["year"] == 2020)]["limit_tonnes"].iloc[0],
            400.0,
        )

    def test_annual_landings_include_partial_years(self):
        observations = pd.DataFrame({
            "year": [2025, 2026, 2026],
            "species": ["Atum-patudo"] * 3,
            "weight_kg": [1000, 2000, 500],
        })
        annual = annual_landings_for_species(observations, "Atum-patudo")
        self.assertEqual(annual["year"].tolist(), [2025, 2026])
        self.assertEqual(annual["landings_tonnes"].tolist(), [1.0, 2.5])


if __name__ == "__main__":
    unittest.main()
