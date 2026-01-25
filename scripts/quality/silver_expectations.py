import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest
import pandas as pd

def validate_silver_orders(spark_df):
    """
    Validate Silver layer orders before merge.
    Returns:
        bool: True if validation passed, False otherwise
    """
    print("\n🧐 Starting Silver Layer Data Validation...")
    
    # Convert Spark DF to Pandas for GX validation (for small batches)
    # For large data, we would use Spark DF directly with GX Spark execution engine
    pdf = spark_df.toPandas()
    
    # Create GX Data Context (in-memory for this script)
    context = gx.get_context()
    
    # Create Data Source & Asset
    datasource_name = "spark_dataframe_datasource"
    asset_name = "silver_orders"
    
    datasource = context.sources.add_pandas(datasource_name)
    asset = datasource.add_dataframe_asset(asset_name, pdf)
    
    # Create Expectation Suite
    suite_name = "silver_orders_quality_suite"
    suite = context.add_or_update_expectation_suite(suite_name)
    
    # Define Expectations
    expectations = [
        # Critical: No null IDs
        {"expectation_type": "expect_column_values_to_not_be_null", 
         "kwargs": {"column": "order_id"}},
        {"expectation_type": "expect_column_values_to_not_be_null", 
         "kwargs": {"column": "customer_id"}},
         
        # Business Logic: Prices must be positive
        {"expectation_type": "expect_column_values_to_be_between", 
         "kwargs": {"column": "price", "min_value": 0.01}}, # Price > 0
         
        # Data Integrity: Dates must exist
        {"expectation_type": "expect_column_values_to_not_be_null", 
         "kwargs": {"column": "order_date"}},
    ]
    
    # Add expectations to suite
    for exp in expectations:
        suite.add_expectation(gx.expectations.ExpectationConfiguration(**exp))
        
    print(f"✅ Created Expectation Suite '{suite_name}' with {len(expectations)} rules.")

    # Validate
    batch_request = asset.build_batch_request()
    checkpoint = context.add_or_update_checkpoint(
        name="silver_validation_checkpoint",
        validations=[{
            "batch_request": batch_request,
            "expectation_suite_name": suite_name
        }]
    )
    
    print("🏃 Running Validation...")
    results = checkpoint.run()
    
    start_time = results.run_results[list(results.run_results.keys())[0]]['validation_result']['meta']['validation_time']
    success = results.success
    
    if success:
        print("✅ GREAT EXPECTATIONS: Validation PASSED! Data is clean.")
    else:
        print("❌ GREAT EXPECTATIONS: Validation FAILED! Blocking merge.")
        # Print failure details
        print(results.list_validation_results())
        
    return success

if __name__ == "__main__":
    print("This module provides validation functions for Silver layer ETL.")
