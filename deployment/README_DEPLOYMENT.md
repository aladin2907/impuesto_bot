# Deployment Guide - Digital Ocean

This guide explains how to deploy TuExpertoFiscal NAIL on your Digital Ocean server.

## Prerequisites

- Digital Ocean Droplet (Ubuntu 22.04 LTS recommended)
- Minimum 2GB RAM, 2 vCPUs
- Root or sudo access
- SSH access to the server

## Quick Start

### 1. Connect to Your Server

```bash
ssh root@your_server_ip
# or
ssh your_user@your_server_ip
```

### 2. Run Setup Script

```bash
# Download and run the setup script
curl -o setup_server.sh https://raw.githubusercontent.com/your-repo/impuesto_bot/main/deployment/setup_server.sh
chmod +x setup_server.sh
./setup_server.sh
```

Or manually:

```bash
# Clone the repository
cd ~
git clone https://github.com/your-username/impuesto_bot.git
cd impuesto_bot

# Run setup
chmod +x deployment/setup_server.sh
./deployment/setup_server.sh
```

### 3. Configure Environment Variables

```bash
nano .env
```

Add all your credentials:
```env
# LLM Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Elasticsearch
ELASTIC_CLOUD_ID=...
ELASTIC_API_KEY=...

# Supabase
SUPABASE_URL=https://mslfndlzjqttteihiopt.supabase.co
SUPABASE_KEY=...
SUPABASE_DB_URL=postgresql://...

# Telegram
TELEGRAM_BOT_TOKEN=...

# etc.
```

### 4. Set Up Cron Jobs

```bash
# Edit crontab
crontab -e

# Paste this (update paths first!):
```

Copy contents from `deployment/crontab_schedule.txt` and update paths.

### 5. Start the Bot Service

```bash
# Start FastAPI service
sudo systemctl start tuexpertofiscal

# Check status
sudo systemctl status tuexpertofiscal

# View logs
journalctl -u tuexpertofiscal -f
```

## Manual Setup (Step by Step)

If you prefer to set up manually:

### 1. Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 2. Install Python 3.11

```bash
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
```

### 3. Install Dependencies

```bash
sudo apt-get install -y build-essential libpq-dev git curl
```

### 4. Clone Repository

```bash
cd ~
git clone https://github.com/your-username/impuesto_bot.git
cd impuesto_bot
```

### 5. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 6. Install Python Packages

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 7. Configure Environment

```bash
cp .env.example .env
nano .env
# Fill in all credentials
```

### 8. Create Directories

```bash
mkdir -p logs
mkdir -p data/raw_documents
```

### 9. Test Connection

```bash
python scripts/test_connections.py
```

Should output:
```
✅ Environment variables loaded
✅ Elasticsearch connected successfully
✅ Supabase connected successfully
```

### 10. Set Up Systemd Service

Create service file:

```bash
sudo nano /etc/systemd/system/tuexpertofiscal.service
```

Paste:

```ini
[Unit]
Description=TuExpertoFiscal NAIL Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user/impuesto_bot
Environment="PATH=/home/your_user/impuesto_bot/venv/bin"
ExecStart=/home/your_user/impuesto_bot/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tuexpertofiscal
sudo systemctl start tuexpertofiscal
sudo systemctl status tuexpertofiscal
```

### 11. Set Up Cron Jobs

```bash
crontab -e
```

Add (update paths):

```cron
SHELL=/bin/bash
PROJECT_DIR=/home/your_user/impuesto_bot
VENV_PYTHON=/home/your_user/impuesto_bot/venv/bin/python
LOG_DIR=/home/your_user/impuesto_bot/logs

# Telegram ingestion - Monday 2 AM
0 2 * * 1 cd $PROJECT_DIR && $VENV_PYTHON scripts/ingestion/ingest_telegram_groups.py >> $LOG_DIR/telegram_ingest.log 2>&1

# News ingestion - Daily 8 AM
0 8 * * * cd $PROJECT_DIR && $VENV_PYTHON scripts/ingestion/ingest_news_articles.py >> $LOG_DIR/news_ingest.log 2>&1

# Reminders - Daily 9 AM
0 9 * * * cd $PROJECT_DIR && $VENV_PYTHON scripts/reminders/send_calendar_reminders.py >> $LOG_DIR/reminders.log 2>&1

# Clean old logs - Weekly
0 3 * * 0 find $LOG_DIR -name "*.log" -mtime +30 -delete
```

## Monitoring & Maintenance

### Check Service Status

```bash
sudo systemctl status tuexpertofiscal
```

### View Logs

```bash
# FastAPI logs
journalctl -u tuexpertofiscal -f

# Cron job logs
tail -f ~/impuesto_bot/logs/telegram_ingest.log
tail -f ~/impuesto_bot/logs/news_ingest.log
tail -f ~/impuesto_bot/logs/reminders.log
```

### Restart Service

```bash
sudo systemctl restart tuexpertofiscal
```

### Update Code

```bash
cd ~/impuesto_bot
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tuexpertofiscal
```

### Check Cron Jobs

```bash
# List current cron jobs
crontab -l

# Edit cron jobs
crontab -e
```

## Firewall Setup (Optional but Recommended)

```bash
# Allow SSH
sudo ufw allow 22

# Allow HTTP/HTTPS (if using webhook)
sudo ufw allow 80
sudo ufw allow 443

# Allow your bot port (if exposing directly)
sudo ufw allow 8000

# Enable firewall
sudo ufw enable
```

## Nginx Setup (Optional - for production)

If you want to use Nginx as reverse proxy:

```bash
sudo apt-get install nginx

sudo nano /etc/nginx/sites-available/tuexpertofiscal
```

Paste:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/tuexpertofiscal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
journalctl -u tuexpertofiscal -n 50

# Check if port is in use
sudo lsof -i :8000

# Check permissions
ls -la /home/your_user/impuesto_bot
```

### Cron Jobs Not Running

```bash
# Check if cron is running
sudo systemctl status cron

# Check cron logs
grep CRON /var/log/syslog

# Test script manually
cd ~/impuesto_bot
source venv/bin/activate
python scripts/ingestion/ingest_telegram_groups.py
```

### Out of Memory

```bash
# Check memory usage
free -h

# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Security Best Practices

1. **Use SSH keys, not passwords**
2. **Keep .env file secure** (never commit to git)
3. **Update system regularly**: `sudo apt-get update && sudo apt-get upgrade`
4. **Use firewall** (ufw)
5. **Monitor logs** for suspicious activity
6. **Backup database** regularly

---

*Developed by NAIL - Nahornyi AI Lab*
