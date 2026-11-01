"""Descriptive statistics, percentage-point changes, and a NumPy matrix exercise."""

import math

from data_preparation import DISORDER_NAMES, DISORDERS, read_cleaned_data


def summarize_data(data):
    countries = data.loc[data["entity_type"] == "country_or_territory"]
    summary = countries[list(DISORDERS.values())].describe().T
    return summary.rename(index=DISORDER_NAMES)


def classify_change(change_pp, tolerance=0.1):
    """Use a descriptive tolerance in percentage points, not a medical cutoff."""
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("The tolerance must be a finite, nonnegative number.")
    if not math.isfinite(change_pp):
        return "Insufficient data"
    elif math.isclose(abs(change_pp), tolerance, abs_tol=1e-10):
        return "Little change"
    elif change_pp > tolerance:
        return "Increased"
    elif change_pp < -tolerance:
        return "Decreased"
    else:
        return "Little change"


def calculate_changes(data, countries, disorder_id, start_year, end_year, tolerance=0.1):
    """Compare exact endpoints; never replace a missing endpoint with another year."""
    import pandas as pd

    if start_year > end_year:
        raise ValueError("The start year must not follow the end year.")
    rows = []
    for country in countries:
        country_data = data.loc[
            data["entity_name"].eq(country) & data["entity_type"].eq("country_or_territory")
        ]
        start_values = country_data.loc[country_data["year"].eq(start_year), disorder_id]
        end_values = country_data.loc[country_data["year"].eq(end_year), disorder_id]
        start_value = float(start_values.iloc[0]) if not start_values.empty else float("nan")
        end_value = float(end_values.iloc[0]) if not end_values.empty else float("nan")
        change = end_value - start_value
        if start_year == end_year:
            category = "No interval"
            change = float("nan")
        else:
            category = classify_change(change, tolerance)
        rows.append({
            "entity_name": country,
            "start_pct": start_value,
            "end_pct": end_value,
            "change_pp": change,
            "trend": category,
        })
    return pd.DataFrame(rows, columns=["entity_name", "start_pct", "end_pct", "change_pp", "trend"])


def make_wide_data(observations):
    """Convert the SQL table back to a country/year matrix for chart calculations."""
    observations = observations.copy()
    observations["code"] = observations["code"].fillna("")
    identifiers = ["entity_name", "code", "entity_type", "year"]
    wide = observations.pivot(index=identifiers, columns="disorder_id", values="prevalence_pct")
    wide = wide.reindex(columns=list(DISORDERS.values())).reset_index()
    wide.columns.name = None
    return wide


def calculate_correlation_matrix(data, year):
    """Return correlation, complete-country count, and excluded constant columns."""
    import numpy as np
    import pandas as pd

    metrics = list(DISORDERS.values())
    snapshot = data.loc[
        data["year"].eq(year) & data["entity_type"].eq("country_or_territory"), metrics
    ].dropna()
    country_count = len(snapshot)
    if country_count < 3:
        return pd.DataFrame(), country_count, []

    values = snapshot.to_numpy(dtype=float)
    deviations = values.std(axis=0, ddof=1)
    varying = deviations > 1e-12
    excluded = [metrics[index] for index in range(len(metrics)) if not varying[index]]
    names = [DISORDER_NAMES[metrics[index]] for index in range(len(metrics)) if varying[index]]
    if len(names) < 2:
        return pd.DataFrame(), country_count, excluded

    values = values[:, varying]
    standardized = (values - values.mean(axis=0)) / deviations[varying]
    correlation = standardized.T @ standardized / (country_count - 1)
    correlation = np.clip(correlation, -1, 1)
    return pd.DataFrame(correlation, index=names, columns=names), country_count, excluded


def main():
    data = read_cleaned_data()
    countries = sorted(data.loc[data["entity_type"].eq("country_or_territory"), "entity_name"].unique())
    first_year = int(data["year"].min())
    last_year = int(data["year"].max())
    print(f"Coverage: {len(countries)} countries/territories, {first_year}-{last_year}")
    print("\nCountry-year descriptive statistics (%); not population-weighted:")
    print(summarize_data(data).round(3).to_string())
    changes = calculate_changes(data, countries, "depression", first_year, last_year)
    print("\nLargest depression increases (percentage points, exact endpoints):")
    print(changes.dropna(subset=["change_pp"]).nlargest(5, "change_pp").round(3).to_string(index=False))
    print("\nLargest depression decreases (percentage points, exact endpoints):")
    print(changes.dropna(subset=["change_pp"]).nsmallest(5, "change_pp").round(3).to_string(index=False))
    correlation, count, excluded = calculate_correlation_matrix(data, last_year)
    print(f"\n{last_year} correlations across {count} complete countries/territories:")
    print(correlation.round(3).to_string())
    print(f"Excluded constant columns: {excluded}")
    print("\nThese are descriptive associations, not causes or individual diagnoses.")


if __name__ == "__main__":
    main()