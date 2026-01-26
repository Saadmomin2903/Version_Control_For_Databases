from pyspark.sql import SparkSession
from pyspark.ml.fpm import FPGrowth
from pyspark.sql.functions import col, collect_set, size
import sys

def run_product_recommendation():
    spark = SparkSession.builder \
        .appName("EcommerceProductRecommendation") \
        .master("local[*]") \
        .config("spark.sql.files.ignoreCorruptFiles", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")

    try:
        print("Loading transaction data...")
        import glob
        import os
        
        base_path = r"c:\Users\lenovo\Documents\CDAC project\Version_Control_For_Databases"
        raw_data_path = os.path.join(base_path, "data", "raw", "*.parquet")
        
        files = glob.glob(raw_data_path)
        if not files:
            print("No files found!")
            return
        
        df = spark.read.parquet(*files)
        
        # Filter for 'purchase' events only to get meaningful product associations
        transactions_df = df.filter(col("event_type") == "purchase")
        
        # Prepare Data: Group by user_session to form a basket
        # Filtering out sessions with only 1 item might improve rule quality (optional)
        print("Grouping transactions by session...")
        baskets = transactions_df.groupBy("user_session").agg(collect_set("product_id").alias("items"))
        
        # Filter baskets with at least 2 items to find associations
        # baskets = baskets.filter(size(col("items")) > 1) 
        # (Standard FP-Growth handles single items but they don't generate rules A->B)
        
        print(f"Total Baskets: {baskets.count()}")
        
        # Hyperparameter Sweep
        min_supports = [0.001, 0.005, 0.01]
        min_confidences = [0.1, 0.3, 0.5]
        
        best_model = None
        best_params = {}
        best_num_rules = -1
        
        print("\n--- Starting Hyperparameter Sweep ---")
        
        for min_sup in min_supports:
            for min_conf in min_confidences:
                print(f"\nTraining with minSupport={min_sup}, minConfidence={min_conf}...")
                fp_growth = FPGrowth(itemsCol="items", minSupport=min_sup, minConfidence=min_conf)
                model = fp_growth.fit(baskets)
                
                # Rule Count Sanity Check
                num_rules = model.associationRules.count()
                print(f"Generated {num_rules} rules.")
                
                if num_rules == 0:
                    print("No rules generated. Skipping.")
                    continue
                
                # Heuristic for 'best' model: maximize number of rules (validity check) 
                # or you could pick the one with highest average lift, etc.
                # Here we pick the one with most rules that isn't exploiding crazy high (sanity check provided implicitly by grid)
                # For simplicity, let's track the one that gives us a "healthy" number of rules, e.g. the most rules
                if num_rules > best_num_rules:
                    best_num_rules = num_rules
                    best_model = model
                    best_params = {'minSupport': min_sup, 'minConfidence': min_conf}

        if best_model is None:
            print("No valid rules found with any parameter combination.")
            return

        print(f"\n--- Best Parameters: {best_params} with {best_num_rules} rules ---")
        
        # Display frequent itemsets
        print("\n--- Top Frequent Itemsets (Best Model) ---")
        best_model.freqItemsets.sort(col("freq").desc()).show(10)
        
        # Display generated association rules with Lift
        print("\n--- Association Rules (Best Model) ---")
        # PySpark FPGrowth associationRules dataframe typically contains: antecedent, consequent, confidence, lift, support
        best_model.associationRules.sort(col("lift").desc()).show(20, truncate=False)
        
        # Generate recommendations for a subset of users/baskets
        print("\n--- Sample Recommendations ---")
        recs = best_model.transform(baskets).filter(size(col("prediction")) > 0)
        recs.show(10, truncate=False)
        
        # Save recommendations to Gold
        output_dir = os.path.join(base_path, "data", "gold")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "product_recommendations.csv")
        
        print(f"Saving recommendations to {output_path}...")
        # Collecting to driver and pandas for simplicity as it might be complex type
        # Ideally for big data we explode and save element wise, but for this demo:
        # We will save the rules instead which is cleaner conformant CSV data usually
        
        rules = best_model.associationRules
        # Convert array columns to string if needed for CSV
        # rules is a spark DF.
        rules_pd = rules.toPandas()
        rules_pd.to_csv(output_path, index=False)
        print(f"Saved {len(rules_pd)} association rules to {output_path}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        spark.stop()

if __name__ == "__main__":
    run_product_recommendation()
