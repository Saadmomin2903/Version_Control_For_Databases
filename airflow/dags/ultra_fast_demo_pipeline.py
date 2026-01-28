
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Default arguments for the Demo DAG
default_args = {
    'owner': 'lakehouse-demo',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0, # No retries for demo to see failures immediately if any
}

# Define the DAG
dag = DAG(
    'ultra_fast_demo_pipeline',
    default_args=default_args,
    description='ULTRA-FAST Demo: 10 Records (Bronze -> Silver -> Gold -> Platinum)',
    schedule_interval=None, # Manual only
    catchup=False,
    tags=['demo', 'ultra-fast', 'nessie'],
)

# SSH Prefix for VM1 (Assumes network_mode: host for Airflow)
SSH_CMD = 'ssh -o StrictHostKeyChecking=no -i /opt/airflow/dags/keys/oracle-vm1.key ubuntu@10.0.0.148'

# 1. Bronze Stage
bronze_demo = BashOperator(
    task_id='bronze_ingestion_10_rows',
    bash_command=f'{SSH_CMD} "docker exec lakehouse-spark python3 /home/jovyan/scripts/demo/bronze_orders_demo.py"',
    dag=dag,
)

# 2. Silver Stage
silver_demo = BashOperator(
    task_id='silver_transform_10_rows',
    bash_command=f'{SSH_CMD} "docker exec lakehouse-spark python3 /home/jovyan/scripts/demo/silver_orders_demo.py"',
    dag=dag,
)

# 3. Gold Stage
gold_demo = BashOperator(
    task_id='gold_aggregation_10_rows',
    bash_command=f'{SSH_CMD} "docker exec lakehouse-spark python3 /home/jovyan/scripts/demo/gold_sales_demo.py"',
    dag=dag,
)

# 4. Platinum Stage
platinum_demo = BashOperator(
    task_id='platinum_ml_insights_10_rows',
    bash_command=f'{SSH_CMD} "docker exec lakehouse-spark python3 /home/jovyan/scripts/demo/platinum_ml_demo.py"',
    dag=dag,
)

# Dependencies
bronze_demo >> silver_demo >> gold_demo >> platinum_demo
