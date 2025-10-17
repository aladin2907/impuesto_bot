#!/bin/bash
# TuExpertoFiscal NAIL - Server Setup Script for Digital Ocean
# Run this script on your Digital Ocean droplet

set -e  # Exit on error

echo "=========================================="
echo "TuExpertoFiscal NAIL - Server Setup"
echo "=========================================="

# Update system
echo "1. Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.11
echo "2. Installing Python 3.11..."
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install system dependencies
echo "3. Installing system dependencies..."
sudo apt-get install -y build-essential libpq-dev git curl

# Create project directory
echo "4. Setting up project directory..."
PROJECT_DIR="$HOME/impuesto_bot"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Clone repo (if not already cloned)
if [ ! -d ".git" ]; then
    echo "5. Cloning repository..."
    read -p "Enter your Git repository URL: " REPO_URL
    git clone $REPO_URL .
else
    echo "5. Repository already exists, pulling latest..."
    git pull
fi

# Create virtual environment
echo "6. Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "7. Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
echo "8. Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env file with your actual credentials:"
    echo "   nano .env"
else
    echo ".env file already exists"
fi

# Create necessary directories
echo "9. Creating directories..."
mkdir -p logs
mkdir -p data/raw_documents

# Set up cron jobs
echo "10. Setting up cron jobs..."
echo "To add cron jobs, run:"
echo "   crontab -e"
echo "Then paste contents from deployment/crontab_schedule.txt"
echo "(Make sure to update paths in the file first!)"

# Create systemd service for FastAPI (optional but recommended)
echo "11. Creating systemd service for FastAPI..."
sudo tee /etc/systemd/system/tuexpertofiscal.service > /dev/null <<EOF
[Unit]
Description=TuExpertoFiscal NAIL Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "12. Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable tuexpertofiscal
# sudo systemctl start tuexpertofiscal  # Uncomment when ready

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file: nano .env"
echo "2. Update crontab: crontab -e (copy from deployment/crontab_schedule.txt)"
echo "3. Start FastAPI service: sudo systemctl start tuexpertofiscal"
echo "4. Check service status: sudo systemctl status tuexpertofiscal"
echo "5. View logs: journalctl -u tuexpertofiscal -f"
echo ""
echo "Cron logs will be in: $PROJECT_DIR/logs/"
echo ""
echo "=========================================="
