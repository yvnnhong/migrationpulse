# MigrationPulse
### Animal Migration Analytics Pipeline

`Airflow` · `PySpark` · `dbt` · `AWS S3` · `MLflow` · `Streamlit`

---

A weekly-automated data engineering pipeline that ingests live GPS telemetry from the Movebank Animal Tracking API, transforms and models the data through a Bronze → Silver → Gold medallion architecture on AWS S3, tracks ML experiments with MLflow, and surfaces findings through a live Streamlit dashboard.

**Live Demo:** [migrationpulse.streamlit.app](https://migrationpulse.streamlit.app) · **Status:** Active

---

## What It Does

- Fetches Movebank GPS records weekly via Airflow DAG — currently tracking Bald Eagle (*Haliaeetus leucocephalus*) in the Pacific Northwest (study active as of 2026)
- Stores raw JSON in AWS S3 bronze bucket and processes it through Bronze → Silver → Gold layers
- Cleans and types raw telemetry with PySpark — deduplicates, casts timestamps, drops null coordinates, writes Silver layer as Parquet
- Models Silver-to-Gold transformations with dbt — staging, fact, and reporting mart layers with built-in data quality tests
- Detects migration corridor deviations per species using DTW (Dynamic Time Warping); all experiment runs logged with MLflow
- Visualizes migration paths, corridor deviations, and anomalies on a live Streamlit dashboard with pydeck maps

---

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | Apache Airflow 2.x |
| Compute | PySpark + pandas |
| Storage | AWS S3 (Bronze/Silver/Gold buckets) |
| Data Modeling | dbt Core |
| ML Tracking | MLflow |
| Cloud | AWS |
| Dashboard | Streamlit + pydeck + Plotly |
| Language | Python 3.11 |
| Data Source | Movebank REST API (CC0 licensed studies) |
| Dev | Docker Compose, Git |

---

## Current Build Status

| Layer | Status | Details |
|---|---|---|
| Airflow DAG | Live | All 8 tasks running end-to-end |
| Bronze ingest | Working | 45,327 bald eagle GPS records in S3 |
| Silver transform | Working | 45,283 cleaned records as Parquet in S3 |
| dbt models | Working | 3 models, 6 tests, all passing |
| DTW + MLflow | Working | Scoring 5 individuals, experiment tracked |
| Streamlit dashboard | Live | migrationpulse.streamlit.app |

---

## Project Structure

```
migrationpulse/
├── dags/
│   └── migration_pipeline.py      # Main Airflow DAG (8 tasks, @weekly)
├── spark/
│   ├── bronze_ingest.py           # Movebank API → raw JSON → S3 bronze
│   └── silver_transform.py        # S3 bronze → cleaned Parquet → S3 silver
├── dbt_project/
│   └── migrationpulse/
│       └── models/
│           ├── staging/
│           │   ├── stg_movebank_sightings.sql
│           │   └── schema.yml
│           └── marts/
│               ├── fct_species_movements.sql
│               └── rpt_corridor_deviation.sql
├── ml/
│   └── dtw_corridor_scorer.py     # DTW scoring + MLflow logging
├── dashboard/
│   ├── app.py                     # Streamlit dashboard
│   └── requirements.txt
├── docker-compose.yaml            # Local Airflow stack
├── .env.example                   # Environment variable template
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker Desktop (for local Airflow)
- AWS account with S3 access
- Movebank account (free at movebank.org)
- `pip install requests boto3 pandas pyarrow dbt-core dbt-duckdb mlflow dtaidistance matplotlib streamlit pydeck plotly`

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
foreach ($line in Get-Content .env) {
    if ($line -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}
```

### 3. Start Airflow locally

```bash
docker-compose up -d
# Airflow UI → localhost:8080
# Username: airflow  Password: airflow
# Find migration_pipeline DAG and trigger a run
```

### 4. Run the pipeline manually

```bash
python spark/bronze_ingest.py
python spark/silver_transform.py
```

### 5. Run dbt models

```bash
cd dbt_project/migrationpulse
python -c "from dbt.cli.main import cli; cli()" build \
  --select stg_movebank_sightings fct_species_movements rpt_corridor_deviation
```

### 6. Run DTW scorer

```bash
python ml/dtw_corridor_scorer.py
mlflow ui  # → localhost:5000
```

### 7. Launch the dashboard locally

```bash
cd dashboard
streamlit run app.py  # → localhost:8501
```

---

## Airflow DAG

The main DAG (`migration_pipeline`) runs on a `@weekly` schedule. Tasks execute in the following order:

| Task | Operator | Description |
|---|---|---|
| `check_api_health` | PythonOperator | Confirms Movebank API is reachable before fetching |
| `fetch_movebank_data` | PythonOperator | Pulls new GPS records for all tracked species |
| `upload_to_s3` | PythonOperator | Confirms raw JSON is written to S3 bronze bucket |
| `run_pyspark_transform` | PythonOperator | Applies Silver-layer cleaning and typing |
| `run_dbt_models` | BashOperator | Runs dbt models (staging → marts) |
| `run_dbt_tests` | BashOperator | Runs dbt build with tests; fails DAG on data quality issues |
| `score_anomalies` | PythonOperator | DTW corridor deviation scoring; results logged to MLflow |
| `notify_on_anomalies` | PythonOperator | Prints alert if anomaly rate exceeds 5% threshold |

---

## Data Source

**Bald Eagle (Haliaeetus leucocephalus) in the Pacific Northwest**
- Study ID: `430263960`
- PI: Myles Lamont / Bald Eagle Tracking Alliance
- License: CC0 (public domain)
- Coverage: 2018 – present (actively updated)
- Records: 120,522+ GPS fixes across 40 individuals

All animal tracking data sourced from [Movebank](https://movebank.org), hosted by the Max Planck Institute of Animal Behavior.

---

## S3 Bucket Structure

```
migrationpulse-bronze/
└── bald_eagle/2026/03/22/raw_213007.json

migrationpulse-silver/
└── bald_eagle/2026/03/22/silver_222624.parquet

migrationpulse-gold/
└── (dbt mart outputs)
```

---

## dbt Models

| Model | Layer | Description |
|---|---|---|
| `stg_movebank_sightings` | Staging | Reads S3 silver Parquet, renames columns, filters null coordinates |
| `fct_species_movements` | Mart | One row per GPS fix; adds displacement and speed_deg_per_hour |
| `rpt_corridor_deviation` | Mart | Weekly aggregate per individual: avg position, speed, bounding box |

### Tests

- `not_null` on `individual_id`, `timestamp`, `latitude`, `longitude`, `species`
- `accepted_values` on `species` — only whitelisted study species pass through

---

## DTW Corridor Deviation

Each pipeline run computes a DTW distance score per individual, comparing that week's GPS trajectory against a species-level template built from median lat/long paths across all individuals.

**How it works:**
1. Build a historical template: median latitude per calendar day of year across all individuals
2. For each individual, extract their ordered sequence of GPS fixes
3. Compute Sakoe-Chiba banded DTW distance (window=30) between the individual's latitude sequence and the template
4. Flag individuals whose DTW distance exceeds 2 standard deviations above the species mean as corridor deviations

**Why DTW over point-based methods:** DTW treats the full trajectory as the unit of analysis and handles sequences of different lengths with non-linear time alignment. It detects an individual flying the wrong route even if each individual GPS fix has normal speed and heading.

---

## MLflow Experiment Tracking

Every pipeline run logs a new experiment run under `migration_pulse`.

```bash
mlflow ui  # → localhost:5000
```

**Logged per run:**

| Type | Details |
|---|---|
| Parameters | `dtw_window`, `anomaly_threshold_std` |
| Metrics | `mean_dtw_distance`, `std_dtw_distance`, `anomaly_threshold`, `anomaly_rate`, `total_individuals`, `anomaly_count` |
| Artifacts | DTW distance distribution plot |

---

## Creator

Yvonne Hong <3

## License

MIT License. Animal tracking data: respective study authors via Movebank.