#!/bin/bash
# Script to diagnose and fix connection issues on the server

echo "============================================================"
echo "🔧 FIXING SERVER CONNECTIONS"
echo "============================================================"

# Get project directory (assume script is in scripts/ folder)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "📍 Project directory: $PROJECT_DIR"

# Check if .env exists
echo ""
echo "1️⃣  Checking .env file..."
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    
    # Check key variables (masked)
    if grep -q "ELASTIC_CLOUD_ID=" .env; then
        echo "✅ ELASTIC_CLOUD_ID is set"
    else
        echo "❌ ELASTIC_CLOUD_ID is MISSING!"
    fi
    
    if grep -q "ELASTIC_API_KEY=" .env; then
        echo "✅ ELASTIC_API_KEY is set"
    else
        echo "❌ ELASTIC_API_KEY is MISSING!"
    fi
    
    if grep -q "SUPABASE_DB_URL=" .env; then
        echo "✅ SUPABASE_DB_URL is set"
    else
        echo "❌ SUPABASE_DB_URL is MISSING!"
    fi
else
    echo "❌ .env file NOT FOUND!"
    echo ""
    echo "Create .env file with:"
    echo "  ELASTIC_CLOUD_ID=..."
    echo "  ELASTIC_API_KEY=..."
    echo "  SUPABASE_DB_URL=..."
    echo "  SUPABASE_URL=..."
    echo "  SUPABASE_KEY=..."
    echo "  OPENAI_API_KEY=..."
    exit 1
fi

# Check if venv exists
echo ""
echo "2️⃣  Checking virtual environment..."
if [ -d "venv" ]; then
    echo "✅ venv directory exists"
else
    echo "❌ venv NOT FOUND! Creating..."
    python3 -m venv venv
fi

# Activate venv and test connections
echo ""
echo "3️⃣  Testing connections..."
source venv/bin/activate

python scripts/diagnose_connections.py
DIAG_EXIT=$?

if [ $DIAG_EXIT -eq 0 ]; then
    echo ""
    echo "🎉 All connections working!"
else
    echo ""
    echo "⚠️  Some connections failed. Check output above."
    echo ""
    echo "💡 Common fixes:"
    echo ""
    echo "For Elasticsearch 401 error:"
    echo "  1. Go to https://cloud.elastic.co/"
    echo "  2. Select your deployment"
    echo "  3. Management → API Keys → Create new"
    echo "  4. Update ELASTIC_API_KEY in .env"
    echo ""
    echo "For Supabase connection error:"
    echo "  1. Go to Supabase dashboard"
    echo "  2. Project Settings → Database"
    echo "  3. Copy 'Connection pooler' URL (Session mode)"
    echo "  4. Update SUPABASE_DB_URL in .env"
fi

# Check if Docker is running
echo ""
echo "4️⃣  Checking Docker status..."
if command -v docker &> /dev/null; then
    echo "✅ Docker is installed"
    
    if docker ps &> /dev/null; then
        echo "✅ Docker is running"
        
        # Check if our containers are running
        if docker ps | grep -q "impuesto-bot-api"; then
            echo "✅ impuesto-bot-api container is running"
            
            echo ""
            echo "📋 Container logs (last 20 lines):"
            docker logs --tail 20 impuesto-bot-api
            
            echo ""
            echo "🔄 To restart the container with new .env:"
            echo "  cd $PROJECT_DIR"
            echo "  docker-compose down"
            echo "  docker-compose up -d --build"
        else
            echo "⚠️  impuesto-bot-api container NOT running"
            echo ""
            echo "🚀 To start it:"
            echo "  cd $PROJECT_DIR"
            echo "  docker-compose up -d --build"
        fi
    else
        echo "⚠️  Docker daemon is not running"
    fi
else
    echo "ℹ️  Docker not installed (may be running without Docker)"
fi

echo ""
echo "============================================================"
echo "✅ DIAGNOSTIC COMPLETE"
echo "============================================================"





