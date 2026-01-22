# Ultra-Detailed Production Guide - Part 3 of 4

**Supabase Setup & Dataset Download**

---

## 🎯 What You'll Accomplish in Part 3

By the end of this guide, you will have:
- ✅ Supabase account created (free tier)
- ✅ PostgreSQL database configured
- ✅ Database connection tested
- ✅ Firebolt dataset downloaded (52 GB)
- ✅ AWS CLI configured for Oracle Object Storage

**Time Required**: 3-4 hours (mostly dataset download time)  
**Prerequisites**: Parts 1 & 2 completed

---

## Step 8: Supabase PostgreSQL Setup

### Step 8.1: Navigate to Supabase

**What to do**:
```bash
# Open this URL in your browser:
https://supabase.com/
```

**What you'll see**:
```
Supabase homepage with:
- Large heading: "Build in a weekend, scale to millions"
- Green "Start your project" button (top right)
- Black "Sign up" button (center)
- Features and testimonials below
```

**Action**: Click **"Start your project"** button (top right)

---

### Step 8.2: Sign Up for Supabase

**What you'll see**:
Sign up page with options:

```
┌──────────────────────────────────────┐
│ Sign up to Supabase                  │
├──────────────────────────────────────┤
│                                       │
│ [Continue with GitHub]               │
│                                       │
│ [Continue with Google]               │
│                                       │
│ ────────── or ──────────             │
│                                       │
│ Email: [input]                       │
│ Password: [input]                    │
│                                       │
│ [Sign up]                            │
└──────────────────────────────────────┘
```

**Recommended option**: **Continue with GitHub** or **Continue with Google**

**Why**:
```
✓ Faster (no email verification]
✓ More secure (OAuth)
✓ One-click login
```

**If using GitHub**:
1. Click "Continue with GitHub"
2. Login to GitHub if needed
3. Click "Authorize Supabase"
4. Done!

**If using email/password**:
```
Email: your-email@gmail.com
Password: [strong password - save it!]

Requirements:
  - At least 6 characters
  - Mix of letters and numbers recommended
```

---

### Step 8.3: Create Organization

**What you'll see after signup**:
"Create your organization" page

**Form fields**:

**Organization name**:
```
What to enter: Lakehouse Production
Why: Descriptive name for your project
Can be anything: Your University name, Team name, etc.
```

**Pricing plan** (at bottom):
```
Options shown:
  ○ Free     $0/month  ← Select this
  ○ Pro      $25/month
  ○ Team     $599/month
  ○ Enterprise  Custom

Select: Free
What you get:
  ✓ 500 MB database
  ✓ Unlimited API requests
  ✓ 50,000 monthly active users
  ✓ Up to 2 GB file storage
  ✓ Community support
```

**What form looks like**:
```
┌──────────────────────────────────────┐
│ Create your organization             │
├──────────────────────────────────────┤
│ Organization name:                   │
│ Lakehouse Production                 │
│                                       │
│ Select a plan:                       │
│ ● Free        $0/month               │
│ ○ Pro         $25/month              │
│ ○ Team        $599/month             │
│                                       │
│ [Create organization]                │
└──────────────────────────────────────┘
```

**Action**: Click **"Create organization"** button

---

### Step 8.4: Create Project

**What you'll see**:
"New Project" page

**Form fields**:

**Project name**:
```
What to enter: nessie-metadata
Why: This database stores Nessie's catalog metadata
Be specific: Helps if you create more projects later
```

**Database Password**:
```
⚠️ CRITICAL - You'll need this to connect!

Options:
  1. Click "Generate a password" (recommended)
  2. Enter your own

If using generated password:
  - Click "Generate a password" button
  - A random secure password appears
  - Click the copy icon to copy it
  - SAVE IT IMMEDIATELY in a file

Example generated password:
  8Kp2nF9mQ3xR7vL5wN4jH6
```

**How to save password**:
```bash
# Create credentials file
cat > ~/supabase-credentials.txt << 'EOF'
SUPABASE_PROJECT=nessie-metadata
SUPABASE_PASSWORD=[paste your generated password]
EOF

chmod 600 ~/supabase-credentials.txt
```

**Region**:
```
What you'll see: Dropdown with regions

Options:
  - East US (N. Virginia)     ← Select this
  - West US (Oregon)
  - Europe (Frankfurt)
  - Asia Pacific (Singapore)
  - etc.

Why East US:
  ✓ Closest to Oracle US-Ashburn region
  ✓ Lower latency
  ✓ Better performance

If your team is in Europe/Asia:
  - Choose region closest to you
  - Make sure Oracle region is also nearby
```

**Pricing Plan**:
```
Shows: Free (already selected from previous step)
```

**What form looks like**:
```
┌──────────────────────────────────────┐
│ New Project                          │
├──────────────────────────────────────┤
│ Name: nessie-metadata                │
│                                       │
│ Database Password:                   │
│ 8Kp2nF9mQ3xR7vL5wN4jH6             │
│ [Generate] [Copy]                    │
│                                       │
│ Region: East US (N. Virginia)        │
│                                       │
│ Pricing: Free                        │
│                                       │
│ [Create new project]                 │
└──────────────────────────────────────┘
```

**Action**: Click **"Create new project"** button

---

### Step 8.5: Wait for Database Provisioning

**What you'll see**:
Progress screen:

```
┌──────────────────────────────────────┐
│ Setting up your project              │
├──────────────────────────────────────┤
│                                       │
│   [====================] 45%          │
│                                       │
│ ⏳ Provisioning database...          │
│                                       │
│ This usually takes 2 minutes          │
└──────────────────────────────────────┘
```

**Progress steps you'll see**:
```
1. Initializing project...           ⏳
2. Provisioning database...          ⏳
3. Configuring security...           ⏳
4. Setting up APIs...                ⏳
5. Finalizing setup...               ⏳

After ~2 minutes:
✅ Project ready!
```

**When complete**:
Page redirects to Project Dashboard

---

### Step 8.6: Get Database Connection Details

**What you'll see**:
Project dashboard with:
- Project name at top
- Sidebar with options
- Main dashboard area

**What to do**:
1. Look at sidebar (left)
2. Click **Settings** (gear icon, near bottom)
3. Click **Database** from submenu

**What you'll see on Database page**:

**Connection Info section**:
```
┌──────────────────────────────────────────────────┐
│ Connection info                                  │
├──────────────────────────────────────────────────┤
│ Host                                             │
│ db.xxxxxxxxxxxxxxxx.supabase.co                 │
│ [Copy]                                           │
│                                                   │
│ Database name                                    │
│ postgres                                         │
│                                                   │
│ Port                                             │
│ 5432                                             │
│                                                   │
│ User                                             │
│ postgres                                         │
│                                                   │
│ Password                                         │
│ [The password you set]                           │
└──────────────────────────────────────────────────┘
```

**Connection string section**:
```
┌──────────────────────────────────────────────────┐
│ Connection string                                │
├──────────────────────────────────────────────────┤
│ URI                                              │
│ postgresql://postgres:[password]@db.xxx.supabase.│
│ co:5432/postgres                                 │
│ [Copy]                                           │
│                                                   │
│ JDBC                                             │
│ jdbc:postgresql://db.xxx.supabase.co:5432/postgres│
│ [Copy]                                           │
└──────────────────────────────────────────────────┘
```

**What to copy and save**:

Click [Copy] next to **URI** connection string

**Update your credentials file**:
```bash
cat >> ~/supabase-credentials.txt << 'EOF'

SUPABASE_HOST=db.xxxxxxxxxxxxxxxx.supabase.co
SUPABASE_PORT=5432
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_CONNECTION=postgresql://postgres:[password]@db.xxx.supabase.co:5432/postgres?sslmode=require
EOF
```

**Replace placeholders**:
- Replace `[password]` with your actual password
- The `xxx` should match your actual host

---

### Step 8.7: Test Database Connection

**Install PostgreSQL client** (if not already installed):

**macOS**:
```bash
brew install postgresql@15
```

**Ubuntu/Linux**:
```bash
sudo apt update
sudo apt install postgresql-client
```

**Windows**:
Download from: https://www.postgresql.org/download/windows/

**Test connection**:
```bash
# Use the connection string from Supabase
psql "postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres?sslmode=require"
```

**What you'll see if successful**:
```
psql (15.4)
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, compression: off)
Type "help" for help.

postgres=>
```

**Test queries**:
```sql
-- List databases
\l

-- Should show:
-- postgres, template0, template1

-- List tables (empty for now)
\dt

-- No relations found (this is correct - Nessie will create tables)

-- Quit
\q
```

**✅ Success indicators**:
```
✓ Connected without errors
✓ Prompt shows "postgres=>"
✓ \l command works
✓ SSL connection shown
```

**If connection fails**:
```
Common issues:

1. "could not translate host name"
   Fix: Check host name copied correctly

2. "password authentication failed"
   Fix: Double-check password

3. "connection refused"
   Fix: Check port is 5432, not 543

4. "SSL connection required"
   Fix: Add ?sslmode=require to connection string
```

---

## Step 9: Download Firebolt Dataset

### Step 9.1: Prepare Download Directory

**On your local machine**:

```bash
# Navigate to project
cd ~/Documents/Version_Control_For_Databases

# Create download directory
mkdir -p data/firebolt-raw
cd data/firebolt-raw

# Check available disk space
df -h .
# Need at least 10 GB free (5 GB parquet + headroom)
```

**What you'll see**:
```
Filesystem      Size   Used  Avail Capacity
/dev/disk1     500G   240G   260G    48%
                              ^^^--- Need 10+ GB
```

**Good news**: The Firebolt dataset is in **Parquet format** (~5 GB compressed)
which is much smaller than the original CSV files!

---

### Step 9.2: Install AWS CLI

**(Skip if already installed)**

---

### Step 9.2: Install AWS CLI

**Why AWS CLI**:
```
✓ Firebolt dataset hosted on AWS S3 (public bucket)
✓ AWS CLI = fast, reliable downloads
✓ Resume capability if interrupted
✓ No AWS account needed (public data)
```

**Installation**:

**macOS**:
```bash
brew install awscli

# Verify
aws --version
# Should show: aws-cli/2.x.x
```

**Linux (Ubuntu)**:
```bash
sudo apt update
sudo apt install awscli

# Verify
aws --version
```

**Windows**:
```powershell
# Download installer from:
https://aws.amazon.com/cli/

# Or use Chocolatey:
choco install awscli

# Verify
aws --version
```

---

### Step 9.3: Download Firebolt E-commerce Dataset (Parquet)

**⚠️ CORRECT BUCKET PATH** (verified working):

```bash
# Make sure you're in the right directory
pwd
# Should show: .../Version_Control_For_Databases/data/firebolt-raw

# Download ALL parquet files (~5 GB total, ~1000 files)
aws s3 sync s3://firebolt-sample-datasets-public-us-east-1/ecommerce_primer/parquet/ . \
    --no-sign-request
```

**What you'll see**:
```
download: s3://firebolt.../ecommerce_1_2_0.gz.parquet to ./ecommerce_1_2_0.gz.parquet
download: s3://firebolt.../ecommerce_1_2_1.gz.parquet to ./ecommerce_1_2_1.gz.parquet
...
(hundreds of files downloading)
```

**Download time estimates**:
```
100 Mbps connection: ~15-20 minutes
50 Mbps connection: ~30-40 minutes
25 Mbps connection: ~1 hour
10 Mbps connection: ~2-3 hours
```

**Monitor download**:
```bash
# In another terminal window:
watch -n 10 'ls *.parquet 2>/dev/null | wc -l'

# This shows number of files downloaded
# Final count will be ~1000 files
```

---

### Step 9.4: Verify Downloads Complete

**After download finishes**:

```bash
# Count downloaded files
ls *.parquet | wc -l
# Expected: ~1000 files

# Check total size
du -sh .
# Expected: ~5.0G
```

**What you'll see**:
```
5.0G    .
```

**Dataset info**:
```
Format: Parquet (compressed)
Files: ~1000 parquet files
Total Size: ~5 GB compressed
Records: ~400 million transactions
Schema: E-commerce transactions (similar to your existing orders schema)
```

---

### Step 9.5: No Decompression Needed!

**Parquet files are already optimized**:
```
✓ Columnar format (efficient queries)
✓ Already compressed (gzip)
✓ Spark reads directly (no gunzip needed)
✓ Perfect for lakehouse processing
```

**Your bronze scripts will read these directly!**

---

## Step 10: Configure AWS CLI for Oracle Storage

### Step 10.1: Configure AWS CLI Credentials

**What to do**:
```bash
aws configure
```

**What you'll be prompted for**:

**Prompt 1: AWS Access Key ID**:
```
AWS Access Key ID [None]: [paste your ORACLE_ACCESS_KEY]

Example:
  2c4b1234567890abcdef1234567890abcdef12

Where from:
  ~/oracle-s3-credentials.txt file you created
```

**Prompt 2: AWS Secret Access Key**:
```
AWS Secret Access Key [None]: [paste your ORACLE_SECRET_KEY]

Example:
  XyZ/aBc123+dEf456gHi789JkL=

Where from:
  ~/oracle-s3-credentials.txt file you created
```

**Prompt 3: Default region**:
```
Default region name [None]: us-ashburn-1

⚠️ IMPORTANT: Use Oracle region, not AWS region!
```

**Prompt 4: Default output format**:
```
Default output format [None]: json

Can also use: table, text
Recommended: json (easiest to read)
```

**What AWS CLI saves**:
```
Configuration saved to:
  ~/.aws/credentials (access keys)
  ~/.aws/config (region, format)
```

---

### Step 10.2: Test Oracle Object Storage Connection

**List buckets**:
```bash
aws s3 ls \
    --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com

# Expected output:
# 2024-01-19 10:30:45 lakehouse-prod
```

**Test upload**:
```bash
# Create test file
echo "Hello from local machine!" > test.txt

# Upload to Oracle
aws s3 cp test.txt s3://lakehouse-prod/ \
    --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com

# Expected output:
# upload: ./test.txt to s3://lakehouse-prod/test.txt
```

**Verify upload**:
```bash
aws s3 ls s3://lakehouse-prod/ \
    --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com

# Should show:
# 2024-01-19 11:45:12    28 test.txt
```

**✅ Success indicators**:
```
✓ Bucket listed without errors
✓ File uploaded successfully
✓ File visible in listing
```

---

## ✅ Part 3 Checkpoint

**What you've accomplished**:
```
✓ Supabase account created
✓ PostgreSQL database configured (500 MB free)
✓ Database connection tested
✓ Firebolt dataset downloaded (52 GB)
✓ All files decompressed
✓ AWS CLI configured for Oracle Storage
✓ Oracle S3 connection tested
```

**What you have now**:
```
Databases:
  - Supabase PostgreSQL (for Nessie metadata)
  - Connection string saved

Data:
  - transactions.csv (412M records, 52 GB)
  - users.csv (2.5M records, 1.2 GB)
  - products.csv (125k records, 200 MB)
  - sessions.csv (85M records, 15 GB)

Storage:
  - Oracle bucket: lakehouse-prod
  - S3 access configured
```

**Files created**:
```
~/supabase-credentials.txt
~/oracle-s3-credentials.txt
~/Documents/Version_Control_For_Databases/data/firebolt-raw/*.csv
```

**Total cost so far**: Still **$0.00** ✅

**What's next in Part 4**:
- Upload data to Oracle Storage
- Deploy Docker containers on VMs
- Configure processing scripts
- Run production pipeline

---

**Continue to DETAILED_GUIDE_PART4.md for final deployment!**
