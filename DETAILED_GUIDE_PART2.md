# Ultra-Detailed Production Guide - Part 2 of 4

**VM Provisioning & Storage Setup**

---

## 🎯 What You'll Accomplish in Part 2

By the end of this guide, you will have:
- ✅ VM1 created and accessible (Airflow + Nessie)
- ✅ VM2 created and accessible (Spark cluster)
- ✅ Object Storage bucket configured
- ✅ S3-compatible API keys generated
- ✅ All SSH keys downloaded and tested

**Time Required**: 1.5-2 hours  
**Prerequisites**: Part 1 completed (VCN ready)

---

## Step 4: Create VM1 (Airflow + Nessie Server)

### Step 4.1: Navigate to Compute Instances

**What to do**:
1. Click **☰** (hamburger menu) in top left
2. Hover over **"Compute"**
3. Click **"Instances"**

**What you'll see**:
```
After clicking ☰:
  - Full menu slides out
  - "Compute" is near the top

After hovering "Compute":
  - Submenu appears:
    * Instances ← click this
    * Custom Images
    * Dedicated VM Hosts
    * etc.
```

**Page you'll land on**:
- Title: "Instances"
- Empty list (no instances yet)
- Blue button: "Create Instance"
- Compartment selector showing "(root)"

---

### Step 4.2: Start Instance Creation

**What you'll see**:
Instances list page with:
```
Left side:
  Compartment: (root) [dropdown]
  State: All [dropdown]
  
Center:
  "No instances in this compartment"
  
Right side:
  [Create Instance] button (blue, prominent)
```

**Action**: Click **"Create Instance"** button

---

### Step 4.3: Configure Basic Instance Details

**What you'll see**:
Long form titled "Create Compute Instance"

**Section 1: Name and Compartment**

**Name**:
```
What to enter: airflow-nessie
Why this name:
  - Describes what runs on this VM
  - Airflow = orchestration
  - Nessie = data catalog
Rules:
  - Letters, numbers, hyphens, underscores
  - No spaces
```

**Create in compartment**:
```
What it shows: (root)
What to do: Leave as is
Why: Root compartment is fine
```

**What the section looks like**:
```
┌──────────────────────────────────────┐
│ Name and compartment                 │
├──────────────────────────────────────┤
│ Name: airflow-nessie                │
│ Create in compartment: (root)        │
└──────────────────────────────────────┘
```

---

### Step 4.4: Configure Placement

**Section 2: Placement**

**What you'll see**:
```
Availability domain: [dropdown]
Capacity type: On-demand capacity (default)
Fault domain: [dropdown]
```

**Availability Domain**:
```
What it shows: AD-1, AD-2, AD-3 (depends on region)
What to select: AD-1 (or any available)
What this means:
  - Physical data center location
  - Within your home region
  - AD-1 = Availability Domain 1
```

**Capacity Type**:
```
What it shows: 
  ○ On-demand capacity (selected by default)
  ○ Preemptible capacity
  
Leave as: On-demand capacity
Why: Guaranteed availability (not interrupted)
```

**Fault Domain**:
```
What to do: Leave as "Let Oracle choose"
Why: Oracle picks best location automatically
```

---

### Step 4.5: Choose Operating System Image

**Section 3: Image and Shape**

**What you'll see**:
Large section with image selection

**Current selection** (default):
```
Image: Oracle Linux 8
Change: Click "Change Image" button
```

**Action**: Click **"Change Image"** button

**What appears**:
Modal popup: "Browse All Images"

**Left sidebar shows categories**:
```
- Oracle Images
  * Oracle Linux
  * Windows Server
- Platform Images ← expand this
  * Canonical Ubuntu
  * CentOS
  * etc.
- My Images
- Partner Images
```

**What to do**:
1. Expand **"Platform Images"**
2. Click **"Canonical Ubuntu"**

**What you'll see**:
List of Ubuntu versions:
```
Name                              Architecture
──────────────────────────────────────────────────
Canonical Ubuntu 20.04            x86
Canonical Ubuntu 20.04 Minimal    x86
Canonical Ubuntu 22.04            x86 ← RECOMMENDED
Canonical Ubuntu 22.04 Minimal aarch64  ARM
Canonical Ubuntu 24.04            x86
```

**Which one to select**:
```
⚠️ IMPORTANT: ARM VMs often have NO CAPACITY in many regions!

Recommended: Canonical Ubuntu 22.04 (x86 version)

Why x86 instead of ARM:
  ✓ ARM (A1.Flex) often shows "Out of capacity" error
  ✓ x86 shapes (E5.Flex) are more available
  ✓ Same functionality, just different CPU architecture
  ✓ Mumbai region especially has ARM capacity issues

Why Ubuntu 22.04:
  ✓ LTS (Long Term Support = stable)
  ✓ Compatible with all our software
  ✓ Well-documented
  ✓ Docker works perfectly
```

**How to select**:
1. Click the **radio button** next to "Canonical Ubuntu 22.04" (x86 version)
2. **Do NOT select "aarch64" or "Minimal aarch64"** (those are ARM)
3. Click **"Select Image"** button at bottom

**What happens**:
- Modal closes
- Image section now shows: "Canonical Ubuntu 22.04"

---

### Step 4.6: Choose Shape (VM Size)

**Still in Section 3: Image and Shape**

**What you'll see**:
```
Current shape: VM.Standard.E2.1.Micro
Change: Click "Change Shape" button
```

**⚠️ IMPORTANT**:
The default shape is NOT what we want!

**Action**: Click **"Change Shape"** button

**What appears**:
Modal: "Browse All Shapes"

**Shape categories**:
```
Left sidebar:
  - AMD ← TRY THIS FIRST
  - Intel
  - Ampere (ARM - often NO capacity!)
  - Specialty and previous generation
```

**⚠️ IMPORTANT - ARM Capacity Issues**:
```
If you selected ARM image (aarch64) and try VM.Standard.A1.Flex,
you may get this error:

  "Out of capacity for shape VM.Standard.A1.Flex"

This is COMMON, especially in Mumbai region!
Solution: Use x86 image + AMD shape instead.
```

**RECOMMENDED: AMD Shape (Works Reliably)**:

1. Click **"AMD"** in the left sidebar
2. Select **VM.Standard.E5.Flex**

**What you'll see**:
```
Name                    OCPU        Memory      
──────────────────────────────────────────────────
VM.Standard.E5.Flex     1 (126 max) 12 (2098 max)
VM.Standard.E4.Flex     1 (114 max) 16 (1760 max)
```

**Configure E5.Flex**:
```
OCPU: 1 (you can try 2, but 1 works fine)
Memory: 12 GB

Note: E5.Flex uses free credits ($300 for 30 days)
      Not "Always Free" but you won't be charged
      if you stay within credits.
```

**What the config looks like**:
```
┌──────────────────────────────────────┐
│ VM.Standard.E5.Flex                  │
├──────────────────────────────────────┤
│ Number of OCPUs                      │
│ [●----------] 1                      │
│                                       │
│ Amount of memory (GB)                │
│ [======●----] 12                     │
│                                       │
│ Network bandwidth (Gbps): 1          │
└──────────────────────────────────────┘
```

**Alternative: Try ARM First (If Available)**:
```
If you want to try ARM (free forever):
1. Click "Ampere" in sidebar
2. Select VM.Standard.A1.Flex
3. Set 2 OCPU, 12 GB
4. If "Out of capacity" error → use E5.Flex above
```

**Action**: Click **"Select Shape"** button

**What happens**:
- Modal closes
- Shape section shows your selected shape

---

### Step 4.7: Configure Networking

**Section 4: Networking**

**Primary VNIC Information**

**Primary network**:
```
What you'll see:
  Virtual cloud network: [dropdown]
  Subnet: [dropdown]
```

**Virtual cloud network**:
```
What to select: lakehouse-vcn
How: Open dropdown, select "lakehouse-vcn"
Why: This is the VCN we created in Part 1
```

**Subnet**:
```
What to select: Public Subnet-lakehouse-vcn
How: Automatically selected after choosing VCN
Why: VMs need public subnet for internet access
```

**Public IPv4 address**:
```
What you'll see:
  ○ Do not assign a public IPv4 address
  ● Assign a public IPv4 address ← should be selected
  
Verify: Radio button for "Assign" is selected
Why: We need public IP to SSH and access dashboards
```

**Private IPv4 address**:
```
What you'll see:
  ● Automatically assign private IPv4 address ← selected
  ○ Manually assign private IPv4 address
  
Leave as: Automatically assign
Why: Oracle will pick available IP
```

**Hostname**:
```
What to enter: airflow-nessie
Why: Same as instance name (clearer organization)
Can leave blank: Will use instance name automatically
```

**What networking section looks like**:
```
┌──────────────────────────────────────┐
│ Networking                            │
├──────────────────────────────────────┤
│ VCN: lakehouse-vcn                   │
│ Subnet: Public Subnet-lakehouse-vcn  │
│ ● Assign public IPv4 address         │
│ ● Auto-assign private IPv4 address   │
│ Hostname: airflow-nessie             │
└──────────────────────────────────────┘
```

---

### Step 4.8: Add SSH Keys

**Section 5: Add SSH keys**

**⚠️ CRITICAL SECTION** - Don't skip this!

**What you'll see**:
```
Add SSH keys:
  ● Generate a key pair for me ← select this!
  ○ Upload public key files
  ○ Paste public keys
```

**Why "Generate a key pair"**:
```
✓ Oracle creates keys for you
✓ Download private key immediately
✓ No need to create keys manually
✓ Most beginner-friendly option
```

**Action**: Select **"Generate a key pair for me"**

**What appears**:
Two buttons appear below:
```
[Save Private Key]  [Save Public Key]
```

**IMPORTANT - Download BOTH keys**:

**Private Key**:
```
Button: "Save Private Key"
Action: Click it
What downloads: ssh-key-YYYY-MM-DD.key
Where to save: ~/.ssh/oracle-vm1.key
Why important: This lets you connect via SSH
Keep it secret: NEVER share this file!
```

**Public Key**:
```
Button: "Save Public Key"
Action: Click it
What downloads: ssh-key-YYYY-MM-DD.key.pub
What it's for: Backup/reference
Less critical: But save it anyway
```

**After downloading**:
```
Rename and move the files:

macOS/Linux Terminal:
cd ~/Downloads

# Move to .ssh folder (RECOMMENDED - avoids permission issues)
sudo cat ssh-key-*.key > ~/.ssh/oracle-vm1.key
cp ssh-key-*.key.pub ~/.ssh/oracle-vm1.key.pub
chmod 600 ~/.ssh/oracle-vm1.key

Verify:
ls -la ~/.ssh/oracle-vm1.key
# Should show: -rw------- (600 permissions)
```

**✅ Verification**:
You should see:
```
✓ Private key downloaded
✓ Public key downloaded
✓ Buttons show "Downloaded" label
```

---

### Step 4.9: Configure Boot Volume

**Section 6: Boot volume**

**What you'll see**:
```
Boot volume size (GB): 50 [default]

Options:
  ☐ Use in-transit encryption
  ☐ Specify a custom boot volume size
```

**Boot volume size**:
```
Default: 50 GB
Recommendation: Keep as 50 GB
Why sufficient:
  ✓ OS takes ~8 GB
  ✓ Docker takes ~10 GB
  ✓ Logs and temp files ~5 GB
  ✓ Plenty of room left (~25 GB)
```

**Encryption**:
```
Checkbox: "Use in-transit encryption"
Recommendation: Leave UNCHECKED
Why: Adds complexity, marginal benefit for our use
```

**Custom size**:
```
Checkbox: "Specify custom boot volume size"
What to do: Leave UNCHECKED
Why: 50 GB default is perfect
```

**Leave this section as default** - no changes needed!

---

### Step 4.10: Review and Create VM1

**Scroll down to bottom of form**

**What you'll see**:
```
[Show Advanced Options ▼]  (collapsed section - ignore for now)

Final review boxes:
  Management
  Capacity reservation
  etc.

At the very bottom:
  [Create] button (big, blue)
```

**Final checklist before creating**:
```
✓ Name: airflow-nessie
✓ Image: Ubuntu 22.04 ARM
✓ Shape: VM.Standard.A1.Flex (2 OCPU, 12 GB)
✓ VCN: lakehouse-vcn
✓ Subnet: Public subnet
✓ Public IP: Assigned
✓ SSH keys: Downloaded
✓ Boot volume: 50 GB
```

**Action**: Click **"Create"** button

---

### Step 4.11: VM1 Creation Progress

**What happens immediately**:
- Page redirects to Instance Details
- Status shows: "PROVISIONING" (orange icon)

**What you'll see**:
```
┌──────────────────────────────────────┐
│ airflow-nessie                       │
│ ⚠️  PROVISIONING                     │
├──────────────────────────────────────┤
│ Work requests                        │
│ ⏳ Launching instance...             │
│                                       │
│ Instance Information                 │
│ OCID: ocid1.instance.oc1...         │
│ Shape: VM.Standard.A1.Flex          │
│ Status: Provisioning                │
└──────────────────────────────────────┘
```

**Provisioning steps** (visible in Work Requests):
```
1. ⏳ Validating configuration...
2. ⏳ Allocating compute resources...
3. ⏳ Provisioning boot volume...
4. ⏳ Attaching network...
5. ⏳ Assigning IP addresses...
6. ⏳ Starting instance...

Time: Usually 1-2 minutes
```

**When complete**:
Status changes to: **"RUNNING"** (green icon ✅)

**What you'll see**:
```
┌──────────────────────────────────────┐
│ airflow-nessie                       │
│ ✅ RUNNING                           │
├──────────────────────────────────────┤
│ Instance Information                 │
│ Public IP: 129.146.XXX.XXX ← SAVE!  │
│ Private IP: 10.0.0.4                │
│ Shape: VM.Standard.A1.Flex          │
│ OCPU: 2, Memory: 12 GB              │
│ Image: Ubuntu 22.04                 │
└──────────────────────────────────────┘
```

---

### Step 4.12: Save VM1 Information

**⚠️ CRITICAL - Save this information immediately**:

```
Create a file: ~/oracle-vm1-info.txt

VM1 Information:
─────────────────────────────────────────
Name: airflow-nessie
Public IP: 129.146.XXX.XXX
Private IP: 10.0.0.4
SSH Key: ~/.ssh/oracle-vm1.key
Username: ubuntu
SSH Command: ssh -i ~/.ssh/oracle-vm1.key ubuntu@129.146.XXX.XXX

Services to run on this VM:
- Nessie (port 19120)
- Airflow Web UI (port 8080)
- Airflow Scheduler (backend)
─────────────────────────────────────────
```

---

### Step 4.13: Test SSH Connection to VM1

**Wait for instance to fully boot** (2-3 minutes after "RUNNING" status)

**From your local terminal**:

```bash
# Set correct permissions on key
chmod 600 ~/.ssh/oracle-vm1.key

# Test SSH connection
ssh -i ~/.ssh/oracle-vm1.key ubuntu@129.146.XXX.XXX
# Replace XXX.XXX with your actual public IP
```

**What you'll see**:

**First time**:
```
The authenticity of host '129.146.XXX.XXX' can't be established.
ED25519 key fingerprint is SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

**What to do**: Type **`yes`** and press Enter

**What you'll see next**:
```
Warning: Permanently added '129.146.XXX.XXX' (ED25519) to the list of known hosts.
Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-1045-oracle aarch64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

ubuntu@airflow-nessie:~$
```

**✅ Success indicators**:
```
✓ Connected without password (key worked!)
✓ Prompt shows: ubuntu@airflow-nessie
✓ No error messages
✓ You're in a shell prompt
```

**Test basic command**:
```bash
# Check you're on the right VM
hostname
# Should show: airflow-nessie

# Check resources
free -h
# Should show ~12 GB total memory

# Exit
exit
```

**If SSH fails**:
```
Common issues and FIXES:

1. "Permission denied (publickey)"
   Cause: Key file permissions wrong or owned by root
   
   Fix Step 1 - Copy key to .ssh folder:
   sudo cat ~/path/to/your/key > ~/.ssh/oracle-vm1.key
   
   Fix Step 2 - Set permissions:
   chmod 600 ~/.ssh/oracle-vm1.key
   
   Fix Step 3 - Retry SSH:
   ssh -i ~/.ssh/oracle-vm1.key ubuntu@[IP]

2. "Identity file not accessible: Permission denied"
   Cause: File is owned by root after using sudo
   
   Fix:
   sudo chown $USER ~/.ssh/oracle-vm1.key
   chmod 600 ~/.ssh/oracle-vm1.key

3. "Connection refused"
   Cause: VM still booting
   Fix: Wait 2-3 more minutes

4. "Connection timed out"
   Cause: Security list missing port 22
   Fix: Check VCN security list has port 22 ingress rule
```

---

## Step 5: Create VM2 (Spark Cluster)

**Now we repeat the process for VM2!**

### Step 5.1: Navigate Back to Instances

**If you're in VM1 details**: Click "Instances" in breadcrumb navigation (top)

**If you're elsewhere**: ☰ → Compute → Instances

---

### Step 5.2: Create Second Instance

**Action**: Click **"Create Instance"** button

**Fill form** (similar to VM1, with these differences):

**Name**:
```
What to enter: spark-cluster
Why different: This VM runs Spark, not Airflow
```

**All other settings IDENTICAL**:
```
Image: Ubuntu 22.04 ARM ✓
Shape: VM.Standard.A1.Flex (2 OCPU, 12 GB) ✓
VCN: lakehouse-vcn ✓
Subnet: Public Subnet ✓
Public IP: Assigned ✓
```

**SSH Keys**:
```
IMPORTANT: Generate NEW keys for VM2!
Don't reuse VM1 keys (security best practice)

Download and save as:
  Private: ~/.ssh/oracle-vm2.key
  Public: ~/.ssh/oracle-vm2.key.pub
```

**Action**: Click **"Create"**

---

### Step 5.3: Wait for VM2 Provisioning

**Same process as VM1**:
```
1. Status: PROVISIONING (orange)
2. Wait 1-2 minutes
3. Status: RUNNING (green)
4. Note down Public IP
```

---

### Step 5.4: Save VM2 Information

```
Create file: ~/oracle-vm2-info.txt

VM2 Information:
─────────────────────────────────────────
Name: spark-cluster
Public IP: 141.148.XXX.XXX
Private IP: 10.0.0.5
SSH Key: ~/.ssh/oracle-vm2.key
Username: ubuntu
SSH Command: ssh -i ~/.ssh/oracle-vm2.key ubuntu@141.148.XXX.XXX

Services to run on this VM:
- Spark Master (port 7077, 8081)
- Spark Worker (backend)
- Jupyter Notebook (port 8888)
─────────────────────────────────────────
```

---

### Step 5.5: Test SSH to VM2

```bash
chmod 600 ~/.ssh/oracle-vm2.key
ssh -i ~/.ssh/oracle-vm2.key ubuntu@141.148.XXX.XXX
# Should connect successfully

hostname
# Should show: spark-cluster

exit
```

---

## Step 6: Create Object Storage Bucket

### Step 6.1: Navigate to Object Storage

**What to do**:
1. Click **☰** (hamburger menu)
2. Hover over **"Storage"**
3. Click **"Buckets"**

**What you'll see**:
```
After hovering "Storage":
  - Object Storage & Archive Storage
    * Buckets ← click this
    * File Systems
```

**Page you'll land on**:
- Title: "Buckets"
- Compartment selector
- Empty list
- Blue "Create Bucket" button

---

### Step 6.2: Create Bucket

**Action**: Click **"Create Bucket"** button

**What appears**:
Modal popup: "Create Bucket"

**Form fields**:

**Bucket Name**:
```
What to enter: lakehouse-prod
Why: 
  - Descriptive name
  - Indicates production use
  - Easy to remember
Rules:
  - Lowercase letters, numbers, hyphens
  - Must be unique in your namespace
```

**Default Storage Tier**:
```
Options:
  ● Standard (selected)
  ○ Archive
  
Leave as: Standard
Why:
  ✓ Frequent access needed
  ✓ Fast retrieval
  ✓ Archive is for cold storage
```

**Object Versioning**:
```
Checkbox: ☐ Enable Object Versioning
Recommendation: CHECK IT ✓
Why:
  ✓ Keep history of file changes
  ✓ Recover from mistakes
  ✓ Good practice for production
```

**Encryption**:
```
Options:
  ● Encrypt using Oracle-managed keys (selected)
  ○ Encrypt using customer-managed keys
  
Leave as: Oracle-managed
Why: Simpler, free, secure enough
```

**What form looks like**:
```
┌──────────────────────────────────────┐
│ Create Bucket                        │
├──────────────────────────────────────┤
│ Bucket Name: lakehouse-prod          │
│ Compartment: (root)                  │
│ Storage Tier: ● Standard             │
│ ☑ Enable Object Versioning          │
│ Encryption: Oracle-managed keys      │
│                                       │
│ [Cancel]  [Create]                   │
└──────────────────────────────────────┘
```

**Action**: Click **"Create"** button

---

### Step 6.3: Verify Bucket Created

**What you'll see**:
Bucket list now shows:
```
Name              Created          Size
──────────────────────────────────────────
lakehouse-prod    Just now         0 B
```

**Click bucket name** to see details:

**What you'll see**:
```
┌──────────────────────────────────────┐
│ lakehouse-prod                       │
├──────────────────────────────────────┤
│ Namespace: xxxxxxxxxx                │
│ Region: US East (Ashburn)           │
│ Storage Tier: Standard              │
│ Versioning: Enabled                 │
│ Size: 0 bytes                       │
│ Objects: 0                          │
└──────────────────────────────────────┘
```

**⚠️ SAVE the Namespace**:
```
You'll see something like:
  Namespace: axfewqvxh74j

This is IMPORTANT - you need it for S3 access!

Add to your notes:
  ORACLE_NAMESPACE=axfewqvxh74j
```

---

## Step 7: Generate S3-Compatible API Keys

### Step 7.1: Navigate to User Settings

**What to do**:
1. Click **Profile Icon** (top right corner - shows your initial or avatar)
2. Click **"User Settings"** from dropdown

**What you'll see**:
```
Dropdown menu:
  Your Name
  ─────────────
  User Settings ← click this
  Help
  Sign Out
```

**Page you'll land on**:
User Details page showing:
- Your username
- Email
- OCID

---

### Step 7.2: Navigate to Customer Secret Keys

**What you'll see**:
Left sidebar with resources:
```
- Auth Tokens
- API Keys
- Customer Secret Keys ← click this
- OAuth 2.0 Client Credentials
- SMTP Credentials
```

**Action**: Click **"Customer Secret Keys"** in the left sidebar

**What you'll see**:
```
Customer Secret Keys
────────────────────────────
Empty table:
  "You don't have any customer secret keys"

[Generate Secret Key] button (blue)
```

---

###Step 7.3: Generate Secret Key

**Action**: Click **"Generate Secret Key"** button

**What appears**:
Modal popup: "Generate Secret Key"

**Form field**:
```
Name: [text input]
```

**What to enter**:
```
Name: lakehouse-s3-access
Why: Descriptive name for this key's purpose
```

**Action**: Click **"Generate Secret Key"** button

---

### Step 7.4: CRITICAL - Copy Secret Key IMMEDIATELY

**⚠️⚠️⚠️ EXTREME IMPORTANCE ⚠️⚠️⚠️**

**What you'll see**:
```
┌────────────────────────────────────────────────┐
│ Generated Secret Key                           │
├────────────────────────────────────────────────┤
│                                                 │
│ ⚠️  Save this secret key now. After you        │
│    close this dialog, you won't be able to     │
│    retrieve it again.                          │
│                                                 │
│ Access Key:                                    │
│ 2c4b1234567890abcdef1234567890abcdef12       │
│                                                 │
│ Secret Key:                                    │
│ XyZ/aBc123+dEf456gHi789JkL=                   │
│ [Copy]                                         │
│                                                 │
│ [Close]                                        │
└────────────────────────────────────────────────┘
```

**WHAT TO DO IMMEDIATELY**:

**Step 1**: Click **[Copy]** button next to Secret Key

**Step 2**: Open a text file and paste:
```bash
# Create credentials file
cat > ~/oracle-s3-credentials.txt << 'EOF'
ORACLE_ACCESS_KEY=2c4b1234567890abcdef1234567890abcdef12
ORACLE_SECRET_KEY=XyZ/aBc123+dEf456gHi789JkL=
ORACLE_NAMESPACE=axfewqvxh74j
ORACLE_REGION=us-ashburn-1
ORACLE_ENDPOINT=https://objectstorage.us-ashburn-1.oraclecloud.com
EOF

chmod 600 ~/oracle-s3-credentials.txt
```

**Step 3**: Verify file created:
```bash
cat ~/oracle-s3-credentials.txt
# Should display your credentials
```

**Step 4**: ONLY AFTER saving, click **[Close]**

**⚠️ Warning**: After closing, you can NEVER see the secret key again!

---

## ✅ Part 2 Checkpoint

**What you've accomplished**:
```
✓ VM1 (airflow-nessie) created and accessible
✓ VM2 (spark-cluster) created and accessible
✓ Both VMs tested via SSH
✓ Object Storage bucket created
✓ S3 API keys generated and saved
```

**What you have saved**:
```
Files created:
  ~/.ssh/oracle-vm1.key (private key for VM1)
  ~/.ssh/oracle-vm2.key (private key for VM2)
  ~/oracle-vm1-info.txt (VM1 details)
  ~/oracle-vm2-info.txt (VM2 details)
  ~/oracle-s3-credentials.txt (S3 access keys)
```

**Summary of resources**:
```
Compute:
  - 2 VMs × 2 OCPU × 12 GB RAM = 4 OCPU, 24 GB total ✓
  
Storage:
  - 1 bucket: lakehouse-prod (20 GB limit)
  
Networking:
  - VCN: lakehouse-vcn
  - 2 VMs with public IPs
  - Security rules configured
  
Access:
  - SSH keys for both VMs
  - S3 API keys
```

**Total cost so far**: **$0.00** ✅

**What's next in Part 3**:
- Supabase PostgreSQL setup
- Firebolt dataset download
- Configure AWS CLI for data upload

---

**Continue to DETAILED_GUIDE_PART3.md when ready!**
