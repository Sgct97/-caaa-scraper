#!/bin/bash
# Complete setup script for NEW 16GB droplet
# Run this immediately after creating the new droplet

set -e  # Exit on any error

echo "=========================================="
echo "CAAA Scraper - New Droplet Setup"
echo "=========================================="

# Update system
echo "Step 1: Updating system..."
export DEBIAN_FRONTEND=noninteractive
apt update && apt upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

# Install dependencies
echo "Step 2: Installing dependencies..."
apt install -y python3.10 python3.10-venv python3-pip git postgresql postgresql-contrib \
    fail2ban ufw x11vnc xvfb websockify novnc curl

# Configure firewall
echo "Step 3: Configuring firewall..."
ufw allow 22
ufw allow 80
ufw allow 443
ufw allow 8000
ufw --force enable

# Setup PostgreSQL
echo "Step 4: Setting up PostgreSQL..."
sudo -u postgres psql << EOF
CREATE DATABASE caaa_scraper;
CREATE USER caaa_user WITH PASSWORD 'secure_password_here';
ALTER DATABASE caaa_scraper OWNER TO caaa_user;
GRANT ALL PRIVILEGES ON DATABASE caaa_scraper TO caaa_user;
EOF

# Create directory structure
echo "Step 5: Creating project directory..."
mkdir -p /srv/caaa_scraper
cd /srv/caaa_scraper

# Clone repository
echo "Step 6: Cloning repository..."
git clone https://github.com/Sgct97/-caaa-scraper.git .

# Create Python virtual environment
echo "Step 7: Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Step 8: Installing Python packages..."
pip install -r requirements.txt

# Install Playwright browsers
echo "Step 9: Installing Playwright browsers..."
python -m playwright install chromium
python -m playwright install-deps

# Install Ollama
echo "Step 10: Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Download Llama model
echo "Step 11: Downloading Llama 3.1 8B (this takes 5-10 min)..."
ollama pull llama3.1:8b-instruct-q4_K_M

# Initialize database schema
echo "Step 12: Initializing database..."
# Run schema if exists, otherwise create tables via Python
if [ -f "schema.sql" ]; then
    sudo -u postgres psql caaa_scraper < schema.sql
else
    # Create tables directly
    sudo -u postgres psql caaa_scraper << 'SQLEOF'
CREATE TABLE IF NOT EXISTS searches (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50),
    user_query TEXT,
    search_fields JSONB,
    ai_enhanced BOOLEAN DEFAULT FALSE,
    total_found INTEGER,
    total_relevant INTEGER,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(50) PRIMARY KEY,
    subject TEXT,
    author VARCHAR(255),
    posted_date DATE,
    listserv VARCHAR(100),
    url TEXT,
    body TEXT,
    first_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS search_results (
    search_id UUID REFERENCES searches(id),
    message_id VARCHAR(50) REFERENCES messages(id),
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (search_id, message_id)
);

CREATE TABLE IF NOT EXISTS ai_analyses (
    search_id UUID REFERENCES searches(id),
    message_id VARCHAR(50) REFERENCES messages(id),
    is_relevant BOOLEAN,
    confidence_score FLOAT,
    ai_reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (search_id, message_id)
);
SQLEOF
fi
echo "✓ Database schema created"

# Grant database permissions
sudo -u postgres psql caaa_scraper << EOF
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO caaa_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO caaa_user;
EOF

# Setup VNC
echo "Step 13: Configuring VNC..."
# VNC start script is already in repo as start_vnc.sh

# Setup persistent browser service
echo "Step 14: Setting up persistent browser service..."
# Copy the service file from repo
cp /srv/caaa_scraper/caaa-browser.service /etc/systemd/system/
systemctl daemon-reload

# Don't start the service yet - need cookies first
# systemctl enable caaa-browser
# systemctl start caaa-browser

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "NEXT STEPS:"
echo "1. Upload auth.json:"
echo "   scp auth_backup.json root@NEW_IP:/srv/caaa_scraper/auth.json"
echo ""
echo "2. Test cookies:"
echo "   cd /srv/caaa_scraper"
echo "   source venv/bin/activate"
echo "   python cookie_capture.py verify"
echo ""
echo "3. If cookies work, start persistent browser:"
echo "   systemctl enable caaa-browser"
echo "   systemctl start caaa-browser"
echo ""
echo "4. If cookies DON'T work, recapture:"
echo "   bash start_vnc.sh"
echo "   # Then screenshare with client"
echo ""

