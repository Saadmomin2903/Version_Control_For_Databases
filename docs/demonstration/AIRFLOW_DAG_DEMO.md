# 🎯 Airflow DAG Trigger Demo

## What This Shows

Demonstrates triggering the automated Medallion pipeline via Apache Airflow.

---

## 🎯 Demo Option 1: Browser UI

1. Open http://140.238.224.207:8080
2. Login: `admin` / `admin`
3. Find: `medallion_architecture_pipeline`
4. Toggle **ON** to unpause
5. Click **▶️ Trigger DAG**

---

## 🎯 Demo Option 2: Command Line

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-airflow airflow dags trigger medallion_architecture_pipeline"
```

---

## Expected Output

```
dag_id                          | run_type | state
================================+==========+========
medallion_architecture_pipeline | manual   | queued
```

---

## Verify Execution

### Check DAG status:
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-airflow airflow dags list-runs -d medallion_architecture_pipeline"
```

### View task logs (in Airflow UI):
1. Click on the DAG run
2. Click on any task
3. Select "Log" tab

---

## 💼 Business Value

| Feature | Benefit |
|---------|---------|
| **Scheduled execution** | Automatic daily/hourly runs |
| **Dependency management** | Tasks run in correct order |
| **Retry on failure** | Auto-retry with backoff |
| **Full visibility** | Logs, duration, status |

---

## 🎤 Presentation Script

> "For production, we use Apache Airflow to orchestrate the pipeline."
>
> *[Show Airflow UI]*
>
> "This DAG runs our complete Medallion architecture:"
> - Bronze → Silver → Gold transformations
> - Automatic scheduling (daily at midnight)
> - Retry logic on failures
>
> *[Trigger the DAG]*
>
> "The pipeline is now executing. We can monitor progress in real-time."
