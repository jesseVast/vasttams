#!/bin/bash
# Script to start webhook test server, register webhook, and run tests

set -e

echo "🚀 Starting Webhook Test Server..."
python3 tests/webhook_test_server.py --port 8080 > /tmp/webhook_server.log 2>&1 &
WEBHOOK_PID=$!
echo "Webhook server started with PID: $WEBHOOK_PID"

# Wait for server to start
sleep 2

# Check if server is running
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "❌ Webhook server failed to start"
    kill $WEBHOOK_PID 2>/dev/null || true
    exit 1
fi

echo "✅ Webhook server is running on http://localhost:8080"

# Register webhook (requires TAMS API server to be running)
echo ""
echo "📝 Registering webhook for all events..."
if python3 tests/register_webhook_all_events.py; then
    echo "✅ Webhook registered successfully"
else
    echo "⚠️  Webhook registration failed (API server may not be running)"
fi

# Run webhook tests
echo ""
echo "🧪 Running webhook tests..."
/Users/jesse.thaloor/Developer/python/vasttams/bin/python -m pytest tests/webhooks/test_crud.py -v --tb=short

# Cleanup
echo ""
echo "🛑 Stopping webhook server..."
kill $WEBHOOK_PID 2>/dev/null || true
echo "✅ Done"
