#!/bin/bash
# ============================================================
# Setup PostgreSQL on Ubuntu 22.04 VM
# ============================================================

set -e  # Exit on error

echo "============================================================"
echo "Setting up PostgreSQL for CAAA Scraper"
echo "============================================================"

# Install PostgreSQL
echo ""
echo "→ Step 1: Installing PostgreSQL..."
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# Start PostgreSQL
echo ""
echo "→ Step 2: Starting PostgreSQL service..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
echo ""
echo "→ Step 3: Creating database and user..."
sudo -u postgres psql <<EOF
-- Create user
CREATE USER caaa_user WITH PASSWORD 'caaa_scraper_2025';

-- Create database
CREATE DATABASE caaa_scraper OWNER caaa_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE caaa_scraper TO caaa_user;

\q
EOF

echo ""
echo "→ Step 4: Installing UUID extension and creating schema..."
sudo -u postgres psql -d caaa_scraper -f /srv/caaa_scraper/database_schema.sql

echo ""
echo "✓ PostgreSQL setup complete!"
echo ""
echo "Database credentials:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: caaa_scraper"
echo "  User: caaa_user"
echo "  Password: caaa_scraper_2025"
echo ""
echo "To connect: psql -U caaa_user -d caaa_scraper"

