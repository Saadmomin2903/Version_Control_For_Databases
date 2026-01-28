"""
Bronze Layer Builder
Executes all Bronze Layer ingestion scripts sequentially.
Run this via Airflow or manually to rebuild the Bronze Layer.
"""

import subprocess
import sys
import os

def run_script(script_path):
    print(f"\n{'='*50}")
    print(f"🚀 Running: {os.path.basename(script_path)}")
    print(f"{'='*50}\n")
    
    # Run the script using the same python interpreter
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    
    # Stream output to stdout/stderr
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
        
    if result.returncode != 0:
        print(f"\n❌ Error running {script_path}. Exit code: {result.returncode}")
        sys.exit(result.returncode)
    else:
        print(f"\n✅ Successfully finished: {os.path.basename(script_path)}")

def build_bronze_layer():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    scripts = [
        "ingest_customers_spark.py",
        "ingest_orders_spark.py"
    ]
    
    for script in scripts:
        full_path = os.path.join(script_dir, script)
        run_script(full_path)
    
    print("\n🎉 Bronze Layer Build Complete!")

if __name__ == "__main__":
    build_bronze_layer()
