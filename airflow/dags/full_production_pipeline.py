
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Default arguments for the Production DAG
default_args = {
    'owner': 'lakehouse-prod',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'full_production_pipeline',
    default_args=default_args,
    description='FULL Production Pipeline: Whole Dataset (Bronze -> Silver -> Gold -> Platinum)',
    schedule_interval=None, # Manual only for now
    catchup=False,
    tags=['production', 'full-load', 'nessie'],
)

# SSH Prefix for VM1 (Assumes network_mode: host for Airflow)
SSH_CMD = 'ssh -o StrictHostKeyChecking=no -i /opt/airflow/dags/keys/oracle-vm1.key ubuntu@10.0.0.148'

# 1. Bronze Stage - Full Ingestion
bronze_prod = BashOperator(
    task_id='bronze_full_ingestion',
    bash_command=f'{SSH_CMD} "docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_full_dataset.py"',
    dag=dag,
)

# 2. Silver Stage - Full Transformation
silver_prod = BashOperator(
    task_id='silver_full_transformation',
    bash_command=f'{SSH_CMD} "docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/build_silver_layer.py"',
    dag=dag,
)

# 3. Gold Stage - Full Aggregation
gold_prod = BashOperator(
    task_id='gold_full_aggregation',
    bash_command=f'{SSH_CMD} "docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/build_gold_layer.py"',
    dag=dag,
)

# 4. Platinum Stage - Full ML Pipeline
platinum_prod = BashOperator(
    task_id='platinum_full_ml_pipeline',
    bash_command=f'{SSH_CMD} "docker exec lakehouse-spark python3 /home/jovyan/scripts/recovery/real_ml_pipeline_full.py"',
    dag=dag,
)

# Dependencies
bronze_prod >> silver_prod >> gold_prod >> platinum_prod
