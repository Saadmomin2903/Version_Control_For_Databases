# Branch Naming Clarification: "gold" vs "main"

## ❓ Question: Are "gold" and "main" branches different?

**Short Answer**: YES, they are different branches, but **"gold" branch is created but NEVER USED!**

---

## 🔍 What's Actually Happening

### Branches Created
```bash
# scripts/utils/create_nessie_branches.py creates:
bronze ✅ (used)
silver ✅ (used)
gold   ⚠️  (created but UNUSED!)
main   ✅ (default, used for production)
```

### How Your Pipeline Actually Works
```
📊 Data Flow:
CSV Files 
  ↓
bronze branch (ingest_orders_spark.py, ingest_customers_spark.py)
  ↓
silver branch (transform_orders_silver.py, transform_customers_silver.py)
  ↓
main branch (aggregate_customer_summary_gold.py) ← NOT gold branch!
```

### Proof from Your Code

**Branch Creation** (`create_nessie_branches.py`):
```python
BRANCHES = ["bronze", "silver", "gold"]  # Creates all 3
```

**Gold Script** (`aggregate_customer_summary_gold.py` line 40):
```python
.set('spark.sql.catalog.nessie.ref', 'main')  # ← Writes to MAIN!
```

**Comment in Code** (line 5):
```python
"""
Writes to main branch (Gold = Production)
"""
```

---

## 📋 Branch Status Table

| Branch Name | Created? | Used? | Contains Data? | Purpose |
|-------------|----------|-------|----------------|---------|
| `bronze` | ✅ Yes | ✅ Yes | ✅ Yes | Raw data ingestion |
| `silver` | ✅ Yes | ✅ Yes | ✅ Yes | Cleaned/validated data |
| **`gold`** | ✅ Yes | ❌ **NO** | ❌ **Empty** | **Unused!** |
| `main` | ✅ Default | ✅ Yes | ✅ Yes | Production gold layer |

---

## 🎯 Current Architecture

### What You Have Now:
```
Medallion Layers          Nessie Branches
─────────────────         ───────────────
Bronze Layer        →     bronze branch
Silver Layer        →     silver branch  
Gold Layer          →     main branch (!!)
                          
(gold branch exists but is empty)
```

### Why This Design?

The code treats **`main` as the production branch** (similar to Git):
- Bronze/Silver branches are "working branches"
- `main` is where final, production-ready data lives
- The "gold" branch was created but isn't actually needed

---

## 💡 Two Ways Forward

### Option 1: Keep Current Approach (Recommended ✅)

**Remove the unused "gold" branch creation**:

Edit `scripts/utils/create_nessie_branches.py`:
```python
# OLD:
BRANCHES = ["bronze", "silver", "gold"]

# NEW:
BRANCHES = ["bronze", "silver"]  # Remove "gold"
```

**Architecture becomes clearer**:
```
Bronze Layer → bronze branch (raw)
Silver Layer → silver branch (curated)
Gold Layer   → main branch   (production)
```

**Pros**:
- ✅ Less confusion
- ✅ Matches actual usage
- ✅ "main" = production is familiar from Git
- ✅ Simpler to explain

---

### Option 2: Use "gold" Branch Properly

**Change gold script to use "gold" branch**:

Edit `scripts/gold/aggregate_customer_summary_gold.py`:

```python
# Line 40: Change
.set('spark.sql.catalog.nessie.ref', 'gold')  # Instead of 'main'

# Line 169: Write to gold branch
spark.sql("""
    CREATE OR REPLACE TABLE nessie.ecommerce.`customer_summary@gold`
    USING iceberg
    AS SELECT * FROM customer_summary_temp
""")
```

**Then merge gold → main when ready for production**:
```bash
# Promote gold to production
curl -X POST "http://localhost:19120/api/v1/trees/branch/main/merge" \
  -H "Content-Type: application/json" \
  -d '{"fromRef": "gold", "message": "Release gold layer to production"}'
```

**Architecture becomes**:
```
Bronze Layer → bronze branch (raw)
Silver Layer → silver branch (curated)
Gold Layer   → gold branch   (aggregated)
              ↓ (merge)
              main branch    (production release)
```

**Pros**:
- ✅ Consistent layer-to-branch mapping
- ✅ Extra isolation for testing aggregations
- ✅ Can test gold metrics before releasing

**Cons**:
- ❌ Extra step (merge gold → main)
- ❌ More complex
- ❌ Adds overhead for simple pipelines

---

## 🎬 Comparison Example

### Current Flow (main as gold):
```python
# Read from silver
customers = spark.sql("SELECT * FROM nessie.ecommerce.`customers_silver@silver`")

# Aggregate
summary = customers.groupBy(...).agg(...)

# Write to main (production immediately)
summary.writeTo("nessie.ecommerce.customer_summary").createOrReplace()
```

### Alternative Flow (using gold branch):
```python
# Read from silver
customers = spark.sql("SELECT * FROM nessie.ecommerce.`customers_silver@silver`")

# Aggregate
summary = customers.groupBy(...).agg(...)

# Write to gold branch (not production yet)
spark.sql("""
    CREATE OR REPLACE TABLE nessie.ecommerce.`customer_summary@gold`
    AS SELECT * FROM summary_temp
""")

# Test on gold branch
spark.sql("SELECT * FROM nessie.ecommerce.`customer_summary@gold`").show()

# If good, merge to main
# curl -X POST .../merge ...
```

---

## 📊 What to Check Right Now

### See which branches have data:

```bash
# List tables on each branch
echo "=== BRONZE BRANCH ==="
curl -s "http://localhost:19120/api/v1/trees/tree/bronze/entries" | \
  python3 -c "import json, sys; [print(e['name']['elements']) for e in json.load(sys.stdin).get('entries', [])]"

echo "=== SILVER BRANCH ==="
curl -s "http://localhost:19120/api/v1/trees/tree/silver/entries" | \
  python3 -c "import json, sys; [print(e['name']['elements']) for e in json.load(sys.stdin).get('entries', [])]"

echo "=== GOLD BRANCH (probably empty) ==="
curl -s "http://localhost:19120/api/v1/trees/tree/gold/entries" | \
  python3 -c "import json, sys; [print(e['name']['elements']) for e in json.load(sys.stdin).get('entries', [])]"

echo "=== MAIN BRANCH (has gold layer) ==="
curl -s "http://localhost:19120/api/v1/trees/tree/main/entries" | \
  python3 -c "import json, sys; [print(e['name']['elements']) for e in json.load(sys.stdin).get('entries', [])]"
```

**Expected Output**:
```
=== BRONZE BRANCH ===
['ecommerce', 'orders_bronze']
['ecommerce', 'customers_bronze']

=== SILVER BRANCH ===
['ecommerce', 'orders_silver']
['ecommerce', 'customers_silver']

=== GOLD BRANCH (probably empty) ===
(nothing)  ← Empty!

=== MAIN BRANCH (has gold layer) ===
['ecommerce', 'customer_summary']
```

---

## ✅ My Recommendation

**Use Option 1**: Remove the "gold" branch from creation since it's not used.

### Quick Fix:

```bash
# Edit the branch creation script
sed -i.bak 's/BRANCHES = \["bronze", "silver", "gold"\]/BRANCHES = ["bronze", "silver"]/' \
  scripts/utils/create_nessie_branches.py

# Verify the change
grep "BRANCHES =" scripts/utils/create_nessie_branches.py
```

### Update Documentation:

Make it clear that:
```
Bronze Layer → bronze branch
Silver Layer → silver branch
Gold Layer → main branch (production)
```

This matches your actual implementation and reduces confusion! 🎯

---

## 📚 Summary

**Question**: Are gold and main different?  
**Answer**: Yes, but gold is unused!

**Current Reality**:
- `gold` branch = created but empty
- `main` branch = contains your gold layer data

**Recommendation**:
- Stop creating the unused "gold" branch
- Document that main = production = gold layer
- Keep your current working approach

**If You Want Isolation**:
- Modify gold script to use "gold" branch
- Add merge step from gold → main
- Keeps production (main) separate from development (gold)

Choose based on your needs:
- **Simple pipeline**: Use main (current approach) ✅
- **Need testing safety**: Use gold branch + merge to main

---

*The key is consistency: either use gold everywhere or remove it entirely. Don't leave it half-created!*
