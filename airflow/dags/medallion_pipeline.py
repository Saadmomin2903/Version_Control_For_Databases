from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Default arguments for the DAG
default_args = {
    'owner': 'lakehouse-data-eng',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email': ['admin@example.com'],
    'email_on_failure': False, # Set to True if SMTP configured
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'medallion_architecture_pipeline',
    default_args=default_args,
    description='End-to-end Bronze -> Silver -> Gold Lakehouse Pipeline',
    schedule_interval='@daily', # Run once a day
    catchup=False,
    tags=['lakehouse', 'spark', 'nessie'],
)

# -------------------------------------------------------------
# TASK 1: BRONZE LAYER (Raw Ingestion)
# -------------------------------------------------------------
# Executes the bronze ingestion script inside the Spark container
build_bronze = BashOperator(
    task_id='build_bronze_layer',
    bash_command='docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/build_bronze_layer.py',
    dag=dag,
)

# -------------------------------------------------------------
# TASK 2: SILVER LAYER (Cleaning & Validation)
# -------------------------------------------------------------
# Runs transformation + Great Expectations validation
# This will FAIL if validation fails, stopping the pipeline (WAP)
build_silver = BashOperator(
    task_id='build_silver_layer',
    bash_command='docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/transform_orders_silver.py',
    dag=dag,
)

# -------------------------------------------------------------
# TASK 3: GOLD LAYER (Business Aggregates)
# -------------------------------------------------------------
# Runs aggregations on validated Silver data
build_gold = BashOperator(
    task_id='build_gold_layer',
    bash_command='docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/build_gold_layer.py',
    dag=dag,
)

# -------------------------------------------------------------
# PIPELINE DEPENDENCIES
# -------------------------------------------------------------
# Bronze -> Silver -> Gold
build_bronze >> build_silver >> build_gold
