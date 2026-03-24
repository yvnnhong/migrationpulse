import sys
import os
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.bash import BashOperator
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/airflow')

default_args = {
    'owner': 'migrationpulse',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
}

def check_api_health_fn():
    import requests
    resp = requests.get(
        'https://www.movebank.org/movebank/service/direct-read'
        '?entity_type=event&study_id=430263960&individual_local_identifier=BACA01',
        auth=(
            os.environ.get('MOVEBANK_USERNAME'),
            os.environ.get('MOVEBANK_PASSWORD')
        ),
        timeout=30
    )
    if resp.status_code != 200:
        raise Exception(f"Movebank API unhealthy: {resp.status_code}")
    print(f"Movebank API healthy — status {resp.status_code}")

def fetch_movebank_data_fn():
    import subprocess
    result = subprocess.run(
        ['python', '/opt/airflow/spark/bronze_ingest.py'],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Bronze ingest failed: {result.stderr}")

def run_silver_transform_fn():
    import subprocess
    result = subprocess.run(
        ['python', '/opt/airflow/spark/silver_transform.py'],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Silver transform failed: {result.stderr}")

def score_anomalies_fn():
    import subprocess
    result = subprocess.run(
        ['python', '/opt/airflow/ml/dtw_corridor_scorer.py'],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"DTW scoring failed: {result.stderr}")

def notify_on_anomalies_fn():
    import mlflow
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name("migration_pulse")
    if experiment is None:
        print("No MLflow experiment found, skipping notification")
        return
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["start_time DESC"],
        max_results=1
    )
    if not runs:
        print("No runs found, skipping notification")
        return
    anomaly_rate = runs[0].data.metrics.get("anomaly_rate", 0)
    anomaly_count = int(runs[0].data.metrics.get("anomaly_count", 0))
    if anomaly_rate > 0.05:
        print(f"ALERT: Anomaly rate {anomaly_rate:.1%} exceeds 5% threshold — {anomaly_count} individuals flagged")
    else:
        print(f"Anomaly rate {anomaly_rate:.1%} — pipeline healthy")

with DAG(
    dag_id='migration_pipeline',
    default_args=default_args,
    description='Weekly animal migration telemetry pipeline',
    schedule='@weekly',
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['migrationpulse', 'movebank', 'aws-s3'],
) as dag:

    check_api_health = PythonOperator(
        task_id='check_api_health',
        python_callable=check_api_health_fn,
    )

    fetch_movebank_data = PythonOperator(
        task_id='fetch_movebank_data',
        python_callable=fetch_movebank_data_fn,
    )

    upload_to_s3 = PythonOperator(
        task_id='upload_to_s3',
        python_callable=lambda: print("Bronze JSON already uploaded inside fetch_movebank_data"),
    )

    run_pyspark_transform = PythonOperator(
        task_id='run_pyspark_transform',
        python_callable=run_silver_transform_fn,
    )

    run_dbt_models = BashOperator(
        task_id='run_dbt_models',
        bash_command=(
            'cd /opt/airflow/dbt_project/migrationpulse && '
            'python -c "from dbt.cli.main import cli; cli()" run '
            '--select stg_movebank_sightings fct_species_movements rpt_corridor_deviation'
        ),
    )

    run_dbt_tests = BashOperator(
        task_id='run_dbt_tests',
        bash_command=(
            'cd /opt/airflow/dbt_project/migrationpulse && '
            'python -c "from dbt.cli.main import cli; cli()" build '
            '--select stg_movebank_sightings fct_species_movements rpt_corridor_deviation'
        ),
    )

    score_anomalies = PythonOperator(
        task_id='score_anomalies',
        python_callable=score_anomalies_fn,
    )

    notify_on_anomalies = PythonOperator(
        task_id='notify_on_anomalies',
        python_callable=notify_on_anomalies_fn,
    )

    # Task dependencies
    check_api_health >> fetch_movebank_data >> upload_to_s3 >> run_pyspark_transform >> run_dbt_models >> run_dbt_tests >> score_anomalies >> notify_on_anomalies