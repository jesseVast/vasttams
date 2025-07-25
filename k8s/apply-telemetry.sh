#!/bin/bash

# Apply Telemetry Updates to Kubernetes Deployment
# This script updates the K8s configuration to enable telemetry features

echo "🔧 Applying telemetry updates to Kubernetes deployment..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace tams &> /dev/null; then
    echo "❌ Namespace 'tams' does not exist. Please create it first:"
    echo "   kubectl create namespace tams"
    exit 1
fi

echo "📋 Current deployment status:"
kubectl get pods -n tams

echo ""
echo "🔄 Applying updated configurations..."

# Apply the updated configurations
echo "   • Updating deployment with telemetry environment variables..."
kubectl apply -f deployment.yaml

echo "   • Updating configmap with telemetry settings..."
kubectl apply -f configmap.yaml

echo "   • Updating service with Prometheus annotations..."
kubectl apply -f service.yaml

echo ""
echo "🔄 Restarting deployment to pick up changes..."
kubectl rollout restart deployment tams-api -n tams

echo ""
echo "⏳ Waiting for deployment to be ready..."
kubectl rollout status deployment tams-api -n tams

echo ""
echo "✅ Telemetry updates applied successfully!"
echo ""
echo "📊 Verification:"
echo "   • Check deployment status: kubectl get pods -n tams"
echo "   • Check telemetry endpoints:"
echo "     - Health: kubectl port-forward service/tams-api-service 8080:80 -n tams && curl http://localhost:8080/health"
echo "     - Metrics: kubectl port-forward service/tams-api-service 8080:80 -n tams && curl http://localhost:8080/metrics"
echo ""
echo "🔗 Telemetry Features Now Available:"
echo "   • Enhanced health checks with system metrics"
echo "   • Prometheus metrics at /metrics endpoint"
echo "   • Structured logging with correlation IDs"
echo "   • OpenTelemetry tracing (if Jaeger/OTLP collectors are deployed)"
echo ""
echo "📝 Note: For full observability, consider deploying:"
echo "   • Prometheus for metrics collection"
echo "   • Grafana for visualization"
echo "   • Jaeger for distributed tracing" 