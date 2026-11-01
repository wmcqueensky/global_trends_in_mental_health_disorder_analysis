# Global Trends in Mental Health Disorder

A small Python and SQL course project: Pandas cleaning, descriptive analysis,
NumPy matrix operations, Supabase PostgreSQL, and a Streamlit dashboard.

**Public Streamlit app URL: NOT DEPLOYED YET.** Replace this line with your actual
public app URL after completing Step 7. A transfer ZIP is not yet a final submission.

## 1. Research goal and source

**Question:** How did the reported prevalence of seven mental health disorders
change from 1990 to 2017, and how do countries and territories compare?

Supporting questions:
- Which countries had the largest depression changes between two selected years?
- How do disorder prevalence distributions differ in a selected year?
- Are country-level anxiety and depression prevalence associated in that year?

Dataset: [Global Trends in Mental Health Disorder on Kaggle](https://www.kaggle.com/datasets/thedevastator/uncover-global-trends-in-mental-health-disorder).
The downloader requests **version 2**, file `Mental health Depression disorder Data.csv`.
Kaggle credits **Amit**, linking to [the original contributor](https://data.world/amitd).
Retain this attribution. Kaggle lists the license as "Other (specified in description)";
do not assume a Creative Commons license. Check the original source's conditions
before publishing data-derived output. This project does not redistribute the CSV.

The CSV contains several different datasets concatenated together. The first
section contains the seven prevalence columns. Later sections contain different
measures, including population and counts, under embedded headers. Filtering the
whole file by year would incorrectly mix these measures. The parser stops at the
first embedded header; it does not depend on a hard-coded row number.

One cleaned row means one entity in one year. A measurement is a reported
prevalence percentage, not a population count. The seven disorders are schizophrenia,
bipolar disorder, eating disorders, anxiety disorders, drug use disorders,
depression, and alcohol use disorders.

### Findings from the supplied source file

An independent standard-library audit on October 31, 2026 found:
- 6,468 first-section rows, covering 1990-2017; 45,276 nonmissing measurements.
- 195 countries/territories, 35 other aggregates or subnational units, and one World series.
- No missing/out-of-range metric cells or repeated entity-year keys in that section.
- In 2017, the highest depression values among the classified countries/territories
  were Greenland (6.234%), Lesotho (5.637%), and Morocco (5.414%).
- The largest 1990-2017 depression increases were Belgium (+0.477 percentage points),
  Guyana (+0.455), and Iran (+0.404).
- The source World depression series changed from 3.542% in 1990 to 3.441% in 2017,
  a decrease of approximately 0.101 percentage points.

These are historical, descriptive findings, not explanations of their causes.
Reproduce them with the preparation and analysis scripts. These source-audit results
do not substitute for running the Pandas pipeline, database checks, and dashboard.

### Interpretation limits

- The data stop at 2017; they do not describe the current situation or COVID-19.
- The CSV does not supply confidence intervals or enough methodological detail to
  establish diagnostic coverage or age-standardization. Do not invent these claims.
- A three-uppercase-letter source code is used to classify a country/territory;
  `OWID_WRL` identifies World. Other codes are grouped as aggregate/subnational.
  This practical rule is not an authoritative geopolitical classification.
- World and aggregates are excluded from country rankings, distributions, and correlations.
  The World trend uses the source series, never an unweighted country average.
- A country median or average is not a population-weighted global prevalence.
- Disorders may overlap. Their percentages must not be added into a total illness rate.
- Cross-country correlation is neither causation nor individual-level comorbidity.
- "Little change" means within +/-0.1 percentage points. This chosen descriptive
  tolerance is neither a clinical cutoff nor a statistical significance test.

## 2. Files and reading order

| File | Purpose | Main course concepts |
| --- | --- | --- |
| [data_preparation.py](data_preparation.py) | Source retrieval, section parsing, cleaning, audit, wide-to-long conversion | Files, dictionaries, loops, conditions, Pandas |
| [analysis.py](analysis.py) | Statistics, endpoint comparisons, correlation matrix | Functions, control flow, NumPy |
| [database.py](database.py) | Manual database setup/load and actual SQL queries | Keys, JOINs, WHERE, GROUP BY, aggregates, Python/SQL |
| [visualizations.py](visualizations.py) | Seven functions returning figures | Seaborn and Matplotlib |
| [app.py](app.py) | Read-only dashboard and filters | Streamlit, importing functions |
| [test_project.py](test_project.py) | Synthetic parser, cleaning, analysis, and figure checks | Optional verification; unittest assertions |
| [requirements.txt](requirements.txt) | Python dependencies | Reproducible environment |
| [.gitignore](.gitignore) | Excludes private files, datasets, and generated output | Safe source control |

Read in the order above. Run preparation, then analysis, then database setup/load,
then the app. Tests can run after installing packages and do not require Supabase.
Only `database.py` performs database writes, and only when explicitly run without
`--check`. Importing it or starting the dashboard never initializes tables.

Runtime files are created locally under `generated/`: `cleaned_data.csv` and
`cleaning_report.json`. They are not source files and must not go in the submission.

## 3. Set up on your private Mac

Nothing needs to be installed on your work laptop. Email the transfer ZIP to yourself
and extract it on your Mac. It contains the `mental_health_project` folder, including
the Git exclusion file, but no datasets, environment, database, or credentials.

1. Install **Python 3.12** for macOS from [python.org](https://www.python.org/downloads/macos/).
   Use a supported patch release. If you already use Homebrew, `brew install python@3.12`
   is another way to obtain an up-to-date Python 3.12. Do not use Apple's system Python.
2. Open the extracted folder in VS Code. The Microsoft Python extension is useful but
   not required for the terminal commands.
3. Open Terminal in the project folder. If extracted into Downloads:

```bash
cd ~/Downloads/mental_health_project
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

If the folder is elsewhere, change only the `cd` path, using quotes for spaces.
In each new terminal, return to that folder and run `source .venv/bin/activate`.
In VS Code, choose `.venv/bin/python` through **Python: Select Interpreter**.
Use the same Python version on Streamlit Community Cloud. Dependency ranges are
listed explicitly; the full stack has not been installed or runtime-tested on the
work laptop. The tests below must pass on the Mac before submission.

## 4. Prepare data, run tests, and explore

```bash
python -m unittest test_project -v
python data_preparation.py
python analysis.py
```

The downloader uses the official KaggleHub client. It downloads the selected CSV
to a local cache; "from a link" does not mean no bytes are downloaded. Once the data
are loaded into Supabase, the app reads Supabase and needs neither a CSV nor Kaggle
credentials on Streamlit Cloud.

If Kaggle requires sign-in or consent, accept its terms in your browser and follow
[KaggleHub's authentication instructions](https://github.com/Kaggle/kagglehub#authenticate).
Keep any token outside this project. A manual CSV download is also supported:

```bash
python data_preparation.py --csv "$HOME/Downloads/Mental health Depression disorder Data.csv"
```

Do not pass the Kaggle webpage URL to `pandas.read_csv`; it is HTML, not CSV.
The local-file mode records that its version has not been independently verified.

Preparation prints the cleaning report. It also:
- Trims entity names/codes and converts years/measurements to numbers.
- Rejects invalid years, fractional years, and blank entity names.
- Converts missing, nonnumeric, infinite, negative, or greater-than-100 percentages
  to missing values while keeping the other valid measurements in that row.
- Removes rows with no remaining measurements and identical duplicate rows.
- Rejects conflicting entity-year rows or conflicting entity codes instead of guessing.
- Reports missingness and exclusions. Counts for blank names and invalid years may
  overlap; `removed_identity_or_year_rows` gives the combined number removed.

No missing values are filled with zero, a mean, or an invented trend. The supplied
first section happens to be complete; synthetic tests exercise the missing-data logic.

`analysis.py` prints descriptive statistics across country-year observations,
the largest exact-endpoint depression changes, and a selected-year correlation
matrix. Missing endpoints yield "Insufficient data"; the code never substitutes
a different year. A single-year selection has no change interval.

## 5. Connect your existing Supabase project

Use your own Supabase account. Never paste passwords or API keys into chat, source
code, email, the README, or GitHub. This app connects to PostgreSQL, so it needs
database credentials, not an `anon` or service-role API key.

### A. Private setup connection

1. In Supabase, open your project and select **Connect > Session pooler**.
2. Copy the actual host, port, database name, and username from that dialog. Session
   mode normally uses port 5432 and supports IPv4. Do not guess the host from the region.
3. In the project folder create `.streamlit/secrets.toml` locally. Start with this
   template, replacing every placeholder privately:

```toml
[setup_database]
host = "YOUR_SESSION_POOLER_HOST"
port = 5432
dbname = "postgres"
user = "postgres.YOUR_PROJECT_REF"
password = "YOUR_DATABASE_PASSWORD"
sslmode = "require"

[database]
host = "YOUR_SESSION_POOLER_HOST"
port = 5432
dbname = "postgres"
user = "mental_health_reader.YOUR_PROJECT_REF"
password = "YOUR_SEPARATE_READER_PASSWORD"
sslmode = "require"
```

The second login does not exist until step C. Choose a separate strong password for
it using your password manager. Respect TOML quoting/escaping if passwords contain
quotes or backslashes; these structured settings do not need URL encoding.

`sslmode = "require"` requires encryption but does not verify the server's identity.
For certificate verification, download the root certificate from Supabase database
settings, use `sslmode = "verify-full"`, and add `sslrootcert` with its local path.
See [Supabase connection documentation](https://supabase.com/docs/guides/database/connecting-to-postgres).
Never disable TLS to work around an error.

### B. Load the cleaned data

```bash
python database.py
```

The script creates a separate **mental_health** schema with three tables. It does
not replace any existing tables or use the public schema. Do not add this schema
to Supabase's exposed Data API schemas. Schema and table privileges are revoked
from `PUBLIC`, `anon`, and `authenticated` for these new project objects only.
The app uses a private server-side database connection, not the public Data API.

| Table | Columns and purpose |
| --- | --- |
| `mental_health.entities` | `entity_name` primary key, source `code`, `entity_type` |
| `mental_health.disorders` | `disorder_id` primary key, readable `disorder_name`, original `source_column` |
| `mental_health.prevalence` | Entity/disorder foreign keys, `year`, `prevalence_pct`; composite entity-disorder-year primary key |

Each entity has many prevalence observations; each disorder has many observations.
Foreign keys prevent observations referring to nonexistent entities or disorders.
The composite primary key prevents duplicate observations. `CHECK` constraints
restrict years and percentage values.

The schema comment stores a project marker and source-file SHA-256 fingerprint.
If that schema already belongs to something else, or the source bytes have changed,
the script refuses to reuse it. Do not remove the protection or drop an existing
schema to fix this. Investigate the source mismatch first. A re-download with a
different line-ending format also changes the fingerprint.

Loading runs in one transaction: an error rolls back the project changes. With the
same cleaned source, running the loader again updates the existing observation
keys instead of duplicating them. It is not a general dataset migration tool.

### C. Create the read-only dashboard login

After loading, run the following in **Supabase SQL Editor**, replacing the password
placeholder privately. Use a new, strong password without a single quote, or apply
correct SQL string escaping. The login name should be new; if it already exists,
inspect it rather than dropping a role that might belong to another application.

```sql
CREATE ROLE mental_health_reader
    LOGIN PASSWORD 'REPLACE_WITH_YOUR_NEW_READER_PASSWORD'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

GRANT CONNECT ON DATABASE postgres TO mental_health_reader;
GRANT USAGE ON SCHEMA mental_health TO mental_health_reader;
GRANT SELECT ON mental_health.entities,
                mental_health.disorders,
                mental_health.prevalence
TO mental_health_reader;
```

Set the `[database]` password in the private TOML file to the password you just chose.
Through the session pooler the reader username is `mental_health_reader.YOUR_PROJECT_REF`,
not the setup username. The local loader alone uses `[setup_database]`.

### D. Verify the real database and rerun safety

```bash
python database.py --check
python database.py
python database.py --check
```

Both checks must pass. They compare all joined SQL observations with the cleaned
file, compare SQL depression averages with Pandas, and verify that the dashboard
role has SELECT but no write or schema-create grants on the project objects.
The supplied source should yield 45,276 observations on both runs, not twice that
number. No credentials or connection strings are printed.

After setup, you can remove the `[setup_database]` section from the local secrets
file unless you need to run the loader again. **Never put that section in Cloud secrets.**

## 6. Run and check the dashboard

```bash
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, normally http://localhost:8501.
If that port is occupied, use `python -m streamlit run app.py --server.port 8502`.
Stop the server with Ctrl+C. An active internet connection and an available Supabase
project are required. The app does not silently fall back to a local CSV.

Seven figures are available across three tabs:

| Tab | Figures | Scope |
| --- | --- | --- |
| Overview | Prevalence ranking, histogram, seven-disorder box plot | Selected cohort, end year of the range |
| Trends | Country trend lines, largest absolute endpoint-change bars | Selected disorder and year range |
| Relationships | Anxiety/depression scatter, seven-disorder correlation heatmap | Selected cohort, end year |

The disorder selector applies to the ranking, histogram, trend, change, and SQL
summary. Box plots and correlations deliberately cover multiple disorders; their
titles say so. World is an optional trend reference only. Country comparisons are
limited to five trend lines to keep the figure readable. A ranking is within the
selected cohort, not necessarily all countries.

The SQL summary under Overview is computed using the real three-table JOIN and
`COUNT`, `AVG`, `MIN`, and `MAX`. Its averages are over each country's observed
years, not global averages. Query results are cached for ten minutes. Restart the
local app or clear/reboot its Cloud cache after reloading the database if needed.

Manual checks before submission:
- Change the disorder, cohort, and years; verify the relevant plots and summary change.
- Select no countries: expect a warning rather than a traceback.
- Select one country: correlations should report insufficient data.
- Select a single year: the trend has markers and change analysis has no interval.
- Toggle World: it must affect only the trend comparison.
- Try a narrow browser window/mobile view and a desktop window; check axes and labels.
- Temporarily use an invalid reader password locally: expect a generic connection
  error, never a password or raw connection traceback. Restore the correct password.

## 7. Deploy to Streamlit Community Cloud

Deployment requires your GitHub, Supabase, and Streamlit accounts. It cannot be
completed by the transfer ZIP alone.

1. Create a GitHub repository containing only the project source files, this README,
   requirements, and `.gitignore`. Put `app.py` at the repository root. You can use
   GitHub's web upload or VS Code's Publish to GitHub command after checking the
   staged files. Never upload `.streamlit/secrets.toml`, `.venv`, `generated`, or
   the original CSV. Git ignore rules do not protect manual browser uploads.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app from
   that repository, choose its actual branch, and set the entrypoint to `app.py`.
3. In advanced settings choose Python 3.12, matching the local environment.
4. Paste **only the `[database]` section** into Cloud's Secrets settings. It must use
   the dedicated reader login. Do not upload a secrets file or supply setup/Kaggle keys.
5. Deploy. Verify that the app can query Supabase and render all seven default charts.
6. Make the app publicly accessible and open its public URL in a signed-out browser.
   Copy the actual working URL into the public app URL line at the top of this README,
   update the GitHub README, and rebuild the submission ZIP.

Official guide: [Streamlit Cloud secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).
If the free Supabase project is paused, resume it before presenting. Recheck the
public app shortly before the defense; a previously successful deployment does
not guarantee the database is still available.

## 8. Understand the code for the oral defense

### Python and Pandas

`DISORDERS` is a dictionary mapping verbose CSV column names to short database IDs.
`read_prevalence_section` uses `csv.DictReader`, a `for` loop, and `break` to stop
at the next schema. The CSV parser handles quoted commas correctly.

`clean_data` returns two objects: a DataFrame and an audit dictionary. Boolean masks
select valid rows with `.loc`. `pd.to_numeric(errors="coerce")` turns invalid numeric
text into missing values. `.where` retains only valid percentages. `.copy` makes
the intended editing step explicit. No arbitrary imputation is needed.

`.melt` changes seven disorder columns into two columns, `disorder_id` and
`prevalence_pct`. The row count becomes up to seven times larger; missing individual
measurements are removed. `.pivot` reverses this layout for charts.

`calculate_changes` loops over countries, finds both exact years, subtracts start
from end, and calls `classify_change`. For example, 4% to 5% is **+1 percentage
point**, not +1 percent relative growth. `math.isclose` avoids a floating-point
rounding artifact misclassifying a value exactly at the chosen tolerance.

### NumPy matrix exercise

The selected-year matrix has one row per complete country/territory and seven
columns. At least three complete rows are required; constant columns are excluded.
These lines in `calculate_correlation_matrix` perform the core calculation:

```python
standardized = (values - values.mean(axis=0)) / deviations[varying]
correlation = standardized.T @ standardized / (country_count - 1)
```

`axis=0` means column-wise means. Broadcasting applies each column's mean and sample
standard deviation to all of its rows. `.T` transposes the matrix. `@` multiplies
matrices, producing one entry per pair of disorders. Dividing by the number of
countries minus one gives the sample correlation matrix. `ddof=1` makes the standard
deviation use the same sample denominator. The test compares this calculation with
`numpy.corrcoef`. This is a descriptive matrix operation, not a predictive model.

### SQL and database connection

The JOIN follows the entity and disorder foreign keys to add names to each numeric
observation. `WHERE` filters records before `GROUP BY`; `AVG` then summarizes each
country. `ORDER BY` and `LIMIT` produce the ranking.

`%s` is a psycopg value placeholder. Values are supplied separately, never pasted
into SQL using f-strings. PostgreSQL's `= ANY(%s)` matches any country in a supplied
Python list. The one use of `sql.Literal` safely quotes the schema's metadata comment;
ordinary query filters use bound parameters.

`with get_connection(...)` commits a successful setup transaction and rolls back an
unsuccessful one. `ON CONFLICT` handles repeated keys without duplicate inserts.
The SHA-256 value is a source-file fingerprint, not a password or encryption scheme.
The reader connection is deliberately separate from the setup connection.

### Streamlit and plotting

Changing a widget reruns the script. `st.cache_data` avoids repeating the same query
on every rerun, with a ten-minute lifetime. The plot functions return figures rather
than opening desktop windows. `st.pyplot` displays them and `plt.close` releases them.
Error handling keeps connection details out of the public interface.

Practice answering these in your own words:
1. Why is selecting only years 1990-2017 insufficient to clean the original file?
2. Why should a missing value not become zero?
3. What do the parser's loop, condition, and `break` do?
4. What is the difference between `.melt` and `.pivot` here?
5. What does the composite primary key prevent? What does a foreign key prevent?
6. Why does the SQL summary need JOINs and GROUP BY?
7. Why is the World line not an average of the selected countries?
8. What does the matrix multiplication calculate, and why exclude constant columns?
9. Why is +1 percentage point different from +1 percent relative growth?
10. Why must the publicly deployed app not use the setup database login?

AI assistance is allowed by the course, but understanding the submitted code is
your responsibility. Review and adapt the explanation and findings honestly; do
not claim unaided authorship or memorize code you cannot explain.

## 9. Verification status and submission

Checks performed on the work laptop:
- First-section parser, entity rules, and change-category tests ran successfully.
- A standard-library audit of the actual source produced the findings above.
- Python syntax checks ran without installing project packages.

Still required on the private Mac:

```bash
python -m pip check
python -m unittest test_project -v
python -m compileall -q app.py data_preparation.py analysis.py database.py visualizations.py test_project.py
python database.py --check
```

All 14 unit tests should run without skips after requirements are installed. Tests
use small synthetic datasets and include drawing all seven figures and checking
nonblank canvas pixels. Missing packages cause clearly labeled skips, not proof
that the corresponding features work. The database and signed-out public-app
checks are separate. Browser responsiveness and real Cloud deployment still need
the manual checks above. No live Supabase connection has been tested here.

The final ZIP must contain source code plus the explicitly required README and
requirements file. From the project folder, after adding the real public URL, run:

```bash
python -m zipfile -c ../Surname_Firstname_StudentNumber_Project.zip app.py data_preparation.py analysis.py database.py visualizations.py test_project.py README.md requirements.txt
python -m zipfile -l ../Surname_Firstname_StudentNumber_Project.zip
```

Replace the surname, first name, and student number in the command. This explicit
file list avoids secrets/data even if they exist locally. It creates a new archive
instead of appending to an older ZIP. The final archive contains eight files;
`.gitignore` is useful for the transfer/GitHub repository but is not needed in Moodle.
Do not ZIP the entire working folder using Finder, which could include private or
generated files. Never include a CSV, JSON audit, database file, token, `.venv`,
`.streamlit/secrets.toml`, `__pycache__`, `.DS_Store`, or `__MACOSX`.

**Upload that final ZIP to Moodle by January 6, 2027, 23:59.** Emailing the transfer
ZIP to your own Mac is fine; emailing it to the professor is not submission.
No Moodle submission means automatic course failure. The README must contain
the working public Streamlit URL before the final archive is created.

### Requirement checklist

| Course requirement | Project evidence |
| --- | --- |
| Real dataset and research goal | Section 1; versioned Kaggle source |
| Pandas/NumPy cleaning and types | Preparation functions and generated audit |
| EDA | Analysis statistics, actual descriptive findings, distributions |
| Matrix operations | Standardization, transpose, and matrix multiplication |
| Modular functions and explicit control flow | Parser, cleaner, entity classification, endpoint changes |
| Relational database and SQL | Three Supabase tables, JOINs, filtering, grouped aggregates |
| 5-10 distinct plots | Seven Seaborn/Matplotlib figures |
| Interactive Streamlit | Country, disorder, year, ranking, and trend selections |
| Deployed app and public link | User action required in Step 7 |
| Source-only ZIP, README, dependencies | Explicit packaging command above |

### Troubleshooting

| Symptom | Action |
| --- | --- |
| `python3.12` not found | Finish the Python installation and reopen Terminal; check the installed version's command. |
| Missing Python module or skipped tests | Activate `.venv`, then install requirements with that environment's `python -m pip`. |
| HTTPS certificate error after a python.org Mac installation | Run the installer's `Install Certificates.command`; keep certificate validation enabled. |
| Kaggle authentication/download failure | Accept dataset terms, configure KaggleHub privately, or use `--csv` with the original file. |
| Missing generated file | Run preparation before analysis or database setup. |
| Invalid database setting or TOML syntax | Check section names, placeholders, quote escaping, and the private file's exact location. |
| Authentication failed / tenant not found | Recheck the exact session-pooler host, role.PROJECT_REF username, role password, and project status. |
| Timeout | Confirm Supabase is running, its network restrictions permit your client, and the session pooler is reachable. |
| Schema already belongs to another source/project | Inspect the existing schema and source fingerprint; do not overwrite or drop it automatically. |
| App shows no database configuration | Use `[database]` in the local secrets file or Cloud's Secrets settings, then restart. |
| Read-only check fails | Use the dedicated reader, not `postgres`; review grants in Step 5. |
| Public app is inaccessible | Verify Cloud sharing and test signed out; an owner-only preview is not a public deployment. |# global_trends_in_mental_health_disorder_analysis
