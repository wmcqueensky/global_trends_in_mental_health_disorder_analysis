"""Seven charts; each function returns a figure for Streamlit or testing."""

import textwrap

import matplotlib.pyplot as plt
import seaborn as sns

from data_preparation import DISORDER_NAMES


TEAL = "#167D8D"
CORAL = "#CC6148"
GOLD = "#AD811B"
GREEN = "#49805B"
COLORS = [TEAL, CORAL, GOLD, GREEN, "#5B65A5"]


def chart_axes(title, size=(9, 5)):
    figure, axes = plt.subplots(figsize=size, layout="constrained")
    axes.set_title(title, loc="left", fontsize=13, pad=14)
    return figure, axes


def empty_chart(axes, message="No observations for this selection"):
    axes.text(0.5, 0.5, message, ha="center", va="center", transform=axes.transAxes, wrap=True)
    axes.set_axis_off()


def plot_trends(data, disorder_name):
    figure, axes = chart_axes(f"{disorder_name}: reported prevalence over time")
    if data.empty:
        empty_chart(axes)
        return figure
    all_years = range(int(data["year"].min()), int(data["year"].max()) + 1)
    for index, entity in enumerate(sorted(data["entity_name"].unique())):
        observations = data.loc[data["entity_name"].eq(entity)].set_index("year").reindex(all_years)
        is_world = observations["entity_type"].eq("world").any()
        axes.plot(
            observations.index, observations["prevalence_pct"],
            label="World (source series)" if is_world else entity,
            color="#333333" if is_world else COLORS[index % len(COLORS)],
            linestyle="--" if is_world else "-", linewidth=2,
            marker="o" if len(all_years) == 1 else None,
        )
    axes.set_xlabel("Year")
    axes.set_ylabel("Prevalence (%)")
    axes.legend(fontsize=9, loc="best")
    return figure


def plot_ranking(ranking, disorder_name, year):
    figure, axes = chart_axes(f"{disorder_name}: highest prevalence in the selected cohort, {year}", (9, 6))
    if ranking.empty:
        empty_chart(axes)
    else:
        sns.barplot(data=ranking, x="prevalence_pct", y="entity_name", color=TEAL, errorbar=None, ax=axes)
        axes.set_xlabel("Prevalence (%)")
        axes.set_ylabel("")
    return figure


def plot_distribution(snapshot, disorder_id, year):
    figure, axes = chart_axes(f"{DISORDER_NAMES[disorder_id]}: country distribution, {year}")
    values = snapshot[disorder_id].dropna()
    if values.empty:
        empty_chart(axes)
    else:
        sns.histplot(values, bins=min(12, max(1, len(values))), color=GOLD, ax=axes)
        axes.set_xlabel("Prevalence (%)")
        axes.set_ylabel("Countries/territories")
    return figure


def plot_disorder_boxplot(snapshot, year):
    figure, axes = chart_axes(f"Seven disorders: country distributions, {year}", (9, 6))
    long_data = snapshot.melt(value_vars=list(DISORDER_NAMES), var_name="disorder_id", value_name="prevalence_pct").dropna()
    if long_data.empty:
        empty_chart(axes)
    else:
        long_data["disorder"] = long_data["disorder_id"].map(DISORDER_NAMES)
        sns.boxplot(data=long_data, x="prevalence_pct", y="disorder", color=CORAL, ax=axes)
        axes.set_xlabel("Prevalence (%)")
        axes.set_ylabel("")
    return figure


def plot_scatter(snapshot, year):
    figure, axes = chart_axes(f"Anxiety and depression across countries, {year}")
    complete = snapshot.dropna(subset=["anxiety", "depression"])
    if complete.empty:
        empty_chart(axes)
    else:
        sns.scatterplot(data=complete, x="anxiety", y="depression", color=GREEN, s=55, alpha=0.8, ax=axes)
        axes.set_xlabel("Anxiety prevalence (%)")
        axes.set_ylabel("Depression prevalence (%)")
    return figure


def plot_correlation(correlation, year):
    figure, axes = chart_axes(f"Cross-country disorder correlations, {year}", (9, 7))
    if correlation.empty:
        empty_chart(axes, "Insufficient complete countries or varying disorder columns")
    else:
        sns.heatmap(correlation, vmin=-1, vmax=1, center=0, cmap="vlag", annot=True,
                    fmt=".2f", square=True, cbar_kws={"label": "Pearson correlation"}, ax=axes)
        labels = [textwrap.fill(name, width=14) for name in correlation.columns]
        axes.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
        axes.set_yticklabels(labels, rotation=0, fontsize=8)
    return figure


def plot_changes(changes, disorder_name, start_year, end_year, limit):
    title = f"{disorder_name}: largest absolute changes, {start_year}-{end_year}"
    figure, axes = chart_axes(title, (9, 6))
    valid = changes.dropna(subset=["change_pp"]).copy()
    if valid.empty:
        empty_chart(axes, "No comparable start/end observations")
    else:
        valid["magnitude"] = valid["change_pp"].abs()
        largest = valid.nlargest(limit, "magnitude").sort_values("change_pp")
        colors = [CORAL if change > 0 else TEAL for change in largest["change_pp"]]
        axes.barh(largest["entity_name"], largest["change_pp"], color=colors)
        axes.axvline(0, color="#444444", linewidth=1)
        axes.set_xlabel("Change in percentage points (end minus start)")
        axes.set_ylabel("")
    return figure