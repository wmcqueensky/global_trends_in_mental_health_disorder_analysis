"""Read-only Streamlit presentation layer. Start with streamlit run app.py."""

import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

from analysis import calculate_changes, calculate_correlation_matrix, make_wide_data
from data_preparation import DISORDER_NAMES, SOURCE_URL
from database import SUMMARY_SQL, fetch_country_summary, fetch_observations, fetch_top_countries
from visualizations import (
    plot_changes, plot_correlation, plot_disorder_boxplot, plot_distribution,
    plot_ranking, plot_scatter, plot_trends,
)


@st.cache_data(ttl=600, show_spinner=False)
def load_observations():
    return fetch_observations(dict(st.secrets["database"]))


@st.cache_data(ttl=600, show_spinner=False)
def load_summary(countries, disorder_id, start_year, end_year):
    return fetch_country_summary(dict(st.secrets["database"]), countries, disorder_id, start_year, end_year)


@st.cache_data(ttl=600, show_spinner=False)
def load_ranking(countries, disorder_id, year, limit):
    return fetch_top_countries(dict(st.secrets["database"]), countries, disorder_id, year, limit)


def show_figure(figure):
    st.pyplot(figure, use_container_width=True)
    plt.close(figure)


def main():
    st.set_page_config(page_title="Global Trends in Mental Health Disorder", layout="wide")
    sns.set_theme(style="whitegrid", font_scale=1.0)
    st.title("Global Trends in Mental Health Disorder")
    st.caption(f"Reported prevalence, 1990-2017 | [Kaggle source]({SOURCE_URL}) | Supabase PostgreSQL")

    try:
        observations = load_observations()
    except (FileNotFoundError, KeyError):
        st.error("Database configuration is missing.")
        st.stop()
    except Exception:
        st.error("The database is unavailable or its project tables are not ready.")
        st.stop()
    if observations.empty:
        st.warning("The database contains no observations.")
        st.stop()

    data = make_wide_data(observations)
    country_data = data.loc[data["entity_type"].eq("country_or_territory")]
    country_options = sorted(country_data["entity_name"].unique())
    if not country_options:
        st.warning("No country or territory observations are available.")
        st.stop()
    first_year = int(data["year"].min())
    last_year = int(data["year"].max())

    with st.sidebar:
        st.header("Selection")
        disorder_id = st.selectbox("Disorder", list(DISORDER_NAMES), index=5,
                                   format_func=DISORDER_NAMES.get, key="disorder")
        if first_year == last_year:
            start_year, end_year = first_year, last_year
        else:
            start_year, end_year = st.slider("Years", first_year, last_year,
                                             (first_year, last_year), key="years")
        scope = st.radio("Country scope", ["All", "Selection"], horizontal=True, key="country_scope")
        if scope == "All":
            countries = country_options
        else:
            defaults = [name for name in ["Poland", "Germany", "France"] if name in country_options]
            countries = st.multiselect("Countries/territories", country_options,
                                       default=defaults or country_options[:3], key="country_selection")
        limit = int(st.number_input("Ranking size", min_value=1, max_value=15, value=10, step=1))
        include_world = st.checkbox("World reference", value=True)

    if not countries:
        st.warning("No countries or territories selected.")
        st.stop()

    cohort = country_data.loc[
        country_data["entity_name"].isin(countries) & country_data["year"].between(start_year, end_year)
    ]
    snapshot = cohort.loc[cohort["year"].eq(end_year)]
    values = snapshot[disorder_id].dropna()
    disorder_name = DISORDER_NAMES[disorder_id]
    metric_columns = st.columns(3)
    metric_columns[0].metric("Countries with selected-disorder data", len(values))
    metric_columns[1].metric("Snapshot year", str(end_year))
    median = f"{values.median():.2f}%" if not values.empty else "N/A"
    metric_columns[2].metric("Country median prevalence", median)

    try:
        ranking = load_ranking(tuple(countries), disorder_id, end_year, limit)
        summary = load_summary(tuple(countries), disorder_id, start_year, end_year)
    except Exception:
        st.error("The selected SQL results are temporarily unavailable.")
        st.stop()

    overview, trends, relationships = st.tabs(["Overview", "Trends", "Relationships"])
    with overview:
        show_figure(plot_ranking(ranking, disorder_name, end_year))
        show_figure(plot_distribution(snapshot, disorder_id, end_year))
        show_figure(plot_disorder_boxplot(snapshot, end_year))
        st.caption("Distributions give each country/territory equal weight. The box plot covers all seven disorders.")
        with st.expander("SQL summary: country averages over the selected years"):
            st.dataframe(summary.round(3), hide_index=True, use_container_width=True)
            st.code(SUMMARY_SQL, language="sql")

    with trends:
        defaults = [name for name in ["Poland", "Germany", "France"] if name in countries]
        comparisons = st.multiselect("Trend comparison", countries, default=defaults or countries[:3],
                                     max_selections=5, key="trend_countries")
        trend_names = list(comparisons)
        if include_world:
            trend_names.extend(observations.loc[observations["entity_type"].eq("world"), "entity_name"].unique())
        trend_data = observations.loc[
            observations["entity_name"].isin(trend_names)
            & observations["disorder_id"].eq(disorder_id)
            & observations["year"].between(start_year, end_year)
        ]
        show_figure(plot_trends(trend_data, disorder_name))
        st.caption("World is the source-provided series, not an average of the selected countries.")
        changes = calculate_changes(cohort, countries, disorder_id, start_year, end_year)
        show_figure(plot_changes(changes, disorder_name, start_year, end_year, limit))
        st.caption("Little change means within +/-0.1 percentage points. This descriptive threshold is not a significance test.")
        st.dataframe(changes.round(3), hide_index=True, use_container_width=True)

    with relationships:
        show_figure(plot_scatter(snapshot, end_year))
        correlation, count, excluded = calculate_correlation_matrix(cohort, end_year)
        show_figure(plot_correlation(correlation, end_year))
        st.caption(f"Correlation cohort: {count} countries/territories with all seven measurements in {end_year}.")
        if excluded:
            st.caption("Constant columns excluded: " + ", ".join(DISORDER_NAMES[name] for name in excluded))
        st.caption("These views cover multiple disorders. Country-level associations do not establish causes or individual comorbidity.")

    st.caption("Historical prevalence estimates, not current diagnoses. Disorder percentages overlap and must not be added together.")


if __name__ == "__main__":
    main()