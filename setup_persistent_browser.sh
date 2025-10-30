#!/bin/bash
# Setup persistent browser as a system service

echo "Setting up persistent browser service..."

# Copy service file
sudo cp caaa-browser.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable caaa-browser.service

echo ""
echo "✓ Service installed!"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start caaa-browser"
echo "  Stop:    sudo systemctl stop caaa-browser"
echo "  Status:  sudo systemctl status caaa-browser"
echo "  Logs:    sudo journalctl -u caaa-browser -f"
echo ""
echo "After client re-logs in and captures cookies, run:"
echo "  sudo systemctl restart caaa-browser"

