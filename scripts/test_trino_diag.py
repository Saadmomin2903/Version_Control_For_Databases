
import trino
import time

def test_trino_connection():
    print("🔍 Testing Trino Connection...")
    try:
        conn = trino.dbapi.connect(
            host='10.0.0.148', # VM1 Private IP from Airflow DAG
            port=8080,
            user='trino',
            catalog='iceberg',
            schema='ecommerce',
        )
        cur = conn.cursor()
        
        print("🚀 Running quick sanity check (SELECT 1)...")
        start = time.time()
        cur.execute("SELECT 1")
        cur.fetchone()
        print(f"✅ Sanity check passed in {time.time() - start:.2f}s")
        
        print("🚀 Checking tables in ecommerce schema...")
        cur.execute("SHOW TABLES")
        tables = cur.fetchall()
        print(f"✅ Found {len(tables)} tables: {[t[0] for t in tables]}")
        
        print("🚀 Testing query on small dataset (LIMIT 5)...")
        start = time.time()
        cur.execute("SELECT * FROM customer_segments_ml LIMIT 5")
        cur.fetchall()
        print(f"✅ Small query passed in {time.time() - start:.2f}s")
        
    except Exception as e:
        print(f"❌ Trino Connection Failed: {e}")

if __name__ == "__main__":
    test_trino_connection()
