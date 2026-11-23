import unittest

import numpy as np
import pandas as pd

from analysis.analysis import (
    annual_species_trends,
    composition_metrics,
    prepare_observations,
    seasonal_concentration,
    species_seasonality,
    summarise_period,
    summarise_species,
    trend_statistics,
)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.observations = pd.DataFrame([
            {"period_start": "2020-01-01", "species": "Atum", "weight_kg": 1000, "value_eur": 5000},
            {"period_start": "2020-02-01", "species": "Atum", "weight_kg": 3000, "value_eur": 18000},
            {"period_start": "2020-01-01", "species": "Cavala", "weight_kg": 1000, "value_eur": 2000},
            {"period_start": "2021-01-01", "species": "Atum", "weight_kg": 2000, "value_eur": 12000},
        ])
        self.prepared = prepare_observations(self.observations)

    def test_prepare_observations_derives_calendar_fields(self):
        self.assertEqual(self.prepared.loc[0, "year"], 2020)
        self.assertEqual(self.prepared.loc[0, "month"], 1)
        self.assertEqual(str(self.prepared.loc[0, "period"]), "2020-01-01 00:00:00")

    def test_species_summary_uses_weighted_price(self):
        summary = summarise_species(self.prepared)
        tuna = summary.loc[summary["species"] == "Atum"].iloc[0]
        self.assertEqual(tuna["weight_kg"], 6000)
        self.assertEqual(tuna["value_eur"], 35000)
        self.assertAlmostEqual(tuna["average_price_eur"], 35000 / 6000)

    def test_period_summary_uses_weighted_price(self):
        monthly = summarise_period(self.prepared, frequency="MS")
        january_2020 = monthly.loc[monthly["period"] == pd.Timestamp("2020-01-01")].iloc[0]
        self.assertEqual(january_2020["weight_kg"], 2000)
        self.assertEqual(january_2020["value_eur"], 7000)
        self.assertEqual(january_2020["average_price_eur"], 3.5)

    def test_composition_metrics(self):
        metrics = composition_metrics(summarise_species(self.prepared))
        self.assertAlmostEqual(metrics["top5_share"], 1.0)
        self.assertGreater(metrics["hhi"], 0)
        self.assertAlmostEqual(metrics["effective_species"], 1 / metrics["hhi"])

    def test_trend_statistics_recovers_linear_slope(self):
        annual = pd.DataFrame({
            "year": [2020, 2021, 2022, 2023],
            "species": ["Atum"] * 4,
            "weight_kg": [100, 200, 300, 400],
        })
        result = trend_statistics(annual)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result.iloc[0]["slope_per_year"], 100)

    def test_annual_species_trends_zero_fills_missing_species_year(self):
        annual = annual_species_trends(self.prepared, [2020, 2021])
        cavala_2021 = annual[(annual["species"] == "Cavala") & (annual["year"] == 2021)]
        self.assertEqual(cavala_2021.iloc[0]["weight_kg"], 0)

    def test_seasonality_returns_expected_months(self):
        concentration = seasonal_concentration(self.prepared)
        self.assertEqual(set(concentration["month"]), {1, 2})
        seasonal = species_seasonality(self.prepared, ["Atum"])
        self.assertEqual(set(seasonal["month"]), {1, 2})

    def test_empty_inputs_are_handled(self):
        empty = pd.DataFrame(columns=["period_start", "species", "weight_kg", "value_eur"])
        self.assertTrue(prepare_observations(empty).empty)
        self.assertTrue(summarise_species(empty).empty)
        self.assertTrue(summarise_period(empty).empty)
        self.assertTrue(trend_statistics(pd.DataFrame()).empty)
        metrics = composition_metrics(pd.DataFrame(columns=["weight_kg"]))
        self.assertTrue(np.isnan(metrics["hhi"]))


if __name__ == "__main__":
    unittest.main()
