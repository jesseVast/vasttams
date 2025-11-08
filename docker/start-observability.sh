#!/bin/bash

# TAMS Observability Stack Startup Script

echo "🚀 Starting TAMS Observability Stack..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create observability network if it doesn't exist
echo "📡 Creating network..."
docker network create tams-network 2>/dev/null || echo "Network already exists"

# Start the observability stack
echo "🔧 Starting services..."
# Use main docker-compose.yml with observability profile
docker-compose --profile observability up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service status
echo "📊 Service Status:"
docker-compose --profile observability ps

echo ""
echo "✅ Observability Stack Started!"
echo ""
echo "📈 Access Points:"
echo "   • Grafana Dashboard: http://localhost:3000 (admin/admin)"
echo "   • Prometheus: http://localhost:9090"
echo "   • Jaeger Tracing: http://localhost:16686"
echo "   • Alertmanager: http://localhost:9093"
echo ""
echo "🔗 TAMS API Metrics: http://localhost:8000/metrics"
echo "🔗 TAMS API Health: http://localhost:8000/health"
echo ""
echo "To stop the stack: docker-compose --profile observability down" 