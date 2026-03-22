# MigrationPulse 🦅
### Animal Migration Analytics Pipeline

`Airflow` · `PySpark` · `dbt` · `Delta Lake` · `AWS S3` · `MLflow` · `Streamlit`

---

A weekly-automated data engineering pipeline that ingests live GPS telemetry from the Movebank Animal Tracking API, transforms and models the data with PySpark and dbt, stores it in a Delta Lake medallion architecture on AWS S3, tracks ML experiments with MLflow, and surfaces findings through a live Streamlit dashboard.

**Live Demo:** [streamlit link] · **Status:** In Development

---

## What It Does

- Fetches new Movebank GPS records weekly via Airflow DAG — currently tracking Bald Eagle (*Haliaeetus leucocephalus*) in the Pacific Northwest (study active as of 2026)
- Stores raw JSON in AWS S3 bronze bucket and processes it through Bronze → Silver → Gold Delta Lake layers
- Cleans and types raw telemetry with PySpark — deduplicates, casts timestamps, drops null coordinates, writes Silver layer as Parquet
- Models Silver-to-Gold transformations with dbt — staging, fact, and reporting mart layers with built-in data quality tests
- Detects migration corridor deviations per species using DTW (Dynamic Time Warping); all experiment runs logged with MLflow
- Visualizes migration paths, corridor deviations, and anomalies on a live Streamlit dashboard with pydeck maps

---

## Current Build Status

| Layer | Status | Details |
|---|---|---|
| Airflow DAG skeleton | ✅ Live | All 8 tasks visible in Airflow UI at localhost:8080 |
| Bronze ingest | ✅ Working | 45,327 bald eagle GPS records landing in S3 |
| Silver transform | ✅ Working | 45,283 cleaned records written as Parquet to S3 |
| dbt models | 🔨 In progress | — |
| DTW + MLflow | 🔨 In progress | — |
| Streamlit dashboard | 🔨 In progress | — |

---

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | Apache Airflow 2.x |
| Compute | PySpark + pandas |
| Storage | AWS S3 (Bronze/Silver/Gold buckets) |
| Table Format | Delta Lake (Gold layer) |
| Data Modeling | dbt Core |
| ML Tracking | MLflow |
| Cloud | AWS |
| Dashboard | Streamlit + pydeck + Plotly |
| Language | Python 3.11 |
| Data Source | Movebank REST API (free, CC0 licensed studies) |
| Dev | Docker Compose, Git |

---

## Project Structure

```
migrationpulse/
├── dags/
│   └── migration_pipeline.py      # Main Airflow DAG (8 tasks, @weekly)
├── spark/
│   ├── bronze_ingest.py           # Movebank API → raw JSON → S3 bronze
│   ├── silver_transform.py        # S3 bronze → cleaned Parquet → S3 silver
│   └── bald_eagle_raw.csv         # Local reference copy of raw data
├── dbt_project/
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_movebank_sightings.sql
│   │   │   └── stg_movebank_studies.sql
│   │   └── marts/
│   │       ├── fct_species_movements.sql
│   │       ├── fct_anomalies.sql
│   │       ├── dim_species.sql
│   │       └── rpt_corridor_deviation.sql
│   └── tests/
│       └── assert_no_duplicate_fixes.sql
├── ml/
│   └── dtw_corridor_scorer.py     # DTW scoring + MLflow logging
├── dashboard/
│   └── app.py                     # Streamlit dashboard
├── docker-compose.yaml            # Local Airflow stack
├── .env.example                   # Environment variable template
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker Desktop (for local Airflow)
- AWS account with S3 access (free tier works)
- Movebank account (free at movebank.org)
- Java (required for PySpark)
- `pip install requests boto3 pandas pyarrow pyspark dbt-core mlflow dtaidistance`

### 1. Clone and configure

```bash
git clone https://github.com/yvnnhong/migrationpulse
cd migrationpulse
cp .env.example .env
# Fill in: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION,
#          MOVEBANK_USERNAME, MOVEBANK_PASSWORD
```

### 2. Load environment variables (PowerShell)

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}
```

### 3. Start Airflow locally

```bash
docker-compose up airflow-init
docker-compose up -d
# Airflow UI → localhost:8080
# Username: airflow  Password: airflow
# Enable the 'migration_pipeline' DAG and trigger a run
```

### 4. Run the pipeline manually

```bash
# Bronze ingest — fetch from Movebank API → S3
python spark/bronze_ingest.py

# Silver transform — clean + type → Parquet on S3
python spark/silver_transform.py
```

### 5. Run dbt models

```bash
cd dbt_project
dbt deps
dbt build          # runs models + tests
dbt docs generate  # optional: browse lineage graph
```

### 6. Launch the dashboard

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

---

## Airflow DAG

The main DAG (`migration_pipeline`) runs on a `@weekly` schedule. Tasks execute in the following order:

| Task | Operator | Description |
|---|---|---|
| `check_api_health` | HttpSensor | Confirms Movebank API is reachable before fetching |
| `fetch_movebank_data` | PythonOperator | Pulls new GPS records for all tracked species |
| `upload_to_blob` | PythonOperator | Writes raw JSON to S3 bronze bucket |
| `run_pyspark_transform` | BashOperator | Applies Silver-layer cleaning and typing |
| `run_dbt_models` | BashOperator | Runs `dbt build` (staging → marts) |
| `run_dbt_tests` | BashOperator | Runs `dbt test`; fails DAG loudly on data quality issues |
| `score_anomalies` | PythonOperator | DTW corridor deviation scoring; results logged to MLflow |
| `notify_on_anomalies` | BashOperator | Alert digest if anomaly rate exceeds 5% threshold |

---

## Data Source

**Bald Eagle (Haliaeetus leucocephalus) in the Pacific Northwest**
- Study ID: `430263960`
- PI: Myles Lamont / Bald Eagle Tracking Alliance
- License: CC0 (public domain)
- Coverage: 2018 – present (actively updated)
- Records: 120,522+ GPS fixes across 40 individuals
- Tags: GPS, acceleration

All animal tracking data sourced from [Movebank](https://movebank.org), a free repository hosted by the Max Planck Institute of Animal Behavior. Individual study citations are logged in `dbt_project/sources.yml`.

---

## S3 Bucket Structure

```
migrationpulse-bronze/
└── bald_eagle/2026/03/22/raw_213007.json     # raw API response

migrationpulse-silver/
└── bald_eagle/2026/03/22/silver_222624.parquet  # cleaned, typed, deduped

migrationpulse-gold/
└── (dbt mart outputs — coming soon)
```

---

## dbt Models

| Model | Description |
|---|---|
| `stg_movebank_sightings` | Casts types, renames columns to snake_case, drops rows with null coordinates |
| `stg_movebank_studies` | Normalizes study metadata; maps study_id to species common name |
| `fct_species_movements` | One row per GPS fix; adds computed velocity, heading_delta, distance_from_centroid_km |
| `fct_anomalies` | Joins DTW distance scores from MLflow output back to movement records; flags corridor deviations |
| `dim_species` | Species dimension: common name, scientific name, IUCN status, typical range |
| `rpt_corridor_deviation` | Weekly aggregate: mean DTW deviation from historical corridor per species |

### dbt Tests

- `not_null` on `individual_id`, `timestamp`, `lat`, `long` in every staging model
- `unique` on `movement_id` in `fct_species_movements`
- `accepted_values` on `species_code` — only whitelisted study species allowed through
- Custom test: no GPS fix should appear more than 2x in a 1-hour window (dedup check)

---

## DTW Corridor Deviation

Each weekly run computes a DTW (Dynamic Time Warping) distance score per individual animal, comparing that week's GPS trajectory against a 5-year species template.

**How it works:**
1. Build a historical template: the median lat/long path across all individuals for the same calendar week over the past 5 years
2. For each individual this week, extract their ordered sequence of GPS fixes
3. Compute Sakoe-Chiba banded DTW distance between the individual's path and the species template — DTW handles sequences of different lengths and allows non-linear time alignment
4. Flag individuals whose DTW distance exceeds 2 standard deviations above the species' historical DTW distribution as anomalous corridor deviations

**Why DTW over point-based anomaly detection:** DTW treats the full trajectory as the unit of analysis. It catches a Bald Eagle flying the wrong route even if every individual GPS fix has normal speed and heading — something a point-scoring method like Isolation Forest cannot do.

---

## MLflow Experiment Tracking

Every pipeline run creates a new MLflow experiment run under the project `migration_pulse`.

```bash
mlflow ui  # → localhost:5000
```

**Logged per run:**

| Type | Details |
|---|---|
| Parameters | `dtw_window` (Sakoe-Chiba band), `anomaly_threshold_stdev`, `min_fixes_required`, `species_code` |
| Metrics | `mean_dtw_distance`, `stdev_dtw_distance`, `anomaly_count`, `anomaly_rate_pct`, `n_individuals_scored` |
| Artifacts | DTW distance distribution plot, anomaly trajectory overlays on corridor map, template path GeoJSON |
| Tags | `species_code`, `pipeline_run_date`, `calendar_week`, `git_commit_sha` |

---

## Key Findings *(updated weekly)*

> Most recent run: 2026-03-22

- 45,283 GPS fixes ingested for Bald Eagle this week
- Corridor anomaly scoring: in development
- Notable finding: study actively updating — last fix recorded 2026-03-22

---

## Creator

Yvonne Hong ❤️

## License

MIT License. See `LICENSE` for details.

Animal tracking data: © respective study authors via Movebank. See `data/citations.md`.