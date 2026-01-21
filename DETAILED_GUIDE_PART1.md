# Ultra-Detailed Production Guide - Part 1 of 4

**Oracle Cloud Account Setup & VM Provisioning**

---

## 🎯 What You'll Accomplish in Part 1

By the end of this guide, you will have:
- ✅ Oracle Cloud account (free tier)
- ✅ Virtual Cloud Network (VCN) configured
- ✅ 2 Virtual Machines running (24 GB RAM total)
- ✅ Object Storage bucket created
- ✅ S3-compatible API keys generated

**Time Required**: 2-3 hours  
**Cost**: $0 (completely free)

---

## 📋 Before You Start

### What You Need:
1. **Email address** (Gmail works best)
2. **Phone number** (for SMS verification)
3. **Credit card** (for verification only - NO charges will be made)
4. **Computer** with internet browser
5. **2-3 hours** of uninterrupted time

### Important Notes:
- ⚠️ Credit card is ONLY for verification - Oracle free tier never charges
- ✅ Always Free resources never expire (as long as you use them)
- 📝 Keep notepad ready to save important information
- 🔐 Use strong passwords (save them in password manager)

---

## Step 1: Create Oracle Cloud Account

### Step 1.1: Navigate to Oracle Cloud Free Tier Page

**What to do**:
```bash
# Open this URL in your browser:
https://www.oracle.com/cloud/free/
```

**What you'll see**:
- Page title: "Oracle Cloud Free Tier"
- Big blue button saying "Start for free"
- Text explaining $300 free credits + Always Free services

**Screenshot description**:
You should see a webpage with:
- Oracle logo in top left
- Navigation menu
- Large heading "Oracle Cloud Free Tier"
- Blue "Start for free" button (center-right)

**Action**: Click the blue **"Start for free"** button

---

### Step 1.2: Fill Out Registration Form

**What you'll see**:
A form titled "Create your Oracle Cloud Free Tier account"

**Form fields to fill** (one by one):

**Field 1: Country/Territory**
```
What to select: Your country
Example: United States
Note: This cannot be changed later, choose carefully
```

**Field 2: Cloud Account Name**
```
What to enter: lakehouse-prod
Rules: 
  - 1-30 characters
  - Letters, numbers, hyphens only
  - Must be globally unique
  
If "lakehouse-prod" is taken, try:
  - lakehouse-prod-2024
  - lakehouse-yourname
  - lakehouse-project-01

What you'll see: Green checkmark if available
                Red X if already taken
```

**Field 3: Home Region**
```
What to select: US East (Ashburn)

Why this region?
  - Good performance for most locations
  - Has all features
  - Supabase nearby (faster connections)

Other options if needed:
  - US West (Phoenix)
  - Europe (Frankfurt) - for Europe-based teams
  - Asia Pacific (Singapore) - for Asia-based teams

⚠️ IMPORTANT: Cannot change region after signup!
```

**Field 4: Email**
```
What to enter: your-email@gmail.com
Rules: 
  - Must be valid email
  - You'll receive verification email
  - Save this - you'll need it to login!
```

**What you'll see after filling**:
- Form validates each field as you type
- Green checkmarks appear for valid entries
- "Next" button becomes active (blue)

**Action**: Click **"Next"** button

---

### Step 1.3: Enter Personal Information

**What you'll see**:
New form page with personal details

**Fields to fill**:

**First Name**: Your first name
**Last Name**: Your last name
**Phone Number**: Your mobile number with country code
```
Format: +1-555-123-4567
Why needed: SMS verification code
```

**Job Title**: Data Engineer (or Student, or Analyst)
**Company Name**: Your university/company (or "Personal Project")

**What you'll see**:
- All fields have red asterisk (*) = required
- Phone number auto-formats as you type

**Action**: Click **"Next"** button

---

### Step 1.4: Payment Verification

**What you'll see**:
Page titled "Payment Verification"

**⚠️ CRITICAL UNDERSTANDING**:
```
Why credit card is needed:
  ✓ Prevents abuse/bots
  ✓ Verifies you're real person
  ✓ Required by Oracle policy

What will be charged:
  ✗ $0.00 - NOTHING!
  ✓ Small temporary hold (~$1) that's refunded
  ✓ No charges for free tier usage
```

**Credit Card Fields**:
```
Card Number: Your credit/debit card
Expiry Date: MM/YY
CVV: 3-digit code on back
Billing Address: Must match card statement
```

**What you'll see**:
- Card type detected automatically (Visa/Mastercard)
- Address auto-complete dropdown

**After entering card**:
- Green checkmark appears
- "Finish" button becomes active

**Action**: Click **"Finish"** button

---

### Step 1.5: Email Verification

**What happens next**:
1. Page shows "Creating your account..."
2. Wait 10-30 seconds
3. New page: "Verify your email"

**Check your email inbox**:
```
From: Oracle Cloud <noreply@oracle.com>
Subject: Verify your Oracle Cloud account
```

**Email will contain**:
- Welcome message
- Blue button: "Verify email"
- Or a verification link

**Action**: Click the **"Verify email"** button in the email

**What you'll see in browser**:
- Page confirming email verified
- Redirect to Oracle Cloud login page

---

### Step 1.6: Set Your Password

**What you'll see**:
"Create your password" form

**Password Requirements**:
```
Must have:
  ✓ At least 12 characters (recommended: 16+)
  ✓ Uppercase letter (A-Z)
  ✓ Lowercase letter (a-z)
  ✓ Number (0-9)
  ✓ Special character (!@#$%^&*)

Example good password:
  Lakehouse2024!Prod#Secure
  CloudData$Project2024!
```

**Fields**:
```
Password: [enter your password]
Confirm Password: [enter same password]
```

**💡 IMPORTANT**: Save this password immediately!
```
Where to save:
  ✓ Password manager (1Password, LastPass, Bitwarden)
  ✓ Secure notes app
  ✗ Don't just remember it - you WILL forget!
```

**What you'll see**:
- Password strength indicator (weak/medium/strong)
- Requirements checklist (turns green as met)

**Action**: Click **"Create Account"** button

---

### Step 1.7: Phone Verification

**What you'll see**:
"Verify your phone" page

**Steps**:
1. Your phone number is shown
2. Click **"Text me"** button
3. Wait 10-60 seconds
4. Receive SMS with 6-digit code

**Example SMS**:
```
Oracle Cloud verification code: 123456
Do not share this code with anyone.
```

**What to do**:
- Enter the 6-digit code in the boxes
- Code valid for 10 minutes

**If you don't receive SMS**:
- Click "Resend code" (wait 1 minute first)
- Try "Call me" option instead
- Check phone has signal

**Action**: Enter verification code

---

### Step 1.8: Welcome to Oracle Cloud!

**What you'll see**:
Oracle Cloud Console dashboard with:
- Welcome message
- Quick start tutorials
- Resource summary (all zeros initially)

**Page elements**:
```
Top Left: 
  - ☰ Hamburger menu (main navigation)
  - Oracle Cloud logo
  
Top Right:
  - Notifications bell
  - Profile icon
  - Region selector (shows "US East (Ashburn)")

Center:
  - "Welcome to Oracle Cloud" banner
  - Quick action cards
  - "Learn more" links
```

**✅ Congratulations!** Oracle Cloud account created!

**What to save in your notes**:
```
Oracle Cloud Account Info:
  Account Name: lakehouse-prod
  Username: your-email@gmail.com
  Password: [your password]
  Home Region: US East (Ashburn)
  Login URL: https://cloud.oracle.com/
```

---

## Step 2: Create Virtual Cloud Network (VCN)

### Step 2.1: Navigate to Networking

**What to do**:
1. Click the **☰** (hamburger menu) in top left
2. Hover over **"Networking"**
3. Click **"Virtual Cloud Networks"**

**What you'll see as you navigate**:
```
After clicking ☰:
  - Menu slides out from left
  - Categories listed alphabetically
  - "Networking" is in middle section

After hovering "Networking":
  - Submenu appears to the right
  - Options:
    * Virtual Cloud Networks ← click this
    * Load Balancers
    * DNS Management
    * etc.
```

**Page you'll land on**:
- Title: "Virtual Cloud Networks"
- Empty list (no VCNs yet)
- Blue button: "Start VCN Wizard"

---

### Step 2.2: Start VCN Wizard

**What you'll see**:
List of VCNs page with:
- Compartment selector (left side)
- "Start VCN Wizard" button (blue, prominent)
- Empty table (no VCNs created yet)

**Compartment selector**:
```
What it shows: (root) [default]
What this means: Root compartment (like root folder)
Leave it as is: Don't change this
```

**Action**: Click **"Start VCN Wizard"** button

---

### Step 2.3: Choose VCN Configuration

**What you'll see**:
Modal popup: "Start VCN Wizard"

**Two options shown**:

**Option 1: Create VCN with Internet Connectivity** ← Choose this!
```
Description: 
  "VCN with a public subnet and an internet gateway."
  
Features:
  ✓ Public subnet (for VMs with public IPs)
  ✓ Internet gateway (for internet access)
  ✓ Security lists pre-configured
  
This is what you need!
```

**Option 2: Create VCN Only**
```
Description:
  "VCN without subnets or gateways."
  
Why not this:
  ✗ More manual configuration needed
  ✗ Have to create subnets yourself
  ✗ More complex for beginners
```

**What to do**:
1. **Select** "Create VCN with Internet Connectivity" (radio button)
2. Click **"Start VCN Wizard"** button at bottom

**What you'll see**:
- Radio button filled for option 1
- Blue "Start VCN Wizard" button becomes active

---

### Step 2.4: Configure VCN Details

**What you'll see**:
Form titled "Configuration" with multiple sections

**Section 1: Basic Information**

**VCN Name**:
```
What to enter: lakehouse-vcn
Why: Descriptive name for your network
Rules: Letters, numbers, hyphens allowed
```

**Compartment**:
```
What it shows: (root)
What to do: Leave as is (don't change)
Why: Root compartment is fine for project
```

**Section 2: VCN CIDR Blocks**

**VCN CIDR Block**:
```
What to enter: 10.0.0.0/16
What this means:
  - 10.0.0.0 = Network address
  - /16 = Subnet mask (65,536 IPs available)
  - Range: 10.0.0.1 to 10.0.255.254

Why this range:
  ✓ Private IP range (not on internet)
  ✓ Standard practice
  ✓ Enough IPs for our project
  
⚠️ Do NOT change this unless you know networking!
```

**Section 3: Subnets**

**Public Subnet CIDR Block**:
```
What to enter: 10.0.0.0/24
What this means:
  - Subnet of the VCN above
  - /24 = 256 IPs (enough for ~250 VMs)
  - Range: 10.0.0.1 to 10.0.0.254

Why public:
  ✓ Our VMs need internet access
  ✓ We'll access them via SSH
  ✓ Dashboards need public access
```

**Private Subnet CIDR Block**:
```
What to enter: 10.0.1.0/24
What this means:
  - Another subnet for private resources
  - We won't use this for now
  - Can ignore it

Leave as default: 10.0.1.0/24
```

**Section 4: DNS Resolution**

**Use DNS Hostnames in this VCN**:
```
What you'll see: Checkbox (checked by default)
What to do: LEAVE IT CHECKED ✓
Why: Allows VMs to have DNS names
```

**What the form looks like overall**:
```
┌─────────────────────────────────────┐
│ Configuration                        │
├─────────────────────────────────────┤
│ Basic Information                    │
│   VCN Name: lakehouse-vcn           │
│   Compartment: (root)               │
│                                      │
│ VCN CIDR Blocks                     │
│   VCN CIDR Block: 10.0.0.0/16      │
│                                      │
│ Subnets                             │
│   Public Subnet: 10.0.0.0/24       │
│   Private Subnet: 10.0.1.0/24      │
│                                      │
│ DNS                                 │
│   ✓ Use DNS hostnames              │
│                                      │
│ [Previous]  [Next]                  │
└─────────────────────────────────────┘
```

**Action**: Click **"Next"** button

---

### Step 2.5: Review VCN Configuration

**What you'll see**:
"Review and Create" page showing summary

**Review checklist**:
```
✓ VCN Name: lakehouse-vcn
✓ VCN CIDR: 10.0.0.0/16
✓ Public Subnet: 10.0.0.0/24
✓ DNS: Enabled

Components to be created:
  ✓ Virtual Cloud Network (VCN)
  ✓ Public Subnet
  ✓ Private Subnet
  ✓ Internet Gateway
  ✓ NAT Gateway
  ✓ Service Gateway
  ✓ Route Tables (2)
  ✓ Security Lists (2)
```

**What to do**:
- Review all settings
- If everything looks correct, continue
- If something's wrong, click "Previous"

**Action**: Click **"Create"** button

---

### Step 2.6: VCN Creation Progress

**What you'll see**:
Progress page with:
- "Creating Virtual Cloud Network" title
- List of components with status icons
- Progress spinner

**Creation sequence** (happens automatically):
```
1. ⏳ Creating VCN...                    [Spinner]
2. ⏳ Creating Internet Gateway...       [Spinner]  
3. ⏳ Creating Subnets...                [Spinner]
4. ⏳ Creating Route Tables...           [Spinner]
5. ⏳ Creating Security Lists...         [Spinner]

After 30-60 seconds:

1. ✅ VCN created
2. ✅ Internet Gateway created
3. ✅ Subnets created
4. ✅ Route Tables created
5. ✅ Security Lists created

Final message:
  "Virtual Cloud Network created successfully!"
```

**Action**: Click **"View Virtual Cloud Network"** button

---

### Step 2.7: VCN Details Page

**What you'll see**:
VCN details page for "lakehouse-vcn"

**Page sections**:

**Top Section - VCN Information**:
```
Name: lakehouse-vcn
CIDR Blocks: 10.0.0.0/16
DNS Domain Name: lakehousevcn.oraclevcn.com
Created: [timestamp]
```

**Resources (left sidebar)**:
```
- Subnets (2)
- Route Tables (2)
- Security Lists (2)
- Internet Gateways (1)
- NAT Gateways (1)
- Service Gateways (1)
```

**✅ Verification**:
```
What to check:
  ✓ Name shows "lakehouse-vcn"
  ✓ State shows "Available" (green)
  ✓ CIDR shows 10.0.0.0/16
```

**Save to your notes**:
```
VCN Information:
  Name: lakehouse-vcn
  CIDR: 10.0.0.0/16
  Region: US East (Ashburn)
  Public Subnet: 10.0.0.0/24
```

---

## Step 3: Configure Security Rules

### Step 3.1: Navigate to Security Lists

**Where you are**: VCN details page

**What to do**:
1. Look at left sidebar under "Resources"
2. Click **"Security Lists"**

**What you'll see**:
Table showing:
```
Name                                  Compartment
Default Security List for lakehouse  (root)
Security List for Private Subnet     (root)
```

**Which one to click**:
Click **"Default Security List for lakehouse-vcn"**

(This is for the public subnet - where our VMs will be)

---

### Step 3.2: View Current Ingress Rules

**What you'll see**:
Security List details page

**Sections shown**:
```
1. Security List Information (top)
2. Ingress Rules (first tab - already selected)
3. Egress Rules (second tab)
```

**Current Ingress Rules** (default):
```
Rule 1:
  Source: 0.0.0.0/0
  Protocol: ICMP
  Description: Allow ping

Rule 2:
  Source: 10.0.0.0/16
  Protocol: All
  Description: Allow all within VCN
```

**What this means**:
- Only ping from internet allowed
- SSH (port 22) NOT YET allowed ← We need to add this!

---

### Step 3.3: Add SSH Rule (Port 22)

**What to do**:
Click blue **"Add Ingress Rules"** button (top of table)

**What you'll see**:
Modal popup: "Add Ingress Rules"

**Form fields to fill**:

**Stateless**:
```
What it shows: Checkbox (unchecked)
What to do: Leave UNCHECKED
Why: Stateful = better (tracks connections)
```

**Source Type**:
```
What it shows: Dropdown, default "CIDR"
What to do: Leave as "CIDR"
```

**Source CIDR**:
```
What to enter: 0.0.0.0/0
What this means: Allow from ANY IP address
Why: So you can SSH from anywhere
Security: We'll use SSH keys (secure)
```

**IP Protocol**:
```
What it shows: Dropdown, default "All Protocols"
What to select: TCP
Why: SSH uses TCP protocol
```

**After selecting TCP, new fields appear**:

**Source Port Range**:
```
What to enter: Leave BLANK
Why: Not needed for inbound SSH
```

**Destination Port Range**:
```
What to enter: 22
What this is: SSH port
Why: SSH daemon listens on port 22
```

**Description** (optional):
```
What to enter: SSH access
Why: Good practice to document rules
```

**What the form looks like**:
```
┌──────────────────────────────────────┐
│ Add Ingress Rules                    │
├──────────────────────────────────────┤
│ Stateless: ☐                         │
│ Source Type: CIDR                    │
│ Source CIDR: 0.0.0.0/0              │
│ IP Protocol: TCP                     │
│ Source Port Range: [blank]           │
│ Destination Port: 22                 │
│ Description: SSH access              │
│                                       │
│ [Cancel]  [Add Ingress Rules]       │
└──────────────────────────────────────┘
```

**Action**: Click **"Add Ingress Rules"** button

**What happens**:
- Modal closes
- New rule appears in table
- Status: "Available" (green)

---

### Step 3.4: Add Airflow Rule (Port 8080)

**Repeat the process for Airflow**:

Click **"Add Ingress Rules"** again

**Fill form**:
```
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port: 8080
Description: Airflow Web UI
```

Click **"Add Ingress Rules"**

---

### Step 3.5: Add Remaining Rules

**Add these rules one by one** (same process):

**Rule 3: Nessie API**
```
Source CIDR: 0.0.0.0/0
Protocol: TCP
Port: 19120
Description: Nessie API
```

**Rule 4: Spark UI**
```
Source CIDR: 0.0.0.0/0
Protocol: TCP
Port: 8081
Description: Spark Master UI
```

**Rule 5: Jupyter Notebook**
```
Source CIDR: 0.0.0.0/0
Protocol: TCP
Port: 8888
Description: Jupyter Notebook
```

---

### Step 3.6: Verify All Rules Added

**What you should see in the table**:
```
Ingress Rules (7 total):

Source         Protocol  Ports   Description
─────────────────────────────────────────────
0.0.0.0/0      ICMP      -       (default)
10.0.0.0/16    All       -       (default)
0.0.0.0/0      TCP       22      SSH access
0.0.0.0/0      TCP       8080    Airflow Web UI
0.0.0.0/0      TCP       19120   Nessie API
0.0.0.0/0      TCP       8081    Spark Master UI
0.0.0.0/0      TCP       8888    Jupyter Notebook
```

**✅ Verification checklist**:
```
✓ All 5 new rules shown
✓ All have source 0.0.0.0/0
✓ All show "Available" status
✓ Correct ports: 22, 8080, 19120, 8081, 8888
```

**Save to notes**:
```
Ports Opened:
  22 - SSH
  8080 - Airflow
  19120 - Nessie
  8081 - Spark UI
  8888 - Jupyter
```

---

## ✅ Part 1 Checkpoint

**You've completed the network setup!**

**What you have now**:
- ✅ Oracle Cloud account
- ✅ Virtual Cloud Network (VCN)
- ✅ Security rules configured

**What's next in Part 2**:
- Create VM1 (Airflow + Nessie)
- Create VM2 (Spark cluster)
- Object Storage setup
- S3 API keys

**Take a break!** Save your progress notes before continuing.

---

**Continue to DETAILED_GUIDE_PART2.md when ready!**
