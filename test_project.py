"""Small, reproducible checks using synthetic data, not network credentials."""

import csv
import importlib.util
import io
import unittest

from data_preparation import DISORDERS, classify_entity, clean_data, read_prevalence_section, to_long_data
from analysis import calculate_changes, calculate_correlation_matrix, classify_change


HAS_PANDAS = importlib.util.find_spec("pandas") is not None
HAS_PLOTS = HAS_PANDAS and all(
    importlib.util.find_spec(package) is not None for package in ["numpy", "matplotlib", "seaborn"]
)


def csv_source(rows):
    source = io.StringIO()
    writer = csv.writer(source)
    writer.writerow(["index", "Entity", "Code", "Year"] + list(DISORDERS))
    writer.writerows(rows)
    source.seek(0)
    return source


class ParserTests(unittest.TestCase):
    def test_stops_before_different_dataset_with_overlapping_year(self):
        source = csv_source([
            [0, "Poland", "POL", 1990] + [1.5] * 7,
            [1, "Entity", "Code", "Year", "Male", "Female", "Population", "", "", "", ""],
            [2, "Poland", "POL", 1990, 3, 5, 38000000, "", "", "", ""],
        ])
        rows = read_prevalence_section(source)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Depression (%)"], "1.5")

    def test_accepts_single_section_and_quoted_entity(self):
        source = csv_source([[0, "Country, example", "ABC", 2017] + [2] * 7])
        self.assertEqual(read_prevalence_section(source)[0]["Entity"], "Country, example")

    def test_rejects_wrong_header(self):
        with self.assertRaises(ValueError):
            read_prevalence_section(io.StringIO("Entity,Population\nPoland,38000000\n"))

    def test_rejects_malformed_row(self):
        with self.assertRaises(ValueError):
            read_prevalence_section(csv_source([[0, "Poland", "POL", 1990]]))

    def test_entity_classification(self):
        self.assertEqual(classify_entity("POL"), "country_or_territory")
        self.assertEqual(classify_entity("OWID_WRL"), "world")
        self.assertEqual(classify_entity(""), "aggregate_or_subnational")
        self.assertEqual(classify_entity("pol"), "aggregate_or_subnational")


class ChangeRuleTests(unittest.TestCase):
    def test_change_categories_and_boundary(self):
        self.assertEqual(classify_change(0.2), "Increased")
        self.assertEqual(classify_change(-0.2), "Decreased")
        self.assertEqual(classify_change(0.1), "Little change")
        self.assertEqual(classify_change(3.1 - 3.0), "Little change")
        self.assertEqual(classify_change(float("nan")), "Insufficient data")
        with self.assertRaises(ValueError):
            classify_change(1, -1)


@unittest.skipUnless(HAS_PANDAS, "Install requirements.txt to run Pandas tests.")
class CleaningTests(unittest.TestCase):
    def test_preserves_valid_values_and_reports_rejections(self):
        rows = read_prevalence_section(csv_source([
            [0, " Poland ", " POL ", 1990, "", "bad", -1, 101, "inf", 2.5, 0],
            [1, "Poland", "POL", 1990.5] + [1] * 7,
            [2, "", "POL", 1991] + [1] * 7,
            [3, "World", "OWID_WRL", 2017] + [3] * 7,
        ]))
        cleaned, report = clean_data(rows)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(report["removed_identity_or_year_rows"], 2)
        self.assertEqual(report["missing_measurements_after_cleaning"]["bipolar"], 1)
        long_data = to_long_data(cleaned)
        self.assertEqual(len(long_data), 9)
        self.assertTrue(long_data["prevalence_pct"].between(0, 100).all())

    def test_removes_identical_duplicates_but_rejects_conflicts(self):
        rows = read_prevalence_section(csv_source([
            [0, "Poland", "POL", 2017] + [2] * 7,
            [1, "Poland", "POL", 2017] + [2] * 7,
        ]))
        cleaned, report = clean_data(rows)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(report["identical_duplicate_rows"], 1)
        rows[1]["Depression (%)"] = "3"
        with self.assertRaises(ValueError):
            clean_data(rows)

    def test_rejects_empty_valid_output(self):
        rows = read_prevalence_section(csv_source([[0, "Poland", "POL", 2018] + [1] * 7]))
        with self.assertRaises(ValueError):
            clean_data(rows)

    def test_retains_aggregate_with_missing_code(self):
        rows = read_prevalence_section(csv_source([[0, "Region", "", 2017] + [1] * 7]))
        cleaned, report = clean_data(rows)
        self.assertEqual(cleaned.iloc[0]["entity_type"], "aggregate_or_subnational")
        self.assertEqual(report["entities"], 1)

    def test_change_requires_both_exact_endpoints(self):
        rows = read_prevalence_section(csv_source([
            [0, "Poland", "POL", 1991] + [2] * 7,
            [1, "Poland", "POL", 2017] + [3] * 7,
        ]))
        data, _ = clean_data(rows)
        missing = calculate_changes(data, ["Poland"], "depression", 1990, 2017)
        self.assertEqual(missing.iloc[0]["trend"], "Insufficient data")
        valid = calculate_changes(data, ["Poland"], "depression", 1991, 2017)
        self.assertEqual(valid.iloc[0]["change_pp"], 1)
        same_year = calculate_changes(data, ["Poland"], "depression", 2017, 2017)
        self.assertEqual(same_year.iloc[0]["trend"], "No interval")

    def test_numpy_matrix_matches_corrcoef(self):
        import numpy as np

        rows = []
        for index, name in enumerate(["Alpha", "Beta", "Gamma", "Delta"]):
            values = [index + 1, (index + 1) ** 2, 4 - index, 2 * index + 1, index + 2, 5 - index, 0.5]
            rows.append([index, name, ["AAA", "BBB", "CCC", "DDD"][index], 2017] + values)
        data, _ = clean_data(read_prevalence_section(csv_source(rows)))
        correlation, count, excluded = calculate_correlation_matrix(data, 2017)
        expected = np.corrcoef(data[list(DISORDERS.values())[:-1]].to_numpy(dtype=float), rowvar=False)
        np.testing.assert_allclose(correlation.to_numpy(), expected, atol=1e-12)
        self.assertEqual(count, 4)
        self.assertEqual(excluded, ["alcohol_use"])
        empty, count, _ = calculate_correlation_matrix(data.iloc[:2], 2017)
        self.assertTrue(empty.empty)
        self.assertEqual(count, 2)


@unittest.skipUnless(HAS_PLOTS, "Install requirements.txt to run chart tests.")
class ChartTests(unittest.TestCase):
    def test_all_seven_figures_render(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from visualizations import (
            plot_changes, plot_correlation, plot_disorder_boxplot, plot_distribution,
            plot_ranking, plot_scatter, plot_trends,
        )

        rows = []
        countries = ["Poland", "France", "Germany", "Spain"]
        for country_index, country in enumerate(countries):
            for year in [1990, 2017]:
                values = [(country_index + 1) * 0.3 + metric_index * 0.1 + (year - 1990) * 0.01 for metric_index in range(7)]
                rows.append([len(rows), country, ["POL", "FRA", "DEU", "ESP"][country_index], year] + values)
        data, _ = clean_data(read_prevalence_section(csv_source(rows)))
        snapshot = data.loc[data["year"].eq(2017)]
        long_data = to_long_data(data)
        trend_data = long_data.loc[long_data["disorder_id"].eq("depression")]
        ranking = trend_data.loc[trend_data["year"].eq(2017)].nlargest(4, "prevalence_pct")
        changes = calculate_changes(data, countries, "depression", 1990, 2017)
        correlation, _, _ = calculate_correlation_matrix(data, 2017)
        figures = [
            plot_trends(trend_data, "Depression"),
            plot_ranking(ranking, "Depression", 2017),
            plot_distribution(snapshot, "depression", 2017),
            plot_disorder_boxplot(snapshot, 2017),
            plot_scatter(snapshot, 2017),
            plot_correlation(correlation, 2017),
            plot_changes(changes, "Depression", 1990, 2017, 4),
        ]
        for figure in figures:
            figure.canvas.draw()
            pixels = np.asarray(figure.canvas.buffer_rgba())
            self.assertGreater(float(pixels.std()), 0)
            plt.close(figure)

    def test_single_year_and_empty_figures_render(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from visualizations import plot_changes, plot_trends

        rows = read_prevalence_section(csv_source([[0, "Poland", "POL", 2017] + [2] * 7]))
        data, _ = clean_data(rows)
        single = to_long_data(data)
        single = single.loc[single["disorder_id"].eq("depression")]
        changes = calculate_changes(data, ["Poland"], "depression", 2017, 2017)
        figures = [plot_trends(single, "Depression"), plot_trends(single.iloc[:0], "Depression"),
                   plot_changes(changes, "Depression", 2017, 2017, 5)]
        self.assertEqual(figures[0].axes[0].lines[0].get_marker(), "o")
        for figure in figures:
            figure.canvas.draw()
            plt.close(figure)


if __name__ == "__main__":
    unittest.main()