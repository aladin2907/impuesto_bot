#!/bin/bash
# Quick script to check server status

echo "============================================================"
echo "🔍 CHECKING SERVER STATUS"
echo "============================================================"

# Check if mafiavlc.org responds
echo ""
echo "1️⃣  Checking if server is accessible..."
if curl -s -o /dev/null -w "%{http_code}" https://mafiavlc.org/ --connect-timeout 5 | grep -q "200\|301\|302"; then
    echo "✅ Server is accessible"
else
    echo "❌ Server not accessible or down"
fi

# Try health endpoint
echo ""
echo "2️⃣  Checking API health endpoint..."
HEALTH_STATUS=$(curl -s https://mafiavlc.org/health 2>&1)
if [ $? -eq 0 ]; then
    echo "Health response:"
    echo "$HEALTH_STATUS" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_STATUS"
else
    echo "❌ Health endpoint not responding"
fi

# Try root endpoint
echo ""
echo "3️⃣  Checking API root endpoint..."
ROOT_STATUS=$(curl -s https://mafiavlc.org/ 2>&1)
if [ $? -eq 0 ]; then
    echo "Root response:"
    echo "$ROOT_STATUS" | python3 -m json.tool 2>/dev/null || echo "$ROOT_STATUS"
else
    echo "❌ Root endpoint not responding"
fi

echo ""
echo "============================================================"
echo "📝 NEXT STEPS:"
echo "============================================================"
echo ""
echo "If server is not responding, you need to:"
echo "1. SSH to the server: ssh root@mafiavlc.org"
echo "2. Check if Docker is running: docker ps"
echo "3. Check container logs: docker logs impuesto-bot-api"
echo "4. Check .env file: cat /root/impuesto_bot/.env | grep ELASTIC"
echo ""
echo "Then run on the server:"
echo "  cd /root/impuesto_bot"
echo "  ./scripts/fix_server_connections.sh"
echo ""





