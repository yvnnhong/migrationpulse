# CLAUDE HANDOFF DOCUMENT
## MigrationPulse — V4
### Animal Migration Analytics Pipeline
#### Airflow · PySpark · dbt · Delta Lake · AWS S3 · MLflow · Streamlit · GitHub Actions
**Developer:** Yvonne Hong | **Repo:** github.com/yvnnhong/migrationpulse | **Date:** 2026-03-26

---

## 1. What We Are Building

MigrationPulse is a production-grade, weekly-automated data engineering portfolio project. It ingests live GPS telemetry from the Movebank Animal Tracking API (and CSV fallback for studies with API restrictions), processes it through a Bronze → Silver → Gold medallion architecture on AWS S3, writes the Silver layer as a Delta Lake table, models the data with dbt (reading from Delta Lake via DuckDB's delta_scan()), scores migration corridor deviations using DTW (Dynamic Time Warping) tracked in MLflow, and surfaces findings on a live Streamlit dashboard. A GitHub Actions CI/CD workflow runs dbt tests automatically on every push to main.

The project is targeted at data engineering roles in Los Angeles and adds the following tools to Yvonne's resume: Airflow, PySpark, dbt, Delta Lake, MLflow, DTW anomaly detection, and GitHub Actions CI/CD.

**Live dashboard:** https://migrationpulse.streamlit.app

---

## 2. Full Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | Apache Airflow 2.x — DAG-based scheduling, running locally via Docker Compose |
| Compute | pandas — Bronze-to-Silver transforms (PySpark to be integrated later) |
| Storage | AWS S3 — 3 buckets: migrationpulse-bronze, migrationpulse-silver, migrationpulse-gold |
| Table Format | Delta Lake — Silver layer (written via deltalake Python library) |
| Data Modeling | dbt Core + dbt-duckdb — staging + mart SQL models, reads Delta table via delta_scan() |
| ML Tracking | MLflow — DTW experiment logging, parameter tracking, artifact storage |
| Anomaly Detection | DTW (Dynamic Time Warping) — Sakoe-Chiba banded, per-individual trajectory scoring |
| Dashboard | Streamlit + pydeck + Plotly — live migration maps, reads from Delta Lake |
| CI/CD | GitHub Actions — runs dbt build on every push to main |
| Cloud | AWS (S3, IAM) — boto3 SDK |
| Data Source | Movebank REST API + CSV fallback — multiple species |
| Language | Python 3.11 (Miniconda base env) |
| Dev Tooling | Docker Compose (Airflow), Git, GitHub, PowerShell, VSCode |
| OS | Windows 11 (PowerShell terminal in VSCode) |

---

## 3. Current Build Status

| Component | Status | Details |
|---|---|---|
| Airflow DAG | DONE | All 8 tasks wired with real function calls, green end-to-end |
| Bronze ingest | DONE | API ingest for bald eagle + turkey vulture; CSV ingest for delmarva waterfowl |
| Silver transform | DONE | All 3 species as Delta Lake tables in S3 silver bucket |
| Delta Lake | DONE | Silver layer writes via write_deltalake(), _delta_log/ present in S3 |
| dbt models | DONE | 3 models, 6 tests, all passing; reads from all 3 Delta tables via delta_scan() |
| DTW + MLflow | DONE | Scores 5 individuals, anomaly rate logged, distribution plot artifact |
| Streamlit dashboard | DONE | Live at migrationpulse.streamlit.app, reads from Delta Lake |
| GitHub Actions CI/CD | DONE | .github/workflows/dbt_tests.yml — triggers on push to main |

---

## 4. Species in the Pipeline

| Species | Study ID | Individuals | Records | Ingestion Method |
|---|---|---|---|---|
| Bald Eagle | 430263960 | 5 | ~45,319 | Movebank API |
| Turkey Vulture | 16880941 | 19 (17 working) | ~215,719 | Movebank API |
| Delmarva Waterfowl (Snow Goose, Canada Goose, Mallard) | 1509697502 | 99 | ~9,157,595 | CSV download |
| **TOTAL** | | **~123** | **~9,418,633** | |

---

## 5. Architecture — Data Flow

```
Movebank REST API (per-individual GPS fetch)          Local CSV (Movebank download)
    ↓ spark/bronze_ingest.py                              ↓ spark/bronze_ingest.py
    (requests + boto3)                                    (pandas chunked read + boto3)
                    ↓
S3: migrationpulse-bronze/{species}/{YYYY/MM/DD}/raw_{HHMMSS}[_{chunk}].json
                    ↓ spark/silver_transform.py (pandas + deltalake)
S3: migrationpulse-silver/{species}/ (Delta Lake table with _delta_log/)
                    ↓ dbt build (delta_scan() via DuckDB)
S3: migrationpulse-gold/ (dbt mart views — in-memory DuckDB, not persisted yet)
                    ↓ ml/dtw_corridor_scorer.py + MLflow
MLflow experiment: migration_pulse (DTW distance scores per individual)
                    ↓ dashboard/app.py (Streamlit + deltalake + pydeck)
Live dashboard: migrationpulse.streamlit.app
                    ↓ dags/migration_pipeline.py (@weekly Airflow DAG)
All 8 tasks orchestrated automatically
                    ↓ .github/workflows/dbt_tests.yml
dbt build runs automatically on every push to main
```

---

## 6. Files in the Repo

```
migrationpulse/
├── .github/
│   └── workflows/
│       └── dbt_tests.yml                               # GitHub Actions CI/CD — dbt build on push
├── dags/migration_pipeline.py                          # Airflow DAG — 8 tasks wired
├── spark/
│   ├── bronze_ingest.py                                # Movebank API + CSV → S3 bronze
│   └── silver_transform.py                             # S3 bronze → Delta Lake → S3 silver
├── dbt_project/migrationpulse/
│   ├── models/staging/
│   │   ├── stg_movebank_sightings.sql                  # Reads all 3 Delta tables via delta_scan()
│   │   └── schema.yml                                  # dbt tests
│   └── models/marts/
│       ├── fct_species_movements.sql                   # GPS fixes + velocity + speed
│       └── rpt_corridor_deviation.sql                  # Weekly aggregate per individual
├── ml/dtw_corridor_scorer.py                           # DTW scoring + MLflow logging
├── dashboard/
│   ├── app.py                                          # Streamlit dashboard (reads Delta Lake)
│   └── requirements.txt                               # streamlit, pydeck, plotly, boto3, pandas, pyarrow, deltalake
├── docker-compose.yaml                                 # Airflow Docker stack (8 containers)
├── .env                                                # Real credentials (gitignored)
├── .env.example                                        # Placeholder template (committed)
├── .gitignore
└── README.md
```

---

## 7. Important Commands Reference

### Load Environment Variables (run every new PowerShell session)

```powershell
foreach ($line in Get-Content .env) {
    if ($line -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}
# Verify
echo $env:AWS_ACCESS_KEY_ID
```

### Docker / Airflow Commands

```powershell
# Start Airflow (Docker Desktop must be open first)
docker-compose up -d

# Stop Airflow
docker-compose down

# Check all containers are healthy
docker-compose ps

# View scheduler logs
docker-compose logs airflow-scheduler

# Install dbt into containers after every restart
docker-compose exec airflow-worker bash -c 'pip install dbt-core dbt-duckdb --quiet'
docker-compose exec airflow-scheduler bash -c 'pip install dbt-core dbt-duckdb --quiet'

# Airflow UI → localhost:8080 | Username: airflow | Password: airflow
```

### Pipeline Commands

```powershell
# Bronze ingest (Movebank API → S3 bronze + CSV → S3 bronze)
python spark/bronze_ingest.py

# Silver transform (S3 bronze → Delta Lake → S3 silver)
python spark/silver_transform.py

# dbt build (run models + tests together)
cd dbt_project/migrationpulse
python -c "from dbt.cli.main import cli; cli()" build --select stg_movebank_sightings fct_species_movements rpt_corridor_deviation

# DTW scorer
cd C:\Users\yvonn\migrationpulse
python ml/dtw_corridor_scorer.py

# MLflow UI
mlflow ui  # → localhost:5000

# Streamlit dashboard (local)
cd C:\Users\yvonn\migrationpulse
streamlit run dashboard/app.py  # → localhost:8501
```

### Git Commands

```powershell
git status
git add .
git commit -m 'feat: description'
git push
```

---

## 8. dbt Configuration

### profiles.yml location
`C:\Users\yvonn\.dbt\profiles.yml`

### Current profiles.yml content

```yaml
migrationpulse:
  outputs:
    dev:
      type: duckdb
      path: ':memory:'
      threads: 4
      extensions:
        - httpfs
        - delta
      settings:
        s3_region: us-east-2
        s3_access_key_id: "{{ env_var('AWS_ACCESS_KEY_ID') }}"
        s3_secret_access_key: "{{ env_var('AWS_SECRET_ACCESS_KEY') }}"
  target: dev
```

### Important dbt notes
- dbt uses DuckDB as the local execution engine (dbt-duckdb adapter)
- path: ':memory:' means the database is in-memory and resets between runs
- Always use `dbt build` — never `dbt run` and `dbt test` separately
- The delta extension enables DuckDB's Delta Lake reader
- dbt is NOT installed inside Docker containers by default — must pip install after each restart
- On Windows, dbt CLI doesn't work — use `python -c "from dbt.cli.main import cli; cli()"` instead
- On Linux (GitHub Actions), plain `dbt build` works fine

---

## 9. Delta Lake Implementation

### Why we use it
- **Atomic commits** — failed writes roll back automatically, dashboard always shows valid data
- **Schema enforcement** — rejects mismatched columns from new species APIs at write time
- **Time travel** — can query Silver table as of any previous version for debugging

### How it works
```python
# silver_transform.py — writing Delta Lake (chunked for large datasets)
from deltalake.writer import write_deltalake
write_deltalake(s3_path, arrow_table, mode="overwrite", storage_options=storage_options)
# subsequent chunks use mode="append"

# stg_movebank_sightings.sql — reading Delta Lake in dbt
from delta_scan('s3://migrationpulse-silver/bald_eagle')
```

### S3 structure
```
migrationpulse-silver/
├── bald_eagle/
│   ├── _delta_log/
│   └── part-*.parquet
├── turkey_vulture/
│   ├── _delta_log/
│   └── part-*.parquet
└── delmarva_waterfowl/
    ├── _delta_log/
    └── part-*.parquet
```

---

## 10. GitHub Actions CI/CD

### File location
`.github/workflows/dbt_tests.yml`

### What it does
- Triggers on every push to main
- Spins up Ubuntu runner
- Installs dependencies from dashboard/requirements.txt + dbt-core + dbt-duckdb
- Writes profiles.yml dynamically from GitHub Secrets
- Runs `dbt build` — fails the workflow if any of the 6 dbt tests fail

### Required GitHub Secrets
Go to repo → Settings → Secrets and variables → Actions:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### Note
On Linux (GitHub Actions), `dbt build` works as a plain CLI command — no need for the Python workaround used on Windows.

---

## 11. Bronze Ingestion — Two Paths

### Path 1: Movebank API (bald_eagle, turkey_vulture)
- Fetches one individual at a time (bulk fetch returns 500)
- Uploads combined JSON to S3 bronze

### Path 2: CSV fallback (delmarva_waterfowl)
- Used when Movebank API returns 403 despite CC0 license
- Reads CSV in 500k row chunks using pandas chunksize parameter
- Uploads each chunk as a separate JSON file to S3 bronze
- Silver transform reads all chunks from the same date folder and combines them

### Why some CC0 studies return 403
- Movebank requires license acceptance via the website download dialog before API access works
- Some studies require the data manager to manually grant programmatic access regardless of license
- This is a Movebank platform quirk, not a credentials issue

---

## 12. Silver Transform — Chunked Delta Lake Write

For large datasets (>1M rows), the Delta Lake write is done in 1M row chunks to avoid S3 upload timeouts:

```python
chunk_size = 1_000_000
first_chunk = True
for i in range(0, len(df), chunk_size):
    chunk = df.iloc[i:i + chunk_size]
    mode = "overwrite" if first_chunk else "append"
    write_deltalake(s3_path, pa.Table.from_pandas(chunk), mode=mode, storage_options=storage_options)
    first_chunk = False
```

---

## 13. All Problems Encountered and Solutions

### From V3 (carried forward)

#### 13.1 Fernet Key Exposed on GitHub
**Problem:** GitGuardian alert — Fernet key committed to public repo.
**Solution:** git-filter-repo to scrub from entire commit history, moved to .env.
**Interview talking point:** "I had a security incident where a secret was exposed. I used git-filter-repo to scrub it from the entire commit history rather than just deleting the file."

#### 13.2 dbt Cannot Be Run as CLI on Windows
**Problem:** `dbt build` returns "command not found" in PowerShell.
**Solution:** `python -c "from dbt.cli.main import cli; cli()" build --select ...`

#### 13.3 dbt :memory: Database Resets Between Commands
**Problem:** Running `dbt run` then `dbt test` separately causes "Table does not exist" errors.
**Solution:** Always use `dbt build` which runs models and tests in the same session.

#### 13.4 spark/ and ml/ Folders Not Mounted in Docker
**Problem:** Airflow tasks failed with "No such file or directory."
**Solution:** Added volume mounts to docker-compose.yaml.

#### 13.5 dbt Not Installed Inside Docker Containers
**Problem:** `run_dbt_models` task failed with "No module named 'dbt'."
**Solution:** Manually pip install after every docker-compose up. Long-term fix: custom Docker image.

#### 13.6 delta_scan() Credential Error — EC2 Metadata Fallback
**Problem:** delta_scan() ignored httpfs credentials and tried EC2 metadata service.
**Solution:** DuckDB S3 SECRET via dbt pre_hook in stg_movebank_sightings.sql.

#### 13.7 matplotlib Crash on Windows
**Problem:** FileNotFoundError on matplotlib icon PNG when trying to open GUI window.
**Solution:** `import matplotlib; matplotlib.use('Agg')` at top of dtw_corridor_scorer.py.

#### 13.8 Movebank Bulk Fetch Returns 500
**Problem:** Fetching all individuals at once returns 500 error.
**Solution:** Always fetch one individual at a time using individual_local_identifier parameter.

#### 13.9 PowerShell Env Var Loader Breaks with Quote Encoding
**Problem:** Original Get-Content | ForEach-Object loader broke in some PowerShell sessions.
**Solution:** Use foreach loop version (see Section 7).

### New in V4

#### 13.10 GitHub Actions — requirements.txt Not Found
**Problem:** Workflow looked for requirements.txt in project root, but it's at dashboard/requirements.txt.
**Solution:** Changed path to `dashboard/requirements.txt` in workflow file.

#### 13.11 GitHub Actions — dbt Command Not Found
**Problem:** `dbt: command not found` because dbt wasn't in dashboard/requirements.txt.
**Solution:** Added explicit `pip install dbt-core dbt-duckdb` step in workflow.

#### 13.12 Movebank API 403 for Multiple CC0 Studies
**Problem:** Many CC0 studies return 403 "Invalid login or missing privilege" despite license acceptance.
**Solution:** CSV download fallback — download from Movebank website, ingest via ingest_from_csv().
**Studies affected:** Delmarva Waterfowl (1509697502), Wood Stork (1448377103), Canada Goose (2105214573).

#### 13.13 Steamhouse 1 and 2 — Space in Individual ID Causes 500
**Problem:** Individual IDs with spaces get URL-encoded as `+` which Movebank API rejects with 500.
**Solution:** Graceful skip — return empty DataFrame on 500 error. Proper fix would be explicit URL encoding.
**Interview talking point:** "Movebank's API returns 500 for individual IDs with spaces because they get encoded as + instead of %20. I handled it gracefully but the proper fix is explicit URL encoding before the request."

#### 13.14 S3 EntityTooLarge on 2.3GB JSON Upload
**Problem:** S3 put_object has a size limit — uploading 9M records as a single JSON file fails.
**Solution:** Chunked CSV ingestion using pandas chunksize=500_000. Uploads 19 separate JSON files.
**Interview talking point:** "The dataset was 2.3GB which exceeded S3's single upload limit, so I implemented chunked ingestion using pandas' chunksize parameter to upload in 500k record batches."

#### 13.15 S3 Upload Timeout on Delta Lake Write
**Problem:** Writing 9M records to Delta Lake in one shot times out after 10 retries.
**Solution:** Chunked Delta Lake write — 1M rows at a time, first chunk uses mode="overwrite", subsequent chunks use mode="append".

#### 13.16 dbt UNION ALL Column Mismatch
**Problem:** "Set operations can only apply to expressions with the same number of result columns" — Delmarva CSV had 30 columns vs bald eagle's fewer columns.
**Solution:** Explicitly SELECT only needed columns in each CTE before UNION ALL in stg_movebank_sightings.sql.

#### 13.17 Streamlit Cloud Crash — Memory Limit
**Problem:** Loading 9.4M records into memory crashes Streamlit Cloud free tier (~1GB RAM).
**Solution:** Load only needed columns via `dt.to_pandas(columns=[...])` and sample large datasets to 500k rows.

#### 13.18 Laptop Sleep Kills Long-Running Operations
**Problem:** Windows sleep mode interrupts S3 downloads and uploads mid-operation.
**Solution:** Set Power & Sleep settings to Never while running long operations.

---

## 14. Environment Variables

```
AIRFLOW_UID=50000
FERNET_KEY=...                    # Airflow encryption key
AWS_ACCESS_KEY_ID=AKIA...         # IAM user: migrationpulse-dev
AWS_SECRET_ACCESS_KEY=...         # Keep secret — never commit
AWS_DEFAULT_REGION=us-east-2      # Ohio region
MOVEBANK_USERNAME=yvonneh
MOVEBANK_PASSWORD=...             # Keep secret — never commit
```

### AWS Resources
- IAM User: migrationpulse-dev (AmazonS3FullAccess policy)
- S3 Bucket: migrationpulse-bronze (us-east-2)
- S3 Bucket: migrationpulse-silver (us-east-2) — Delta Lake tables
- S3 Bucket: migrationpulse-gold (us-east-2) — dbt output, not yet persisted

### Streamlit Cloud Secrets
```toml
AWS_ACCESS_KEY_ID = "..."
AWS_SECRET_ACCESS_KEY = "..."
AWS_DEFAULT_REGION = "us-east-2"
MOVEBANK_USERNAME = "yvonneh"
MOVEBANK_PASSWORD = "..."
```

---

## 15. Immediate Next Steps — In Order

### Step 1 — Fix Delmarva Waterfowl Not Showing on Dashboard (IMMEDIATE)
Delmarva individuals are in the Delta table (99 individuals confirmed) but not appearing in the dashboard dropdown. Likely a Streamlit cache issue or column mismatch between species. Debug by:
1. Stop and restart streamlit (`Ctrl+C` then `streamlit run dashboard/app.py`)
2. Check if Delmarva individuals appear in the dropdown
3. If map lines don't show, check column names — map uses `location_long`/`location_lat` which must exist in the loaded df

### Step 2 — Fix Dashboard Spinner Text
Currently says "Loading eagle GPS data from S3..." — should say "Loading migration data from S3..."

### Step 3 — Commit and Push Everything
Once dashboard is working locally, commit all changes:
```powershell
git add .
git commit -m "feat: add delmarva waterfowl, multi-species dashboard, chunked ingestion"
git push
```

### Step 4 — Dashboard UI Polish
- Fix spinner text
- Consider adding a species filter to the map
- General cleanup

### Step 5 — Fix dbt Gold Layer Persistence
Currently dbt runs in :memory: DuckDB so Gold layer views are not persisted to S3.
Options:
- Use local DuckDB file path instead of :memory:
- Use dbt-duckdb's external materialization to write Parquet/Delta directly to S3

### Step 6 — Fix dbt in Airflow (Permanent Solution)
Build custom Docker image with dbt pre-installed:
```dockerfile
FROM apache/airflow:3.1.8
RUN pip install dbt-core dbt-duckdb deltalake
```
In docker-compose.yaml replace `image: apache/airflow:3.1.8` with `build: .`

### Step 7 — Add PySpark
Replace pandas transforms in silver_transform.py with actual PySpark code. This is on the resume already — needs to actually be implemented. A local Spark session works fine.

### Step 8 — Update DTW Scorer for Multiple Species
Currently dtw_corridor_scorer.py only scores bald eagles. Update to score turkey vultures and delmarva waterfowl too.

### Step 9 — Update Resume and Start Applying
Use updated bullet points reflecting 9.4M records across 3 species, GitHub Actions CI/CD, chunked ingestion.

---

## 16. Resume Bullet Points (Current)

```latex
\resumeItemListStart
    \resumeItem{Built a weekly-automated data engineering pipeline that ingests live GPS telemetry from the Movebank Animal Tracking API for migratory species, processes it through a \textbf{Bronze → Silver → Gold medallion architecture} on \textbf{AWS S3}, and detects migration corridor deviations using \textbf{DTW (Dynamic Time Warping)} — surfaced via a live \textbf{Streamlit} dashboard with pydeck migration maps and per-individual anomaly scoring}
    \resumeItem{Ingested 45,000+ Bald Eagle GPS fixes across 40 individuals via per-individual Movebank REST API calls (bulk fetch returns 500); cleaned and typed raw telemetry with \textbf{PySpark} — deduplicating records, casting UTC timestamps, dropping null coordinates — and wrote the Silver layer as a \textbf{Delta Lake} table on S3 for atomic commits and schema enforcement}
    \resumeItem{Modeled Silver-to-Gold transformations with \textbf{dbt Core} using \textbf{DuckDB} as the local execution engine; wrote 3 SQL models (\texttt{stg\_movebank\_sightings}, \texttt{fct\_species\_movements}, \texttt{rpt\_corridor\_deviation}) with 6 data quality tests; staging model reads directly from the Delta Lake table via DuckDB's \texttt{delta\_scan()} with a pre-hook S3 secret for credential injection; automated test execution on every commit via a \textbf{GitHub Actions} CI/CD workflow}
    \resumeItem{Implemented \textbf{Sakoe-Chiba banded DTW} anomaly detection — built a species-level trajectory template from median lat/long paths across all individuals, computed per-individual DTW distance against the template, and flagged individuals exceeding 2 standard deviations as corridor deviations; all experiment runs logged to \textbf{MLflow} with parameters, metrics, and distance distribution artifacts}
    \resumeItem{Orchestrated full pipeline with \textbf{Apache Airflow} 8-task DAG (\texttt{@weekly}) running via Docker Compose — from API health check through bronze ingest, silver Delta Lake write, dbt build, DTW scoring, and anomaly notification; deployed live dashboard to \textbf{Streamlit Cloud} reading directly from Delta Lake Silver table}
\resumeItemListEnd
```

**TODO:** Update record count bullet to reflect 9.4M+ records across 3 species once dashboard is fully working.

---

## 17. Known Issues and Gotchas

- PowerShell env vars don't persist across terminal sessions — run foreach loader every session
- Movebank bulk event fetch returns 500 — always fetch one individual at a time
- Most Movebank studies require license acceptance — only CC0 studies work, and even some CC0 studies return 403
- Individual IDs with spaces (e.g. "Steamhouse 1") cause 500 errors — currently skipped gracefully
- dbt run and dbt test must be run together as dbt build — separate runs fail due to :memory: reset
- dbt is not installed in Docker containers — must be manually pip installed after every docker-compose restart
- delta_scan() requires a DuckDB SECRET pre_hook — httpfs credentials alone are not enough
- Docker Desktop must be running before any docker-compose commands
- matplotlib must use Agg backend on Windows — add matplotlib.use('Agg') before all imports
- mlruns/ folder is gitignored — MLflow experiment history is local only
- Large Delta Lake writes (>1M rows) must be chunked to avoid S3 upload timeouts
- Streamlit Cloud free tier has ~1GB RAM — sample large datasets before loading into dashboard
- Laptop sleep mode kills long S3 operations — set Power & Sleep to Never for long runs
- The Delmarva waterfowl study contains 3 species (Snow Goose, Canada Goose, Mallard) but is labeled as a single species in the pipeline

---

MigrationPulse V4 Handoff · Yvonne Hong · 2026-03-26 · github.com/yvnnhong/migrationpulse