#!/bin/bash

# Server setup script for AWS EC2
# Run this script on your EC2 instance after first SSH connection

set -e

echo "🚀 Setting up TuExpertoFiscal server..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo apt install git -y

# Install additional tools
sudo apt install curl wget htop -y

# Create app directory
mkdir -p /home/ubuntu/impuesto_bot
cd /home/ubuntu/impuesto_bot

# Clone repository
git clone https://github.com/aladin2907/impuesto_bot.git .

# Create logs directory
mkdir -p logs

# Create .env file template
cat > .env << EOF
# Supabase Configuration
SUPABASE_URL=https://mslfndlzjqttteihiopt.supabase.co
SUPABASE_KEY=your_supabase_key_here

# Elasticsearch Configuration  
ELASTICSEARCH_URL=your_elasticsearch_url_here
ELASTICSEARCH_USERNAME=your_username_here
ELASTICSEARCH_PASSWORD=your_password_here

# LLM Configuration
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GOOGLE_API_KEY=your_google_key_here

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_token_here
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here

# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
EOF

echo "📝 Please edit .env file with your actual API keys:"
echo "   nano /home/ubuntu/impuesto_bot/.env"

# Set proper permissions
sudo chown -R ubuntu:ubuntu /home/ubuntu/impuesto_bot

echo "✅ Server setup completed!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run: docker-compose up -d"
echo "3. Check logs: docker-compose logs -f"
echo ""
echo "🔧 To start the application:"
echo "   cd /home/ubuntu/impuesto_bot"
echo "   docker-compose up -d"
