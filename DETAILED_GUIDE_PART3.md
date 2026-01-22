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
Default region name [None]: ap-mumbai-1

⚠️ IMPORTANT: Use YOUR Oracle region!
For Mumbai: ap-mumbai-1
For Ashburn: us-ashburn-1
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
# For Mumbai region:
aws s3 ls \
    --endpoint-url https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com

# Expected output:
# 2026-01-22 13:15:45 lakehouse-prod
```

**Test upload**:

**⚠️ NOTE**: AWS CLI `s3 cp` has a compatibility issue with Oracle S3. Use curl instead:

```bash
# Create test file
echo "Hello from local machine!" > test.txt

# Upload using curl (works reliably with Oracle)
curl -X PUT \
    -T test.txt \
    -H "Content-Type: text/plain" \
    --aws-sigv4 "aws:amz:ap-mumbai-1:s3" \
    --user "[YOUR_ACCESS_KEY]:[YOUR_SECRET_KEY]" \
    "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com/lakehouse-prod/test.txt"

# No output = success!
```

**Verify upload**:
```bash
aws s3 ls s3://lakehouse-prod/ \
    --endpoint-url https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com

# Should show:
# 2026-01-22 17:10:00    26 test.txt
```

**✅ Success indicators**:
```
✓ Bucket listed without errors
✓ File uploaded successfully (curl returns no error)
✓ File visible in listing
```

---

## ✅ Part 3 Checkpoint

**What you've accomplished**:
```
✓ Supabase account created
✓ PostgreSQL database configured (500 MB free)
✓ Database connection tested
✓ Firebolt ecommerce dataset downloaded (~5 GB parquet)
✓ AWS CLI configured for Oracle Storage
```

**What you have now**:
```
Databases:
  - Supabase PostgreSQL (for Nessie metadata)
  - Host: db.vxpwataohydyzegvbxws.supabase.co
  - Connection string saved in SUPABASE_INFO.md

Data:
  - ~1000 parquet files (~5 GB compressed)
  - ~400 million transaction records
  - Ready for Spark processing (no decompression needed)

Storage:
  - Oracle bucket: lakehouse-prod
  - Namespace: bmcfe6z38foz
  - Region: ap-mumbai-1
  - S3-compatible endpoint configured
```

**Files created**:
```
~/supabase-credentials.txt (or SUPABASE_INFO.md)
~/oracle-s3-credentials.txt
~/Documents/Version_Control_For_Databases/data/firebolt-raw/*.parquet
```

**Total cost so far**: Still **$0.00** ✅

---

## Step 11: Deploy Docker on VM1

### Step 11.1: SSH to VM1

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207
```

### Step 11.2: Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y
# Press Tab + Enter if prompted about services

# Install Docker
sudo apt install -y docker.io

# Enable and start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker ubuntu

# Install Docker Compose standalone
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.3/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker-compose --version
# Should show: Docker Compose version v2.23.3
```

**Logout and login again** to apply docker group:
```bash
exit
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207
```

### Step 11.3: Clone Repository and Setup

```bash
cd /home/ubuntu
git clone https://github.com/Saadmomin2903/Version_Control_For_Databases.git
cd Version_Control_For_Databases
```

### Step 11.4: Install Local PostgreSQL

**⚠️ IMPORTANT**: Supabase only provides IPv6 addresses, and Oracle VMs don't support IPv6.
The solution is to install PostgreSQL locally on the VM.

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start and enable
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database for Nessie
sudo -u postgres psql -c "CREATE DATABASE nessie;"
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'nessie123';"
```

### Step 11.5: Configure PostgreSQL for Docker

Docker containers can't connect to localhost - they need to use the Docker gateway IP.

```bash
# Allow Docker networks to connect
sudo bash -c 'echo "host    all    all    172.18.0.0/16    md5" >> /etc/postgresql/14/main/pg_hba.conf'
sudo bash -c 'echo "host    all    all    172.17.0.0/16    md5" >> /etc/postgresql/14/main/pg_hba.conf'
sudo bash -c 'echo "host    all    all    10.0.0.0/24    md5" >> /etc/postgresql/14/main/pg_hba.conf'

# Configure PostgreSQL to listen on all interfaces
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/14/main/postgresql.conf

# Open firewall
sudo iptables -I INPUT -p tcp --dport 5432 -j ACCEPT

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Step 11.6: Create .env File

```bash
cd /home/ubuntu/Version_Control_For_Databases

# Create .env
cat > .env << 'EOF'
# Supabase (using local PostgreSQL instead)
SUPABASE_HOST=localhost
SUPABASE_PASSWORD=nessie123
SUPABASE_JDBC_URL=jdbc:postgresql://172.18.0.1:5432/nessie?user=postgres&password=nessie123

# Oracle
ORACLE_NAMESPACE=bmcfe6z38foz
ORACLE_ACCESS_KEY=962c9f862226831e4edea90cfcfafb8a8dffcd51
ORACLE_SECRET_KEY=sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=
ORACLE_ENDPOINT=https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com
ORACLE_REGION=ap-mumbai-1
WAREHOUSE=s3a://lakehouse-prod/warehouse

# Nessie
NESSIE_URI=http://nessie:19120/api/v1
EOF
```

### Step 11.7: Start Docker Containers

```bash
docker-compose -f docker-compose-production.yml up -d
```

**Wait 15 seconds, then verify**:
```bash
sleep 15
docker ps

# Should show:
# lakehouse-nessie - healthy
# lakehouse-spark - running
```

### Step 11.8: Verify Nessie API

```bash
curl http://localhost:19120/api/v2/config
```

**Expected output**:
```json
{
  "defaultBranch" : "main",
  "minSupportedApiVersion" : 1,
  "maxSupportedApiVersion" : 2,
  "actualApiVersion" : 2,
  "specVersion" : "2.1.0"
}
```

---

### Step 11.9: Access Web UIs

**Get Jupyter Token** (run on VM1):
```bash
docker logs lakehouse-spark 2>&1 | grep token
```

**Access Jupyter Notebook**:
```
http://140.238.224.207:8888/?token=[YOUR-TOKEN]
```

Or paste the token in the login page.

**Access Spark UI**:
```
http://140.238.224.207:8081
```

**⚠️ If connection refused**, open ports in Oracle Cloud:

1. Oracle Console → Networking → Virtual Cloud Networks
2. Click your VCN → Security Lists → Default Security List
3. Add Ingress Rules:

| Source CIDR | Protocol | Port |
|-------------|----------|------|
| 0.0.0.0/0 | TCP | 8081 |
| 0.0.0.0/0 | TCP | 8888 |
| 0.0.0.0/0 | TCP | 19120 |

**Test Nessie API from browser**:
```
http://140.238.224.207:19120/api/v2/config
```

---

## ✅ Part 3 Complete!

**What you've accomplished**:
```
✓ Supabase account created
✓ Firebolt dataset downloaded (~5 GB parquet)
✓ AWS CLI configured for Oracle Storage
✓ Docker installed on VM1
✓ PostgreSQL installed on VM1 (for Nessie catalog)
✓ Nessie + Spark containers running
```

**Running Services on VM1**:
| Service | Port | Status |
|---------|------|--------|
| Nessie API | 19120 | ✅ Running |
| Spark Master | 7077 | ✅ Running |
| Spark UI | 8081 | ✅ Running |
| Jupyter | 8888 | ✅ Running |
| PostgreSQL | 5432 | ✅ Running |

**Total cost so far**: Still **$0.00** ✅

---

## Next: Part 4 - Complete Pipeline

**Continue to DETAILED_GUIDE_PART4.md for**:
1. ⭐ Setup VM2 with Spark workers
2. ⭐ Upload parquet data to Oracle Storage
3. ⭐ Run the Bronze → Silver → Gold pipeline
4. ⭐ Query data with Nessie branches
