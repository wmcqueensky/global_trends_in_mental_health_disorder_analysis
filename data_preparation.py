"""Read only the seven-disorder prevalence section of the Kaggle CSV."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
GENERATED_DIR = PROJECT_DIR / "generated"
SOURCE_URL = "https://www.kaggle.com/datasets/thedevastator/uncover-global-trends-in-mental-health-disorder"
DATASET_HANDLE = "thedevastator/uncover-global-trends-in-mental-health-disorder/versions/2"
SOURCE_FILENAME = "Mental health Depression disorder Data.csv"
DISORDERS = {
    "Schizophrenia (%)": "schizophrenia",
    "Bipolar disorder (%)": "bipolar",
    "Eating disorders (%)": "eating",
    "Anxiety disorders (%)": "anxiety",
    "Drug use disorders (%)": "drug_use",
    "Depression (%)": "depression",
    "Alcohol use disorders (%)": "alcohol_use",
}
DISORDER_NAMES = {
    disorder_id: source_column.removesuffix(" (%)")
    for source_column, disorder_id in DISORDERS.items()
}


def read_prevalence_section(source):
    """Accept an open text file; stop at the next embedded CSV header."""
    reader = csv.DictReader(source)
    required_columns = ["Entity", "Code", "Year"] + list(DISORDERS)
    if reader.fieldnames is None:
        raise ValueError("The source file is empty.")
    for column in required_columns:
        if column not in reader.fieldnames:
            raise ValueError(f"The source is missing the column: {column}")

    rows = []
    for row in reader:
        if row["Entity"] == "Entity" and row["Code"] == "Code" and row["Year"] == "Year":
            break
        if None in row or None in row.values():
            raise ValueError(f"Unexpected number of fields near CSV line {reader.line_num}.")
        rows.append(row)
    if not rows:
        raise ValueError("No prevalence rows were found before the next header.")
    return rows


def get_source_path(local_path=None):
    """Use a supplied CSV or download the selected file from Kaggle version 2."""
    if local_path is not None:
        return Path(local_path).expanduser().resolve()

    import kagglehub

    return Path(kagglehub.dataset_download(DATASET_HANDLE, path=SOURCE_FILENAME))


def classify_entity(code):
    """The source code is a practical grouping rule, not a geography standard."""
    if code == "OWID_WRL":
        return "world"
    elif len(code) == 3 and code.isascii() and code.isalpha() and code.isupper():
        return "country_or_territory"
    else:
        return "aggregate_or_subnational"


def clean_data(rows):
    """Return a wide DataFrame and an audit; do not invent missing measurements."""
    import pandas as pd

    columns = ["Entity", "Code", "Year"] + list(DISORDERS)
    data = pd.DataFrame(rows).loc[:, columns].copy()
    report = {"input_section_rows": len(data)}
    for column in ["Entity", "Code"]:
        data[column] = data[column].fillna("").astype(str).str.strip()

    years = pd.to_numeric(data["Year"], errors="coerce")
    valid_year = years.between(1990, 2017) & years.mod(1).eq(0)
    valid_entity = data["Entity"].ne("")
    report["invalid_year_rows"] = int((~valid_year).sum())
    report["blank_entity_rows"] = int((~valid_entity).sum())
    report["removed_identity_or_year_rows"] = int((~(valid_year & valid_entity)).sum())
    data = data.loc[valid_year & valid_entity].copy()
    data["Year"] = years.loc[data.index].astype(int)

    report["measurement_checks"] = {}
    for source_column in DISORDERS:
        text = data[source_column].fillna("").astype(str).str.strip()
        values = pd.to_numeric(text, errors="coerce")
        valid = values.between(0, 100)
        report["measurement_checks"][source_column] = {
            "blank_values": int(text.eq("").sum()),
            "invalid_nonblank_values": int((text.ne("") & ~valid).sum()),
        }
        data[source_column] = values.where(valid)

    no_measurements = data[list(DISORDERS)].isna().all(axis=1)
    report["removed_rows_without_measurements"] = int(no_measurements.sum())
    data = data.loc[~no_measurements].copy()
    report["identical_duplicate_rows"] = int(data.duplicated().sum())
    data = data.drop_duplicates()
    if data.empty:
        raise ValueError("No valid prevalence observations remain after cleaning.")
    if data.duplicated(["Entity", "Year"]).any():
        raise ValueError("Conflicting rows for the same entity and year; inspect the source.")
    if data.groupby("Entity")["Code"].nunique().gt(1).any():
        raise ValueError("An entity has conflicting codes; inspect the source.")

    data["entity_type"] = data["Code"].apply(classify_entity)
    rename_columns = {"Entity": "entity_name", "Code": "code", "Year": "year"}
    rename_columns.update(DISORDERS)
    data = data.rename(columns=rename_columns)
    data = data.sort_values(["entity_name", "year"]).reset_index(drop=True)
    report["cleaned_rows"] = len(data)
    report["entities"] = int(data["entity_name"].nunique())
    report["entity_counts_by_type"] = data.drop_duplicates("entity_name")["entity_type"].value_counts().to_dict()
    report["first_year"] = int(data["year"].min())
    report["last_year"] = int(data["year"].max())
    report["missing_measurements_after_cleaning"] = data[list(DISORDERS.values())].isna().sum().to_dict()
    return data, report


def read_cleaned_data():
    """Read the generated file with consistent text types on Windows and macOS."""
    import pandas as pd

    path = GENERATED_DIR / "cleaned_data.csv"
    if not path.exists():
        raise FileNotFoundError("Run python data_preparation.py first.")
    data = pd.read_csv(path, dtype={"entity_name": str, "code": str, "entity_type": str})
    data["code"] = data["code"].fillna("")
    return data


def to_long_data(data):
    """One observation is one entity, one year, and one disorder."""
    long_data = data.melt(
        id_vars=["entity_name", "code", "entity_type", "year"],
        value_vars=list(DISORDERS.values()),
        var_name="disorder_id",
        value_name="prevalence_pct",
    )
    return long_data.dropna(subset=["prevalence_pct"]).reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="Use an existing CSV instead of downloading.")
    arguments = parser.parse_args()
    source_path = get_source_path(arguments.csv)
    with source_path.open(encoding="utf-8-sig", newline="") as source:
        rows = read_prevalence_section(source)
    cleaned, report = clean_data(rows)
    with source_path.open("rb") as source:
        report["source_sha256"] = hashlib.file_digest(source, "sha256").hexdigest()
    report["source_url"] = SOURCE_URL
    report["dataset_handle"] = DATASET_HANDLE
    report["source_mode"] = "local file (version not independently verified)" if arguments.csv else "Kaggle version 2"
    GENERATED_DIR.mkdir(exist_ok=True)
    cleaned.to_csv(GENERATED_DIR / "cleaned_data.csv", index=False)
    with (GENERATED_DIR / "cleaning_report.json").open("w", encoding="utf-8") as destination:
        json.dump(report, destination, indent=2)
    print(json.dumps(report, indent=2))
    print(f"\nGenerated files: {GENERATED_DIR}")


if __name__ == "__main__":
    main()