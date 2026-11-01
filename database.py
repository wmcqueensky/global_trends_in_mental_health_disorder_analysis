"""Create this project's Supabase tables manually; query them from Streamlit."""

import argparse
import json
import re
import tomllib

from data_preparation import DISORDER_NAMES, DISORDERS, GENERATED_DIR, PROJECT_DIR, read_cleaned_data, to_long_data


OBSERVATIONS_SQL = """
SELECT entities.entity_name, entities.code, entities.entity_type, prevalence.year,
       disorders.disorder_id, disorders.disorder_name, prevalence.prevalence_pct
FROM mental_health.prevalence AS prevalence
JOIN mental_health.entities AS entities ON prevalence.entity_name = entities.entity_name
JOIN mental_health.disorders AS disorders ON prevalence.disorder_id = disorders.disorder_id
WHERE prevalence.year BETWEEN %s AND %s
ORDER BY entities.entity_name, prevalence.year, disorders.disorder_id
"""

SUMMARY_SQL = """
SELECT entities.entity_name, disorders.disorder_name,
       COUNT(*) AS years_observed,
             AVG(prevalence.prevalence_pct) AS mean_pct,
             MIN(prevalence.prevalence_pct) AS minimum_pct,
             MAX(prevalence.prevalence_pct) AS maximum_pct
FROM mental_health.prevalence AS prevalence
JOIN mental_health.entities AS entities ON prevalence.entity_name = entities.entity_name
JOIN mental_health.disorders AS disorders ON prevalence.disorder_id = disorders.disorder_id
WHERE entities.entity_type = 'country_or_territory'
    AND entities.entity_name = ANY(%s)
    AND disorders.disorder_id = %s
    AND prevalence.year BETWEEN %s AND %s
GROUP BY entities.entity_name, disorders.disorder_name
ORDER BY mean_pct DESC, entities.entity_name
"""

RANKING_SQL = """
SELECT entities.entity_name, prevalence.prevalence_pct
FROM mental_health.prevalence AS prevalence
JOIN mental_health.entities AS entities ON prevalence.entity_name = entities.entity_name
JOIN mental_health.disorders AS disorders ON prevalence.disorder_id = disorders.disorder_id
WHERE entities.entity_type = 'country_or_territory'
    AND entities.entity_name = ANY(%s)
    AND disorders.disorder_id = %s AND prevalence.year = %s
ORDER BY prevalence.prevalence_pct DESC, entities.entity_name
LIMIT %s
"""


def get_connection(settings):
    """Connection details stay outside source code; never print settings."""
    import psycopg

    options = dict(settings)
    for field in ["host", "user", "password", "dbname"]:
        if not options.get(field):
            raise ValueError(f"Missing database setting: {field}")
    options.setdefault("sslmode", "require")
    if options["sslmode"] not in ["require", "verify-ca", "verify-full"]:
        raise ValueError("An encrypted database connection is required.")
    options["connect_timeout"] = 10
    return psycopg.connect(**options)


def local_settings(section):
    with (PROJECT_DIR / ".streamlit" / "secrets.toml").open("rb") as source:
        return tomllib.load(source)[section]


def create_tables(connection, source_sha256):
    """Refuse unrelated schemas or changed source files instead of replacing data."""
    from psycopg import sql

    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("Invalid source fingerprint. Run data_preparation.py again.")
    marker = "mental_health_course_v1:" + source_sha256
    with connection.cursor() as cursor:
        cursor.execute("SELECT obj_description(oid, 'pg_namespace') FROM pg_namespace WHERE nspname = 'mental_health'")
        existing = cursor.fetchone()
        if existing is not None and existing[0] != marker:
            raise ValueError("The mental_health schema already belongs to another source or project. Nothing was replaced.")
        if existing is None:
            cursor.execute("CREATE SCHEMA mental_health")
            cursor.execute(sql.SQL("COMMENT ON SCHEMA mental_health IS {}").format(sql.Literal(marker)))
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mental_health.entities (
                entity_name TEXT PRIMARY KEY,
                code TEXT,
                entity_type TEXT NOT NULL CHECK (entity_type IN
                    ('country_or_territory', 'world', 'aggregate_or_subnational'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mental_health.disorders (
                disorder_id TEXT PRIMARY KEY,
                disorder_name TEXT NOT NULL UNIQUE,
                source_column TEXT NOT NULL UNIQUE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mental_health.prevalence (
                entity_name TEXT REFERENCES mental_health.entities(entity_name),
                disorder_id TEXT REFERENCES mental_health.disorders(disorder_id),
                year INTEGER NOT NULL CHECK (year BETWEEN 1990 AND 2017),
                prevalence_pct DOUBLE PRECISION NOT NULL CHECK (prevalence_pct BETWEEN 0 AND 100),
                PRIMARY KEY (entity_name, disorder_id, year)
            )
        """)
        cursor.execute("REVOKE ALL ON SCHEMA mental_health FROM PUBLIC, anon, authenticated")
        cursor.execute("REVOKE ALL ON ALL TABLES IN SCHEMA mental_health FROM PUBLIC, anon, authenticated")


def load_cleaned_data(settings, data, source_sha256):
    entities = data[["entity_name", "code", "entity_type"]].drop_duplicates()
    observations = to_long_data(data)[["entity_name", "disorder_id", "year", "prevalence_pct"]]
    disorders = []
    for source_column, disorder_id in DISORDERS.items():
        disorders.append((disorder_id, DISORDER_NAMES[disorder_id], source_column))

    with get_connection(settings) as connection:
        create_tables(connection, source_sha256)
        with connection.cursor() as cursor:
            cursor.executemany("""
                INSERT INTO mental_health.entities (entity_name, code, entity_type)
                VALUES (%s, %s, %s) ON CONFLICT (entity_name) DO NOTHING
            """, entities.itertuples(index=False, name=None))
            cursor.executemany("""
                INSERT INTO mental_health.disorders (disorder_id, disorder_name, source_column)
                VALUES (%s, %s, %s) ON CONFLICT (disorder_id) DO NOTHING
            """, disorders)
            cursor.executemany("""
                INSERT INTO mental_health.prevalence (entity_name, disorder_id, year, prevalence_pct)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (entity_name, disorder_id, year)
                DO UPDATE SET prevalence_pct = EXCLUDED.prevalence_pct
            """, observations.itertuples(index=False, name=None))
    return len(observations)


def run_query(settings, query, parameters):
    import pandas as pd

    with get_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            cursor.execute(query, parameters)
            columns = [column.name for column in cursor.description]
            return pd.DataFrame(cursor.fetchall(), columns=columns)


def fetch_observations(settings, start_year=1990, end_year=2017):
    return run_query(settings, OBSERVATIONS_SQL, (start_year, end_year))


def fetch_country_summary(settings, countries, disorder_id, start_year, end_year):
    return run_query(settings, SUMMARY_SQL, (list(countries), disorder_id, start_year, end_year))


def fetch_top_countries(settings, countries, disorder_id, year, limit):
    return run_query(settings, RANKING_SQL, (list(countries), disorder_id, year, int(limit)))


def verify_database(settings, data):
    """Check real joins, aggregate parity, and reader grants without testing writes."""
    import pandas as pd

    columns = ["entity_name", "disorder_id", "year", "prevalence_pct"]
    keys = columns[:3]
    expected = to_long_data(data)[columns].sort_values(keys).reset_index(drop=True)
    actual = fetch_observations(settings)[columns].sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(expected, actual, check_dtype=False, atol=1e-10, rtol=1e-10)
    countries = sorted(data.loc[data["entity_type"].eq("country_or_territory"), "entity_name"].unique())
    summary = fetch_country_summary(settings, countries, "depression", 1990, 2017)
    expected_means = data.loc[data["entity_name"].isin(countries)].groupby("entity_name")["depression"].mean().dropna()
    actual_means = summary.set_index("entity_name")["mean_pct"]
    pd.testing.assert_series_equal(expected_means.sort_index(), actual_means.sort_index(), check_names=False, check_dtype=False)
    privileges = run_query(settings, """
         SELECT table_info.relname, has_table_privilege(current_user, table_info.oid, 'SELECT') AS can_read,
             has_table_privilege(current_user, table_info.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS can_write
         FROM pg_class AS table_info JOIN pg_namespace AS schema_info ON table_info.relnamespace = schema_info.oid
         WHERE schema_info.nspname = 'mental_health' AND table_info.relkind = 'r'
    """, ())
    if len(privileges) != 3 or not privileges["can_read"].all() or privileges["can_write"].any():
        raise ValueError("Use a reader with SELECT on exactly the three project tables, and no write grants.")
    schema_grants = run_query(settings, "SELECT has_schema_privilege(current_user, 'mental_health', 'CREATE') AS can_create", ())
    if schema_grants.iloc[0]["can_create"]:
        raise ValueError("The dashboard reader must not have CREATE permission on the project schema.")
    print(f"PASS: {len(actual)} joined observations match the cleaned file; SQL averages match Pandas.")
    print("PASS: dashboard role can read but has no project-table write or schema-create grants.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify data and read-only grants using [database].")
    arguments = parser.parse_args()
    data = read_cleaned_data()
    if arguments.check:
        verify_database(local_settings("database"), data)
    else:
        with (GENERATED_DIR / "cleaning_report.json").open(encoding="utf-8") as source:
            report = json.load(source)
        count = load_cleaned_data(local_settings("setup_database"), data, report["source_sha256"])
        print(f"Loaded {count} observations into mental_health. Existing source keys were updated, not duplicated.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Database step failed ({type(error).__name__}).")
        if isinstance(error, (ValueError, FileNotFoundError, KeyError)):
            print(str(error))
        else:
            print("Check the README troubleshooting section. Connection details are not printed.")
        raise SystemExit(1) from None