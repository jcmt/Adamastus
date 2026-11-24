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
    """Return annual species totals and weighted average prices for complete years."""

    annual = annual_species_summary(df[df["year"].isin(complete_years)])
    species = sorted(df["species"].dropna().unique().tolist())
    if complete_years and species:
        index = pd.MultiIndex.from_product([complete_years, species], names=["year", "species"])
        annual = annual.set_index(["year", "species"]).reindex(index, fill_value=0).reset_index()

    if annual.empty:
        return annual.assign(average_price_eur=pd.Series(dtype=float))

    annual["average_price_eur"] = annual["value_eur"] / annual["weight_kg"]
    annual.loc[annual["weight_kg"] <= 0, "average_price_eur"] = np.nan
    return annual


def trend_statistics(annual, value_column="weight_kg", min_years=4):
    """Calculate simple linear trends; results describe landings, not stock status."""

    rows = []
    if annual.empty:
        return pd.DataFrame(columns=["species", "years", "slope_per_year", "change_percent", "r_squared"])

    for species, group in annual.groupby("species"):
        group = group.sort_values("year")
        valid = np.isfinite(group["year"]) & np.isfinite(group[value_column])
        group = group.loc[valid]
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


def seasonal_concentration(df):
    """Summarise the distribution of total landings across calendar months."""

    if df.empty:
        return pd.DataFrame(columns=["month", "weight_kg", "share"])

    monthly = df.groupby("month", as_index=False)["weight_kg"].sum()
    total = monthly["weight_kg"].sum()
    monthly["share"] = monthly["weight_kg"] / total if total else np.nan
    return monthly
