import sys
import os
import polars as pl
from datetime import datetime, timedelta
import random

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def generate_orders_data(num_records=1000, seed=42):
    """Generate sample orders data"""
    random.seed(seed)  # For reproducibility
    start_date = datetime(2024, 1, 1)
    
    data = {
        "order_id": [f"ORD{i:06d}" for i in range(1, num_records + 1)],
        "customer_id": [f"CUST{random.randint(1, 200):04d}" for _ in range(num_records)],
        "order_date": [start_date + timedelta(days=random.randint(0, 365)) for _ in range(num_records)],
        "total_amount": [round(random.uniform(10, 1000), 2) for _ in range(num_records)],
        "status": [random.choice(["pending", "completed", "cancelled", "refunded"]) for _ in range(num_records)],
        "created_at": [datetime.now() for _ in range(num_records)],
    }
    return pl.DataFrame(data)

def generate_customers_data(num_records=200, seed=42):
    """Generate sample customers data"""
    random.seed(seed)  # For reproducibility
    
    data = {
        "customer_id": [f"CUST{i:04d}" for i in range(1, num_records + 1)],
        "name": [f"Customer {i}" for i in range(1, num_records + 1)],
        "email": [f"customer{i}@example.com" for i in range(1, num_records + 1)],
        "signup_date": [datetime(2023, 1, 1) + timedelta(days=random.randint(0, 500)) for _ in range(num_records)],
        "is_active": [random.choice([True, False]) for _ in range(num_records)],
    }
    return pl.DataFrame(data)

def main():
    print("=" * 60)
    print("GENERATING SAMPLE DATA")
    print("=" * 60)
    
    # Ensure data/raw directory exists
    os.makedirs("data/raw", exist_ok=True)
    
    # Generate orders data
    print("\nGenerating orders data...")
    orders_df = generate_orders_data(1000)
    orders_path = "data/raw/orders.csv"
    orders_df.write_csv(orders_path)
    print(f"✓ Generated {orders_path}: {len(orders_df):,} records")
    print(f"  File size: {os.path.getsize(orders_path) / 1024:.2f} KB")
    
    # Generate customers data
    print("\nGenerating customers data...")
    customers_df = generate_customers_data(200)
    customers_path = "data/raw/customers.csv"
    customers_df.write_csv(customers_path)
    print(f"✓ Generated {customers_path}: {len(customers_df):,} records")
    print(f"  File size: {os.path.getsize(customers_path) / 1024:.2f} KB")
    
    # Display sample data
    print("\n" + "=" * 60)
    print("SAMPLE ORDERS DATA (first 5 rows)")
    print("=" * 60)
    print(orders_df.head(5))
    
    print("\n" + "=" * 60)
    print("SAMPLE CUSTOMERS DATA (first 5 rows)")
    print("=" * 60)
    print(customers_df.head(5))
    
    # Data quality summary
    print("\n" + "=" * 60)
    print("DATA QUALITY SUMMARY")
    print("=" * 60)
    print(f"Orders:")
    print(f"  Total records: {len(orders_df):,}")
    print(f"  Unique order_ids: {orders_df['order_id'].n_unique():,}")
    print(f"  Date range: {orders_df['order_date'].min()} to {orders_df['order_date'].max()}")
    print(f"  Amount range: ${orders_df['total_amount'].min():.2f} - ${orders_df['total_amount'].max():.2f}")
    
    print(f"\nCustomers:")
    print(f"  Total records: {len(customers_df):,}")
    print(f"  Unique customer_ids: {customers_df['customer_id'].n_unique():,}")
    print(f"  Active customers: {customers_df['is_active'].sum()}")
    
    print("\n✓ Sample data generation complete!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"✗ Error generating sample data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)