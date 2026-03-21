# MigrationPulse
### Animal Migration Analytics Pipeline

`Airflow` · `PySpark` · `dbt` · `Delta Lake` · `Azure` · `MLflow` · `Streamlit`

---

A weekly-automated data engineering pipeline that ingests GPS telemetry from the Movebank Animal Tracking API for 5 migratory species, transforms and models the data at scale with PySpark and dbt, stores it in a Delta Lake medallion architecture on Azure, tracks ML experiments with MLflow, and surfaces findings through a live Streamlit dashboard.

**Live Demo:** [streamlit link] · **Status:** Active

---

## What It Does

- Fetches new Movebank GPS records weekly via Airflow DAG (Osprey, Swainson's Hawk, Monarch Butterfly, Gray Whale, and Caribou)
- Stores raw JSON in Azure Blob Storage and processes it through Bronze → Silver → Gold Delta Lake layers using PySpark
- Models transformations with dbt — staging, fact, and reporting mart layers with built-in data quality tests
- Detects migration corridor deviations per species using DTW (Dynamic Time Warping); all experiment runs logged with MLflow
- Visualizes migration paths, corridor deviations, and anomalies on a live Streamlit dashboard with pydeck maps

---

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | Apache Airflow 2.x |
| Distributed Compute | PySpark (local or Azure HDInsight) |
| Storage | Delta Lake on Azure Blob Storage |
| Data Modeling | dbt Core |
| ML Tracking | MLflow |
| Cloud | Microsoft Azure |
| Dashboard | Streamlit + pydeck + Plotly |
| Language | Python 3.11 |
| Data Source | Movebank REST API (free, public studies) |
| Dev | Docker Compose, Git, GitHub Actions |

---

## Project Structure

```
migration_pulse/
├── dags/
│   └── migration_pipeline.py      # Main Airflow DAG
├── spark/
│   ├── bronze_ingest.py           # Raw JSON → Delta Bronze
│   └── silver_transform.py        # Bronze → Silver (clean + type)
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
├── docker-compose.yml             # Local Airflow stack
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker Desktop (for local Airflow)
- Azure account (free tier works — Blob Storage is ~$0.02/GB)
- Movebank account (free at movebank.org) — needed for API key on some studies
- `pip install dbt-spark mlflow dtaidistance`

### 1. Clone and configure

```bash
git clone https://github.com/[you]/migration-pulse
cd migration-pulse
cp .env.example .env
# Fill in: AZURE_CONN_STR, MOVEBANK_USERNAME, MOVEBANK_PASSWORD
```

### 2. Start Airflow locally

```bash
docker-compose up -d
# Airflow UI → localhost:8080
# Username: admin  Password: admin
# Enable the 'migration_pipeline' DAG and trigger a run
```

### 3. Run dbt models

```bash
cd dbt_project
dbt deps
dbt build          # runs models + tests
dbt docs generate  # optional: browse lineage graph
```

### 4. Launch the dashboard

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
| `fetch_movebank_data` | HttpOperator | Pulls new GPS records for all tracked species |
| `upload_to_blob` | PythonOperator | Writes raw JSON to Azure Blob bronze zone |
| `run_pyspark_transform` | SparkSubmitOperator | Applies Silver-layer cleaning and typing |
| `run_dbt_models` | BashOperator | Runs `dbt build` (staging → marts) |
| `run_dbt_tests` | BashOperator | Runs `dbt test`; fails DAG loudly on data quality issues |
| `score_anomalies` | PythonOperator | DTW corridor deviation scoring; results logged to MLflow |
| `notify_on_anomalies` | EmailOperator | Alert digest if anomaly rate exceeds 5% threshold |

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

**Why DTW over point-based anomaly detection:** DTW treats the full trajectory as the unit of analysis. It catches an Osprey flying the wrong route even if every individual GPS fix has normal speed and heading — something a point-scoring method like Isolation Forest cannot do.

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

> Most recent run: [date]

- XX,XXX GPS fixes ingested across 5 species this week
- Corridor anomaly rate: X.X% (threshold: 5%)
- Highest deviation species this week: [species]
- Notable finding: [auto-populated from dashboard]

---

## Data Source

All animal tracking data sourced from [Movebank](https://movebank.org), a free repository hosted by the Max Planck Institute of Animal Behavior. Data is used under Movebank's terms for non-commercial research. Individual study citations are logged in `dbt_project/sources.yml`.

---
## Creator
Yvonne Hong <3 

## License

MIT License. See `LICENSE` for details.

Animal tracking data: © respective study authors via Movebank. See `data/citations.md`.