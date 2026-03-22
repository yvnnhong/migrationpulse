from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.http.sensors.http import HttpSensor
from datetime import datetime, timedelta
default_args = {
    'owner': 'migrationpulse',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
}

with DAG(
    dag_id='migration_pipeline',
    default_args=default_args,
    description='Weekly animal migration telemetry pipeline',
    schedule='@weekly',
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['migrationpulse', 'movebank', 'delta-lake'],
) as dag:

    check_api_health = HttpSensor(
        task_id='check_api_health',
        http_conn_id='movebank_api',
        endpoint='/movebank/service/direct-read?entity_type=study&limit=1',
        timeout=30,
        poke_interval=10,
    )

    fetch_movebank_data = PythonOperator(
        task_id='fetch_movebank_data',
        python_callable=lambda: print("TODO: fetch Movebank GPS records"),
    )

    upload_to_blob = PythonOperator(
        task_id='upload_to_blob',
        python_callable=lambda: print("TODO: upload raw JSON to Azure Blob bronze zone"),
    )

    run_pyspark_transform = BashOperator(
        task_id='run_pyspark_transform',
        bash_command='echo "TODO: run PySpark silver transform"',
    )

    run_dbt_models = BashOperator(
        task_id='run_dbt_models',
        bash_command='echo "TODO: dbt build"',
    )

    run_dbt_tests = BashOperator(
        task_id='run_dbt_tests',
        bash_command='echo "TODO: dbt test"',
    )

    score_anomalies = PythonOperator(
        task_id='score_anomalies',
        python_callable=lambda: print("TODO: DTW corridor scoring + MLflow logging"),
    )

    notify_on_anomalies = BashOperator(
        task_id='notify_on_anomalies',
        bash_command='echo "TODO: send alert digest if anomaly rate > 5%"',
    )

    # Task dependencies — this defines the order
    check_api_health >> fetch_movebank_data >> upload_to_blob >> run_pyspark_transform >> run_dbt_models >> run_dbt_tests >> score_anomalies >> notify_on_anomalies