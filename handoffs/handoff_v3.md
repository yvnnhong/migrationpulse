CLAUDE HANDOFF DOCUMENT
MigrationPulse — V3
Animal Migration Analytics Pipeline
Airflow · PySpark · dbt · Delta Lake · AWS S3 · MLflow · Streamlit
Developer: Yvonne Hong | Repo: github.com/yvnnhong/migrationpulse | Date: 2026-03-24

---

## 1. What We Are Building

MigrationPulse is a production-grade, weekly-automated data engineering portfolio project. It ingests live GPS telemetry from the Movebank Animal Tracking API, processes it through a Bronze → Silver → Gold medallion architecture on AWS S3, writes the Silver layer as a Delta Lake table, models the data with dbt (reading from Delta Lake via DuckDB's delta_scan()), scores migration corridor deviations using DTW (Dynamic Time Warping) tracked in MLflow, and surfaces findings on a live Streamlit dashboard.

The project is targeted at data engineering roles in Los Angeles and adds the following tools to Yvonne's resume: Airflow, PySpark, dbt, Delta Lake, MLflow, and DTW anomaly detection.

Live dashboard: https://migrationpulse.streamlit.app

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
| Cloud | AWS (S3, IAM) — boto3 SDK |
| Data Source | Movebank REST API — Bald Eagle study ID 430263960, CC0 license |
| Language | Python 3.11 (Miniconda base env) |
| Dev Tooling | Docker Compose (Airflow), Git, GitHub, PowerShell, VSCode |
| OS | Windows 11 (PowerShell terminal in VSCode) |

---

## 3. Current Build Status — Everything Working

| Component | Status | Details |
|---|---|---|
| Airflow DAG | DONE | All 8 tasks wired with real function calls, green end-to-end |
| Bronze ingest | DONE | 45,327 bald eagle GPS records in S3 bronze bucket |
| Silver transform | DONE | 45,295 cleaned records as Delta Lake table in S3 silver bucket |
| Delta Lake | DONE | Silver layer writes via write_deltalake(), _delta_log/ present in S3 |
| dbt models | DONE | 3 models, 6 tests, all passing; reads from Delta table via delta_scan() |
| DTW + MLflow | DONE | Scores 5 individuals, anomaly rate logged, distribution plot artifact |
| Streamlit dashboard | DONE | Live at migrationpulse.streamlit.app, reads from Delta Lake |

---

## 4. Architecture — Data Flow

```
Movebank REST API (per-individual GPS fetch)
    ↓ spark/bronze_ingest.py (requests + boto3)
S3: migrationpulse-bronze/{species}/{YYYY/MM/DD}/raw_{HHMMSS}.json
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
```

---

## 5. Files in the Repo

```
migrationpulse/
├── dags/migration_pipeline.py                          # Airflow DAG — 8 tasks wired
├── spark/
│   ├── bronze_ingest.py                                # Movebank API → S3 bronze
│   └── silver_transform.py                             # S3 bronze → Delta Lake → S3 silver
├── dbt_project/migrationpulse/
│   ├── models/staging/
│   │   ├── stg_movebank_sightings.sql                  # Reads Delta table via delta_scan()
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

## 6. Important Commands Reference

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

NOTE: The original handoff used a Get-Content | ForEach-Object pattern with single quotes around the regex — this breaks in some PowerShell contexts due to quote encoding. Always use the foreach loop version above.

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

# Check DAG file syntax
docker-compose exec airflow-scheduler bash -c 'python /opt/airflow/dags/migration_pipeline.py'

# Check what files Airflow can see
docker-compose exec airflow-scheduler bash -c 'ls /opt/airflow'
docker-compose exec airflow-scheduler bash -c 'ls /opt/airflow/spark'

# Install packages directly into running containers (survives until restart)
docker-compose exec airflow-worker bash -c 'pip install dbt-core dbt-duckdb --quiet'
docker-compose exec airflow-scheduler bash -c 'pip install dbt-core dbt-duckdb --quiet'

# Airflow UI
# → localhost:8080 | Username: airflow | Password: airflow
```

### Pipeline Commands

```powershell
# Bronze ingest (Movebank API → S3 bronze)
python spark/bronze_ingest.py

# Silver transform (S3 bronze → Delta Lake → S3 silver)
python spark/silver_transform.py

# dbt build (run models + tests together — must be run together due to :memory: DuckDB)
cd dbt_project/migrationpulse
python -c "from dbt.cli.main import cli; cli()" build --select stg_movebank_sightings fct_species_movements rpt_corridor_deviation

# dbt debug (check connection)
python -c "from dbt.cli.main import cli; cli()" debug

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

## 7. dbt Configuration

### profiles.yml location
`C:\Users\yvonn\.dbt\profiles.yml`

### Current profiles.yml content

```yaml
bird_project:
  outputs:
    dev:
      dbname: postgres
      host: localhost
      password: tere1229
      port: 5432
      schema: analytics
      threads: 1
      type: postgres
      user: postgres
  target: dev

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
- Because of this, dbt run and dbt test must be run together with dbt build — running them separately causes "table does not exist" errors
- The delta extension in profiles.yml enables DuckDB's Delta Lake reader
- dbt is NOT installed inside Docker containers by default — must be pip installed into airflow-worker and airflow-scheduler manually after each docker-compose down/up

---

## 8. Delta Lake Implementation

### Why we added it
The Streamlit dashboard at migrationpulse.streamlit.app shows summary metric cards at the top (Total GPS Fixes, Individuals Tracked, Date Range, Species). If a weekly Airflow run crashes mid-write to the Silver layer, the dashboard would show corrupted values like "Total GPS Fixes: 3" or "Individuals Tracked: 0" to any recruiter who clicks the live link. Delta Lake's atomic commits mean a failed write rolls back automatically — the dashboard always reads the last successfully committed version.

Additional reasons:
- Schema enforcement: rejects mismatched columns from new species APIs at write time
- Time travel: can query Silver table as of any previous version for debugging
- Natural fit for medallion architecture

### How it works in this project
The Silver layer writes a Delta Lake table to S3 instead of individual Parquet files. Delta Lake is still Parquet under the hood — it adds a _delta_log/ folder containing JSON transaction logs alongside the data files. DuckDB reads this format natively via the delta extension and delta_scan() function.

```python
# silver_transform.py — writing Delta Lake
from deltalake.writer import write_deltalake
write_deltalake(s3_path, arrow_table, mode="overwrite", storage_options=storage_options)

# stg_movebank_sightings.sql — reading Delta Lake in dbt
from delta_scan('s3://migrationpulse-silver/bald_eagle')
```

### Credential handling for delta_scan()
delta_scan() does not accept AWS credentials as function parameters and does not use dbt's httpfs credential settings. It requires a DuckDB SECRET to be created first. This is handled via a dbt pre_hook in stg_movebank_sightings.sql:

```sql
{% set aws_key = env_var('AWS_ACCESS_KEY_ID') %}
{% set aws_secret = env_var('AWS_SECRET_ACCESS_KEY') %}

{{ config(pre_hook="
    CREATE OR REPLACE SECRET delta_s3_secret (
        TYPE S3,
        KEY_ID '" ~ aws_key ~ "',
        SECRET '" ~ aws_secret ~ "',
        REGION 'us-east-2'
    )
") }}
```

### S3 structure after Delta Lake
```
migrationpulse-silver/
└── bald_eagle/
    ├── _delta_log/
    │   └── 00000000000000000000.json   # transaction log
    └── part-00000-*.parquet            # data files managed by Delta
```

---

## 9. Problems We Encountered and How We Solved Them

### 9.1 Fernet Key Exposed on GitHub
Problem: GitGuardian sent an email alerting that a Fernet key (Airflow's internal encryption key) was committed to the public repo. It was in a config/ file that Airflow auto-generated and that got accidentally tracked.

Solution:
1. Generated a new Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. Moved key to .env (gitignored), referenced in docker-compose.yaml as ${FERNET_KEY}
3. Installed git-filter-repo: `pip install git-filter-repo`
4. Created replacements.txt with the old key value
5. Ran: `git filter-repo --replace-text replacements.txt --force`
6. Re-added remote and force pushed: `git remote add origin https://github.com/yvnnhong/migrationpulse.git` then `git push --set-upstream origin main --force`

Interview talking point: "I had a security incident where a secret was exposed to GitHub. I used git-filter-repo to scrub it from the entire commit history rather than just deleting the file, since the secret would still be visible in git log."

### 9.2 dbt Cannot Be Run as a CLI Command on Windows
Problem: `dbt init` and `dbt build` returned "command not found" in PowerShell even after pip install.

Solution: Call dbt through Python directly:
```powershell
python -c "from dbt.cli.main import cli; cli()" build --select ...
```

### 9.3 dbt :memory: Database Resets Between Commands
Problem: Running `dbt run` then `dbt test` separately caused "Table does not exist" errors because DuckDB's in-memory database resets between Python invocations, destroying the views created by dbt run.

Solution: Always use `dbt build` which runs models and tests in the same session. Never run `dbt run` and `dbt test` as separate commands.

### 9.4 spark/ and ml/ Folders Not Mounted in Docker
Problem: Airflow DAG tasks calling `python /opt/airflow/spark/bronze_ingest.py` failed with "No such file or directory" because only the dags/ folder was mounted into the containers by default.

Solution: Added volume mounts to docker-compose.yaml under the x-airflow-common volumes section:
```yaml
- ./spark:/opt/airflow/spark
- ./ml:/opt/airflow/ml
- ./dbt_project:/opt/airflow/dbt_project
- ~/.dbt:/home/airflow/.dbt
```

### 9.5 dbt Not Installed Inside Docker Containers
Problem: run_dbt_models task failed with "No module named 'dbt'" because dbt is installed in the local Python environment but not inside the Airflow Docker containers.

Solution: After each docker-compose up, manually install dbt into the running containers:
```powershell
docker-compose exec airflow-worker bash -c 'pip install dbt-core dbt-duckdb --quiet'
docker-compose exec airflow-scheduler bash -c 'pip install dbt-core dbt-duckdb --quiet'
```
Note: This install is lost on docker-compose down. Long-term fix is to build a custom Docker image with dbt pre-installed (not yet implemented).

### 9.6 delta_scan() Credential Error — EC2 Metadata Fallback
Problem: delta_scan() ignored DuckDB's httpfs S3 credentials and tried to fetch credentials from the EC2 instance metadata service (169.254.169.254), which only exists on actual AWS EC2 machines.

Solution: Created a DuckDB S3 SECRET via a dbt pre_hook in stg_movebank_sightings.sql before the delta_scan() call. This is the only credential method delta_scan() respects — passing credentials as function parameters is not supported.

### 9.7 matplotlib Crash on Windows (No Display)
Problem: dtw_corridor_scorer.py crashed with a FileNotFoundError on a matplotlib icon PNG when trying to open a GUI window on Windows.

Solution: Added `import matplotlib; matplotlib.use('Agg')` at the very top of the file before any other imports. The Agg backend renders to file without needing a display.

### 9.8 Movebank Bulk Fetch Returns 500
Problem: Fetching all individuals at once from the Movebank API returns a 500 error.

Solution: Always fetch one individual at a time using the individual_local_identifier parameter. See bronze_ingest.py for the per-individual loop.

### 9.9 PowerShell Env Var Loader Breaks with Certain Quote Encodings
Problem: The original Get-Content | ForEach-Object loader from the V2 handoff broke in some PowerShell sessions due to quote encoding issues when copied from documents.

Solution: Use the foreach loop version which is more robust:
```powershell
foreach ($line in Get-Content .env) {
    if ($line -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}
```

---

## 10. Environment Variables

These are in .env (gitignored) and must be loaded into each PowerShell session.

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
- S3 Bucket: migrationpulse-bronze (us-east-2, block all public access)
- S3 Bucket: migrationpulse-silver (us-east-2, block all public access) — Delta Lake table
- S3 Bucket: migrationpulse-gold (us-east-2, block all public access — dbt output, not yet persisted)

### Streamlit Cloud Secrets
The live dashboard at migrationpulse.streamlit.app requires these secrets set in Streamlit Cloud settings:
```toml
AWS_ACCESS_KEY_ID = "..."
AWS_SECRET_ACCESS_KEY = "..."
AWS_DEFAULT_REGION = "us-east-2"
MOVEBANK_USERNAME = "yvonneh"
MOVEBANK_PASSWORD = "..."
```

---

## 11. Immediate Next Steps — In Order

### Step 1 — Add More Species (highest priority)
More species = more data = more impressive dashboard and more meaningful DTW anomaly detection.

Process for adding a new species:
1. Go to movebank.org → map → search for species
2. Find a study, click Download — this accepts the license and reveals the study ID
3. ONLY use CC0 licensed studies — any other license causes API 403 errors
4. Already identified candidates:
   - Ferruginous Hawk — study ID 110270319
   - Northern Elephant Seal — study ID 7006760
5. Add the new species to SPECIES_STUDIES dict in spark/bronze_ingest.py
6. Test API access: `python -c "import requests, os; resp = requests.get('https://www.movebank.org/movebank/service/direct-read?entity_type=event&study_id=STUDY_ID&individual_local_identifier=INDIVIDUAL_ID', auth=(os.environ.get('MOVEBANK_USERNAME'), os.environ.get('MOVEBANK_PASSWORD'))); print(resp.status_code, resp.text[:300])"`
7. Run bronze_ingest.py and silver_transform.py for the new species
8. Update stg_movebank_sightings.sql to union multiple Delta tables or parameterize the scan
9. Update accepted_values test in schema.yml to include the new species name
10. Update Streamlit dashboard subtitle to reflect multiple species

### Step 2 — Dashboard UI Polish
Current issues noted:
- Minor styling inconsistencies (Yvonne to list specific issues)
- Subtitle visibility
- General cleanup after more species are added and the map shows richer data

### Step 3 — Fix dbt Gold Layer Persistence
Currently dbt runs in :memory: DuckDB so the Gold layer views are not actually persisted to S3. For a complete medallion architecture, the Gold layer should be written to migrationpulse-gold S3 bucket.
Options:
- Use a local DuckDB file path instead of :memory: and export to S3
- Use dbt-duckdb's external materialization to write Parquet/Delta directly to S3

### Step 4 — Fix dbt in Airflow (Permanent Solution)
Currently dbt must be manually pip installed into Docker containers after every restart. The proper fix is to build a custom Airflow Docker image with dbt pre-installed.
Create a Dockerfile in the project root:
```dockerfile
FROM apache/airflow:3.1.8
RUN pip install dbt-core dbt-duckdb deltalake
```
Then in docker-compose.yaml, replace `image: apache/airflow:3.1.8` with `build: .` and run `docker-compose build`.

### Step 5 — Add PySpark (Resume Gap)
The pipeline currently uses pandas for Bronze-to-Silver transforms. The project is called a PySpark pipeline on the resume. Replace the pandas transforms in silver_transform.py with actual PySpark code. A local Spark session works fine for this — no cluster needed.

### Step 6 — Update Resume and Start Applying
Only after Steps 1-2 are complete. Use the bullet block from the V2 handoff doc as the starting point, updated to include Delta Lake.

---

## 12. Known Issues and Gotchas

- PowerShell env vars don't persist across terminal sessions — run the foreach loader at the start of every session
- Movebank bulk event fetch returns 500 — always fetch one individual at a time
- Most Movebank studies require license acceptance — only CC0 studies work without it
- dbt run and dbt test must be run together as dbt build — separate runs fail due to :memory: reset
- dbt is not installed in Docker containers — must be manually pip installed after every docker-compose restart
- delta_scan() requires a DuckDB SECRET pre_hook — httpfs credentials alone are not enough
- Docker Desktop must be running before any docker-compose commands
- matplotlib must use Agg backend on Windows — add matplotlib.use('Agg') before all imports
- mlruns/ folder is gitignored — MLflow experiment history is local only
- logs/ and config/ folders are auto-generated by Airflow — gitignored, never commit them

---

MigrationPulse V3 Handoff · Yvonne Hong · 2026-03-24 · github.com/yvnnhong/migrationpulse