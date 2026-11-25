import numpy as np
import pandas as pd


def prepare_observations(df):
    if df.empty:
        return df.copy()

    df = df.copy()
    df["period_start"] = pd.to_datetime(df["period_start"])
    df["year"] = df["period_start"].dt.year
    df["month"] = df["period_start"].dt.month
    df["period"] = df["period_start"].dt.to_period("M").dt.to_timestamp()
    return df


def summarise_period(df, frequency="YS"):
    if df.empty:
        return pd.DataFrame(columns=["period", "weight_kg", "value_eur", "average_price_eur"])

    grouped = (
        df.set_index("period").groupby(pd.Grouper(freq=frequency))
        .agg(weight_kg=("weight_kg", "sum"), value_eur=("value_eur", "sum"))
        .reset_index()
    )
    grouped["average_price_eur"] = grouped["value_eur"] / grouped["weight_kg"]
    grouped.loc[grouped["weight_kg"] == 0, "average_price_eur"] = np.nan
    return grouped


def summarise_species(df):
    if df.empty:
        return pd.DataFrame(columns=["species", "weight_kg", "value_eur", "average_price_eur"])

    grouped = df.groupby("species", as_index=False).agg(
        weight_kg=("weight_kg", "sum"), value_eur=("value_eur", "sum")
    )
    grouped["average_price_eur"] = grouped["value_eur"] / grouped["weight_kg"]
    grouped.loc[grouped["weight_kg"] == 0, "average_price_eur"] = np.nan
    return grouped.sort_values("weight_kg", ascending=False)


def annual_species_summary(df):
    if df.empty:
        return pd.DataFrame(columns=["year", "species", "weight_kg", "value_eur"])

    return df.groupby(["year", "species"], as_index=False).agg(
        weight_kg=("weight_kg", "sum"), value_eur=("value_eur", "sum")
    )


def monthly_species_summary(df, species=None):
    selected = df if species is None else df[df["species"].isin(species)]
    if selected.empty:
        return pd.DataFrame(columns=["period", "species", "weight_kg", "value_eur"])

    return selected.groupby(["period", "species"], as_index=False).agg(
        weight_kg=("weight_kg", "sum"), value_eur=("value_eur", "sum")
    )


def species_seasonality(df, species):
    selected = df[df["species"].isin(species)]
    if selected.empty:
        return pd.DataFrame(columns=["month", "species", "mean_weight_kg"])

    annual_monthly = selected.groupby(["year", "month", "species"], as_index=False)["weight_kg"].sum()
    return annual_monthly.groupby(["month", "species"], as_index=False)["weight_kg"].mean().rename(
        columns={"weight_kg": "mean_weight_kg"}
    )


def annual_species_trends(df, complete_years):
    """Return annual species totals, zero-filling only years with 12 successful monthly requests."""

    annual = annual_species_summary(df[df["year"].isin(complete_years)])
    species = sorted(df["species"].dropna().unique().tolist())
    if not complete_years or not species:
        return annual

    index = pd.MultiIndex.from_product([complete_years, species], names=["year", "species"])
    annual = annual.set_index(["year", "species"]).reindex(index, fill_value=0).reset_index()
    return annual


def trend_statistics(annual, value_column="weight_kg", min_years=4):
    """Calculate simple linear trends; results describe landings, not stock status."""

    rows = []
    if annual.empty:
        return pd.DataFrame(columns=["species", "years", "slope_per_year", "change_percent", "r_squared"])

    for species, group in annual.groupby("species"):
        group = group.sort_values("year")
        x = group["year"].to_numpy(dtype=float)
        y = group[value_column].to_numpy(dtype=float)
        if len(x) < min_years or np.all(y == 0):
            continue

        slope, intercept = np.polyfit(x, y, 1)
        fitted = slope * x + intercept
        residual_sum = np.sum((y - fitted) ** 2)
        total_sum = np.sum((y - y.mean()) ** 2)
        r_squared = 1 - residual_sum / total_sum if total_sum > 0 else np.nan
        baseline = fitted[0]
        change = ((fitted[-1] / baseline) - 1) * 100 if baseline > 0 else np.nan
        rows.append({
            "species": species, "years": len(group), "slope_per_year": slope,
            "change_percent": change, "r_squared": r_squared,
            "first_year": int(x[0]), "last_year": int(x[-1]),
        })

    return pd.DataFrame(rows).sort_values("slope_per_year") if rows else pd.DataFrame(
        columns=["species", "years", "slope_per_year", "change_percent", "r_squared",
                 "first_year", "last_year"]
    )


def composition_metrics(species_summary):
    if species_summary.empty or species_summary["weight_kg"].sum() <= 0:
        return {"top5_share": np.nan, "hhi": np.nan, "effective_species": np.nan}

    shares = species_summary["weight_kg"] / species_summary["weight_kg"].sum()
    hhi = float(np.sum(shares ** 2))
    return {
        "top5_share": float(shares.nlargest(5).sum()),
        "hhi": hhi,
        "effective_species": 1 / hhi if hhi > 0 else np.nan,
    }


def annual_diversity_metrics(df, complete_years):
    """Calculate annual catch-composition metrics from complete calendar years.

    Relative abundance is represented by each species' share of total landed weight.
    These metrics describe landings composition, not the status of fish populations.
    """

    columns = [
        "year", "species_richness", "shannon_diversity", "pielou_evenness",
        "dominant_species_share", "dominant_species",
    ]
    if df.empty or not complete_years:
        return pd.DataFrame(columns=columns)

    selected = df[df["year"].isin(complete_years)].copy()
    selected = selected.dropna(subset=["species", "weight_kg"])
    selected = selected[np.isfinite(selected["weight_kg"]) & (selected["weight_kg"] > 0)]
    if selected.empty:
        return pd.DataFrame(columns=columns)

    species_weights = selected.groupby(["year", "species"], as_index=False)["weight_kg"].sum()
    rows = []
    for year, group in species_weights.groupby("year"):
        group = group[group["weight_kg"] > 0]
        total_weight = group["weight_kg"].sum()
        if total_weight <= 0:
            continue

        shares = group["weight_kg"].to_numpy(dtype=float) / total_weight
        richness = len(shares)
        shannon = float(-np.sum(shares * np.log(shares)))
        evenness = shannon / np.log(richness) if richness > 1 else np.nan
        dominant_index = int(np.argmax(shares))
        dominant_species = group.iloc[dominant_index]["species"]

        rows.append({
            "year": int(year),
            "species_richness": int(richness),
            "shannon_diversity": shannon,
            "pielou_evenness": float(evenness) if np.isfinite(evenness) else np.nan,
            "dominant_species_share": float(shares[dominant_index]),
            "dominant_species": dominant_species,
        })

    return pd.DataFrame(rows, columns=columns).sort_values("year").reset_index(drop=True)


def seasonal_concentration(df):
    """Summarise the distribution of total landings across calendar months."""

    if df.empty:
        return pd.DataFrame(columns=["month", "weight_kg", "share"])

    monthly = df.groupby("month", as_index=False)["weight_kg"].sum()
    total = monthly["weight_kg"].sum()
    monthly["share"] = monthly["weight_kg"] / total if total else np.nan
    return monthly
