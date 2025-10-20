# VM Recommendations for CAAA Scraper

## Recommended VM Specifications

### Minimum (MVP - Single User)
- **vCPU:** 2 cores
- **RAM:** 2 GB
- **Storage:** 20 GB SSD
- **OS:** Ubuntu 22.04 LTS (or 20.04 LTS)
- **Bandwidth:** 1 TB/month (more than enough)

### Recommended (Production - Stable Performance)
- **vCPU:** 2 cores
- **RAM:** 4 GB
- **Storage:** 40 GB SSD
- **OS:** Ubuntu 22.04 LTS
- **Bandwidth:** 2 TB/month

---

## Provider Comparison (2025 Pricing)

### 1. DigitalOcean Droplet ⭐ RECOMMENDED
**Plan:** Basic Droplet - 2 vCPU, 2 GB RAM
- **Cost:** $18/month
- **Storage:** 50 GB SSD
- **Transfer:** 2 TB
- **Pros:**
  - Simple, clean UI
  - Excellent documentation
  - Automated backups: +$3.60/month (20% of droplet cost)
  - Snapshots available
  - Easy firewall management
  - 1-click Docker install
- **Cons:**
  - Slightly more expensive than competitors
- **Best for:** First-time VM users, fast setup

**How to provision:**
1. Sign up at digitalocean.com
2. Create Droplet → Ubuntu 22.04 → Basic → $18/mo plan
3. Choose region closest to proxy IP (or San Francisco for US West)
4. Add SSH key
5. Enable automated backups
6. Done in 60 seconds

---

### 2. Linode (Akamai) - Great Alternative
**Plan:** Shared CPU - 2 GB RAM
- **Cost:** $12/month
- **Storage:** 50 GB SSD
- **Transfer:** 2 TB
- **Pros:**
  - Lower cost than DigitalOcean
  - Excellent performance
  - Good support
  - Backups: +$2/month
- **Cons:**
  - UI less intuitive for beginners
- **Best for:** Cost-conscious, still reliable

---

### 3. Vultr - Budget Option
**Plan:** Cloud Compute - 2 vCPU, 2 GB RAM
- **Cost:** $12/month
- **Storage:** 55 GB SSD
- **Transfer:** 2 TB
- **Pros:**
  - Competitive pricing
  - Many datacenter locations
  - Hourly billing
- **Cons:**
  - Less polished than DO
  - Support can be slower
- **Best for:** Budget priority, hourly billing flexibility

---

### 4. AWS Lightsail - AWS Ecosystem
**Plan:** 2 GB RAM
- **Cost:** $18/month
- **Storage:** 60 GB SSD
- **Transfer:** 3 TB
- **Pros:**
  - Easier than full AWS EC2
  - Good if already using AWS
  - Can integrate with other AWS services
  - Static IP included
- **Cons:**
  - Still more complex than DO/Linode
  - Billing can surprise if you exceed limits
- **Best for:** AWS-familiar users, need AWS integrations

---

### 5. Hetzner Cloud - EU Budget Option
**Plan:** CPX11 - 2 vCPU, 2 GB RAM
- **Cost:** €4.51/month (~$5 USD)
- **Storage:** 40 GB SSD
- **Transfer:** 20 TB
- **Pros:**
  - Cheapest option by far
  - Excellent performance
  - Generous bandwidth
- **Cons:**
  - Datacenters only in EU (Germany, Finland)
  - Higher latency if scraping US sites
  - Less known in US market
- **Best for:** EU-based or budget-critical projects

---

## Final Recommendation

### For This Project: DigitalOcean $18/mo plan

**Why:**
1. **Simplicity:** Easiest for client to understand billing and manage
2. **Reliability:** 99.99% uptime SLA
3. **Support:** Best documentation and community support
4. **Backups:** Simple automated backups ($3.60/mo extra)
5. **SSH key management:** Very straightforward
6. **Firewall:** Built-in, easy to configure
7. **Monitoring:** Free built-in graphs (CPU, RAM, disk, bandwidth)

**Total Monthly Cost:**
- Droplet: $18
- Automated Backups: $3.60
- **Subtotal VM: $21.60/month**

---

## Residential Proxy Recommendations

### For CAAA Scraping (Low Volume)

#### 1. Smartproxy ⭐ RECOMMENDED
- **Pricing:** $8.50/GB (with starter plan)
- **Minimum:** $50/month for 6 GB
- **Pros:**
  - Sticky sessions (same IP for 10-30 min)
  - US residential IPs
  - Good for login sessions
  - Simple API
- **Estimated usage:** 1-3 GB/month for this project
- **Monthly cost:** $50 (minimum, get 6 GB)

#### 2. Bright Data (formerly Luminati)
- **Pricing:** $15/GB
- **Minimum:** $300/month
- **Pros:**
  - Premium quality, largest pool
  - Best success rates
- **Cons:**
  - Expensive, high minimum
- **Best for:** High-volume or enterprise only

#### 3. Oxylabs
- **Pricing:** $15/GB
- **Minimum:** $300/month
- **Similar to Bright Data—overkill for MVP**

#### 4. SOAX
- **Pricing:** $99/month for 7 GB (~$14/GB)
- **No huge minimum like Bright Data**
- **Pros:**
  - Good balance of cost/quality
  - US residential available
- **Cons:**
  - Less polished than Smartproxy

#### 5. Static Residential ISP Proxy (Alternative)
- **Pricing:** ~$3-5/IP/month
- **Providers:** IPRoyal, Proxy-Cheap, Webshare
- **Pros:**
  - Fixed IP (best for stable sessions)
  - Much cheaper for low volume
  - No per-GB billing
- **Cons:**
  - Need to buy specific IPs
  - Less flexible
- **Best for:** This use case if CAAA doesn't have heavy anti-bot

---

## Total Monthly Cost Estimate

### Option A: DigitalOcean + Smartproxy (Rotating Residential)
| Item | Cost |
|------|------|
| DigitalOcean VM (2 GB) | $18.00 |
| DO Automated Backups | $3.60 |
| Smartproxy (6 GB minimum) | $50.00 |
| **Total** | **$71.60/month** |

### Option B: DigitalOcean + Static Residential ISP Proxy
| Item | Cost |
|------|------|
| DigitalOcean VM (2 GB) | $18.00 |
| DO Automated Backups | $3.60 |
| Static Residential IP (1) | $4.00 |
| **Total** | **$25.60/month** |

**Recommendation for MVP:** Start with **Option B** (static residential). Test if CAAA blocks it. If sessions are stable, you save $45/month. Upgrade to rotating pool only if needed.

---

## Database Recommendation

### For MVP:
**PostgreSQL in Docker on same VM**
- Cost: $0 (uses VM resources)
- Pros: Simple, no extra billing, fast local access
- Cons: Not isolated, backups via VM snapshots
- Good for: <100K records, single user

### For Production (V2):
**Managed Postgres**
- DigitalOcean Managed DB: $15/month (1 GB RAM, 10 GB storage)
- Pros: Automated backups, monitoring, scaling
- Cons: Extra $15/month
- Good for: Multi-user, production reliability

**Decision:** Start with Postgres in Docker. Migrate to managed when you add users or hit reliability issues.

---

## Setup Time Estimate

| Task | Time |
|------|------|
| Sign up for DO account | 5 min |
| Create droplet | 2 min |
| Configure SSH key | 3 min |
| Connect to VM | 1 min |
| Install dependencies | 5 min |
| Upload scripts | 2 min |
| Configure proxy | 3 min |
| Test proxy connectivity | 2 min |
| **Total** | **~25 min** |

---

## Security Checklist

- [ ] SSH key-only access (disable password auth)
- [ ] Configure UFW firewall (allow 22, 80, 443 only)
- [ ] Automated security updates enabled
- [ ] Fail2ban installed (protects against brute-force)
- [ ] Non-root user created for deployment
- [ ] `.auth_key` and `auth.json.enc` have 600 permissions
- [ ] Secrets stored in environment variables (not code)

---

## Quick Start Commands (DigitalOcean)

### 1. After Droplet Created
```bash
# Connect
ssh root@<droplet-ip>

# Update system
apt update && apt upgrade -y

# Create non-root user
adduser deployer
usermod -aG sudo deployer

# Add your SSH key to deployer
mkdir -p /home/deployer/.ssh
cp /root/.ssh/authorized_keys /home/deployer/.ssh/
chown -R deployer:deployer /home/deployer/.ssh
chmod 700 /home/deployer/.ssh
chmod 600 /home/deployer/.ssh/authorized_keys

# Exit and reconnect as deployer
exit
ssh deployer@<droplet-ip>
```

### 2. Install Dependencies
```bash
# Install basics
sudo apt install -y python3-pip python3-venv git curl ufw fail2ban

# Setup firewall
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# Install Docker (optional, for production)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker deployer
# Log out and back in for docker group to take effect
```

### 3. Create Project Directory
```bash
mkdir -p /srv/caaa_scraper
cd /srv/caaa_scraper
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Playwright
```bash
pip install -r requirements.txt
playwright install chromium
sudo playwright install-deps
```

---

## Monitoring & Alerts (Post-MVP)

### Free Options:
- **UptimeRobot:** Ping VM every 5 min, email on downtime
- **DigitalOcean Monitoring:** Built-in graphs for CPU/RAM/disk
- **Logs:** Set up simple log rotation and grep for errors

### Paid (V2):
- **Datadog:** Full observability ($15/month)
- **Better Stack:** Log aggregation + alerts ($10/month)

---

## Summary: What to Tell the Client

> "I recommend starting with a **DigitalOcean droplet at $18/month** plus a **static residential proxy at ~$4/month**. Total infrastructure: **~$25-30/month** to start. This gives you a secure, reliable VM with automated backups. If we need more powerful proxies later (rotating pool), that would add ~$45/month, but let's test with the simple setup first. Setup takes about 30 minutes, and I'll handle all the technical parts—you'll just need to approve the billing."


