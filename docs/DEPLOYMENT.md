# TAMS Deployment Documentation

This document provides comprehensive deployment instructions for the TAMS (Time-addressable Media Store) API system.

## 🚀 **Deployment Overview**

The TAMS API can be deployed using multiple approaches depending on your infrastructure and requirements:

- **Local Development**: Direct Python execution with hot reload
- **Docker**: Containerized deployment with Docker Compose
- **Kubernetes**: Production-grade orchestration with K8s manifests
- **Cloud Platforms**: AWS, GCP, Azure deployment options

## 🛠️ **Prerequisites**

### **System Requirements**

- **Operating System**: Linux (Ubuntu 20.04+), macOS 12+, or Windows 10+
- **Python**: Python 3.12+ with pip
- **Memory**: Minimum 4GB RAM, recommended 8GB+
- **Storage**: Minimum 10GB free space, recommended 50GB+
- **Network**: Access to VAST database and S3-compatible storage

### **External Dependencies**

- **VAST Database**: Running VAST server with network access
- **S3-Compatible Storage**: MinIO, AWS S3, or VAST S3
- **Network Access**: Firewall rules for required ports

### **Required Ports**

| Port | Service | Description |
|------|---------|-------------|
| 8000 | TAMS API | Main API service |
| 9090 | VAST Database | VAST server endpoint |
| 9090 | S3 Storage | S3-compatible storage endpoint |
| 3000 | Grafana | Monitoring dashboard (optional) |
| 9090 | Prometheus | Metrics collection (optional) |

## 🏠 **Local Development Deployment**

### **1. Environment Setup**

#### **Python Environment**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

#### **Environment Configuration**
```bash
# Copy environment template
cp env.example .env

# Edit environment variables
nano .env
```

**Required Environment Variables:**
```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
LOG_LEVEL=INFO

# VAST Database Configuration
VAST_ENDPOINT=http://your-vast-server:9090
VAST_ACCESS_KEY=your-access-key
VAST_SECRET_KEY=your-secret-key
VAST_BUCKET=your-bucket-name
VAST_SCHEMA=tams7

# S3 Storage Configuration
S3_ENDPOINT_URL=http://your-s3-server:9090
S3_ACCESS_KEY_ID=your-s3-access-key
S3_SECRET_ACCESS_KEY=your-s3-secret-key
S3_BUCKET_NAME=your-s3-bucket
S3_USE_SSL=false
S3_REGION=us-east-1

# Storage Configuration
TAMS_STORAGE_PATH=tams
S3_TAMS_ROOT=/tams
GET_URLS_MAX_COUNT=5
FLOW_STORAGE_DEFAULT_LIMIT=10

# Presigned URL Configuration
S3_PRESIGNED_URL_UPLOAD_TIMOUT=3600
S3_PRESIGNED_URL_DOWNLOAD_TIMEOUT=3600

# Security
SECRET_KEY=your-secret-key-here
```

### **2. Database Setup**

#### **VAST Database Connection**
```bash
# Test VAST connection
python mgmt/test_diagnostics.py --check=db

# Create required tables (automatic on first run)
python run.py
```

#### **S3 Storage Setup**
```bash
# Test S3 connection
python mgmt/test_diagnostics.py --check=s3

# Verify bucket access
python mgmt/check_s3_direct.py
```

### **3. Application Startup**

#### **Direct Python Execution**
```bash
# Start the application
python run.py

# Or use uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### **Development with Hot Reload**
```bash
# Start with auto-reload for development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### **4. Verification**

#### **Health Check**
```bash
curl http://localhost:8000/health
```

#### **API Documentation**
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

#### **Service Information**
```bash
curl http://localhost:8000/service
```

## 🐳 **Docker Deployment**

### **1. Docker Setup**

#### **Install Docker**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# macOS
brew install docker docker-compose

# Windows
# Download Docker Desktop from https://www.docker.com/products/docker-desktop
```

#### **Verify Installation**
```bash
docker --version
docker-compose --version
```

### **2. Docker Configuration**

#### **Dockerfile**
The project includes a multi-stage Dockerfile for optimized builds:

```dockerfile
# Build stage
FROM python:3.12-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# Set PATH to include user-installed packages
ENV PATH=/root/.local/bin:$PATH

# Create non-root user
RUN useradd --create-home --shell /bin/bash tams
USER tams

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["python", "run.py"]
```

#### **Docker Compose Configuration**
```yaml
# docker-compose.yml
version: '3.8'

services:
  tams-api:
    build: .
    container_name: tams-api
    ports:
      - "8000:8000"
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - DEBUG=false
      - LOG_LEVEL=INFO
      - VAST_ENDPOINT=${VAST_ENDPOINT}
      - VAST_ACCESS_KEY=${VAST_ACCESS_KEY}
      - VAST_SECRET_KEY=${VAST_SECRET_KEY}
      - VAST_BUCKET=${VAST_BUCKET}
      - VAST_SCHEMA=${VAST_SCHEMA}
      - S3_ENDPOINT_URL=${S3_ENDPOINT_URL}
      - S3_ACCESS_KEY_ID=${S3_ACCESS_KEY_ID}
      - S3_SECRET_ACCESS_KEY=${S3_SECRET_ACCESS_KEY}
      - S3_BUCKET_NAME=${S3_BUCKET_NAME}
      - S3_USE_SSL=${S3_USE_SSL}
      - S3_REGION=${S3_REGION}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - tams-network

  # Optional: Add MinIO for local S3-compatible storage
  minio:
    image: minio/minio:latest
    container_name: tams-minio
    ports:
      - "9090:9000"
      - "9091:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    networks:
      - tams-network

networks:
  tams-network:
    driver: bridge

volumes:
  minio_data:
```

### **3. Docker Deployment Steps**

#### **Build and Start**
```bash
# Navigate to docker directory
cd docker

# Build and start services
docker-compose up --build -d

# View logs
docker-compose logs -f tams-api

# Check service status
docker-compose ps
```

#### **Environment Configuration**
```bash
# Create environment file
cp ../env.example .env

# Edit environment variables
nano .env

# Restart services with new environment
docker-compose down
docker-compose up -d
```

#### **Service Management**
```bash
# Stop services
docker-compose down

# Restart services
docker-compose restart

# View service logs
docker-compose logs tams-api

# Access container shell
docker-compose exec tams-api bash
```

### **4. Docker Production Configuration**

#### **Production Docker Compose**
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  tams-api:
    build: .
    container_name: tams-api-prod
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - LOG_LEVEL=WARNING
      - VAST_ENDPOINT=${VAST_ENDPOINT}
      - VAST_ACCESS_KEY=${VAST_ACCESS_KEY}
      - VAST_SECRET_KEY=${VAST_SECRET_KEY}
      - VAST_BUCKET=${VAST_BUCKET}
      - VAST_SCHEMA=${VAST_SCHEMA}
      - S3_ENDPOINT_URL=${S3_ENDPOINT_URL}
      - S3_ACCESS_KEY_ID=${S3_ACCESS_KEY_ID}
      - S3_SECRET_ACCESS_KEY=${S3_SECRET_ACCESS_KEY}
      - S3_BUCKET_NAME=${S3_BUCKET_NAME}
      - S3_USE_SSL=${S3_USE_SSL}
      - S3_REGION=${S3_REGION}
    volumes:
      - ./logs:/app/logs
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    networks:
      - tams-network

networks:
  tams-network:
    driver: bridge
```

#### **Production Deployment**
```bash
# Deploy production configuration
docker-compose -f docker-compose.prod.yml up --build -d

# Monitor production deployment
docker-compose -f docker-compose.prod.yml logs -f tams-api
```

## ☸️ **Kubernetes Deployment**

### **1. Kubernetes Prerequisites**

#### **Required Tools**
```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm (optional, for advanced deployments)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

#### **Cluster Access**
```bash
# Verify cluster access
kubectl cluster-info

# Check nodes
kubectl get nodes

# Check namespaces
kubectl get namespaces
```

### **2. Kubernetes Manifests**

#### **Namespace Configuration**
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tams
  labels:
    name: tams
    app: tams-api
```

#### **ConfigMap Configuration**
```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tams-config
  namespace: tams
data:
  vast_endpoint: "http://your-vast-server:9090"
  vast_bucket: "your-bucket-name"
  vast_schema: "tams7"
  s3_endpoint_url: "http://your-s3-server:9090"
  s3_bucket_name: "your-s3-bucket"
  s3_region: "us-east-1"
  tams_storage_path: "tams"
  log_level: "INFO"
  debug: "false"
```

#### **Secret Configuration**
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: tams-secrets
  namespace: tams
type: Opaque
data:
  vast_access_key: <base64-encoded-access-key>
  vast_secret_key: <base64-encoded-secret-key>
  s3_access_key_id: <base64-encoded-s3-access-key>
  s3_secret_access_key: <base64-encoded-s3-secret-key>
  secret_key: <base64-encoded-secret-key>
```

#### **Deployment Configuration**
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tams-api
  namespace: tams
  labels:
    app: tams-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tams-api
  template:
    metadata:
      labels:
        app: tams-api
    spec:
      containers:
      - name: tams-api
        image: tams-api:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: HOST
          value: "0.0.0.0"
        - name: PORT
          value: "8000"
        - name: DEBUG
          valueFrom:
            configMapKeyRef:
              name: tams-config
              key: debug
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: tams-config
              key: log_level
        - name: VAST_ENDPOINT
          valueFrom:
            configMapKeyRef:
              name: tams-config
              key: vast_endpoint
        - name: VAST_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: tams-secrets
              key: vast_access_key
        - name: VAST_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: tams-secrets
              key: vast_secret_key
        - name: VAST_BUCKET
          valueFrom:
            configMapKeyRef:
              name: tams-config
              key: vast_bucket
        - name: VAST_SCHEMA
          valueFrom:
            configMapKeyRef:
              name: tams-config
              key: vast_schema
        - name: S3_ENDPOINT_URL
          valueFrom:
            configMapKeyRef:
              name: tams-config
              key: s3_endpoint_url
        - name: S3_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: tams-secrets
              key: s3_access_key_id
        - name: S3_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: tams-secrets
              key: s3_secret_access_key
        - name: S3_BUCKET_NAME
          valueFrom:
            configMapKeyRef:
              name: tams-config
              key: s3_bucket_name
        - name: S3_REGION
          valueFrom:
            configMapKeyRef:
              name: tams-config
              key: s3_region
        - name: TAMS_STORAGE_PATH
          valueFrom:
            configMapKeyRef:
              name: tams-config
              key: tams_storage_path
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: tams-secrets
              key: secret_key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: logs
        emptyDir: {}
      imagePullSecrets:
      - name: tams-registry-secret
```

#### **Service Configuration**
```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: tams-api-service
  namespace: tams
  labels:
    app: tams-api
spec:
  selector:
    app: tams-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
    name: http
  type: LoadBalancer
```

#### **Ingress Configuration**
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tams-api-ingress
  namespace: tams
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
spec:
  rules:
  - host: tams-api.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: tams-api-service
            port:
              number: 80
```

#### **Horizontal Pod Autoscaler**
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: tams-api-hpa
  namespace: tams
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: tams-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### **3. Kubernetes Deployment Steps**

#### **Create Namespace**
```bash
kubectl apply -f k8s/namespace.yaml
```

#### **Create Secrets and ConfigMaps**
```bash
# Create secrets (update with your actual values)
kubectl create secret generic tams-secrets \
  --from-literal=vast_access_key=your-access-key \
  --from-literal=vast_secret_key=your-secret-key \
  --from-literal=s3_access_key_id=your-s3-access-key \
  --from-literal=s3_secret_access_key=your-s3-secret-key \
  --from-literal=secret_key=your-secret-key \
  -n tams

# Apply configmap
kubectl apply -f k8s/configmap.yaml
```

#### **Deploy Application**
```bash
# Apply deployment
kubectl apply -f k8s/deployment.yaml

# Apply service
kubectl apply -f k8s/service.yaml

# Apply ingress (if using)
kubectl apply -f k8s/ingress.yaml

# Apply HPA
kubectl apply -f k8s/hpa.yaml
```

#### **Verify Deployment**
```bash
# Check deployment status
kubectl get deployments -n tams

# Check pod status
kubectl get pods -n tams

# Check service status
kubectl get services -n tams

# Check ingress status
kubectl get ingress -n tams
```

### **4. Kubernetes Management**

#### **Scaling**
```bash
# Scale deployment manually
kubectl scale deployment tams-api --replicas=5 -n tams

# Check HPA status
kubectl get hpa -n tams
```

#### **Updates and Rollouts**
```bash
# Update image
kubectl set image deployment/tams-api tams-api=new-image:tag -n tams

# Check rollout status
kubectl rollout status deployment/tams-api -n tams

# Rollback if needed
kubectl rollout undo deployment/tams-api -n tams
```

#### **Logs and Debugging**
```bash
# View pod logs
kubectl logs -f deployment/tams-api -n tams

# Access pod shell
kubectl exec -it deployment/tams-api -n tams -- bash

# Check events
kubectl get events -n tams
```

## ☁️ **Cloud Platform Deployment**

### **1. AWS Deployment**

#### **ECS/Fargate Deployment**
```yaml
# aws/ecs-task-definition.json
{
  "family": "tams-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/tams-api-task-role",
  "containerDefinitions": [
    {
      "name": "tams-api",
      "image": "your-account.dkr.ecr.region.amazonaws.com/tams-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "HOST",
          "value": "0.0.0.0"
        },
        {
          "name": "PORT",
          "value": "8000"
        }
      ],
      "secrets": [
        {
          "name": "VAST_ACCESS_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:vast-access-key"
        },
        {
          "name": "VAST_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:vast-secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/tams-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### **AWS EKS Deployment**
```bash
# Create EKS cluster
eksctl create cluster --name tams-cluster --region us-east-1 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4 --managed

# Deploy TAMS to EKS
kubectl apply -f k8s/ -n tams
```

### **2. Google Cloud Platform**

#### **GKE Deployment**
```bash
# Create GKE cluster
gcloud container clusters create tams-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2

# Deploy TAMS to GKE
kubectl apply -f k8s/ -n tams
```

### **3. Azure**

#### **AKS Deployment**
```bash
# Create AKS cluster
az aks create \
  --resource-group tams-rg \
  --name tams-cluster \
  --node-count 3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# Deploy TAMS to AKS
kubectl apply -f k8s/ -n tams
```

## 📊 **Monitoring and Observability**

### **1. Prometheus and Grafana**

#### **Observability Stack**
```bash
# Start observability stack
cd observability
docker-compose up -d

# Access monitoring tools
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# Alertmanager: http://localhost:9093
```

#### **Grafana Dashboards**
The project includes pre-configured Grafana dashboards:
- **TAMS Overview**: General system health and metrics
- **API Performance**: Request rates, response times, error rates
- **Storage Metrics**: Database and S3 performance
- **System Resources**: CPU, memory, network usage

### **2. Health Monitoring**

#### **Health Endpoints**
```bash
# Basic health check
curl http://your-api:8000/health

# Detailed health check
curl http://your-api:8000/health?detailed=true

# Metrics endpoint
curl http://your-api:8000/metrics
```

#### **Health Check Configuration**
```python
# Custom health checks
@router.get("/health")
async def health_check(detailed: bool = False):
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
    
    if detailed:
        health_status["dependencies"] = {
            "database": await check_database_health(),
            "storage": await check_storage_health(),
            "cache": await check_cache_health()
        }
    
    return health_status
```

## 🔒 **Security Configuration**

### **1. Network Security**

#### **Firewall Rules**
```bash
# Allow required ports
sudo ufw allow 8000/tcp  # TAMS API
sudo ufw allow 9090/tcp  # VAST/S3
sudo ufw allow 22/tcp    # SSH (if needed)

# Enable firewall
sudo ufw enable
```

#### **Network Policies (Kubernetes)**
```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tams-network-policy
  namespace: tams
spec:
  podSelector:
    matchLabels:
      app: tams-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
```

### **2. Authentication and Authorization**

#### **API Key Authentication**
```python
# API key middleware
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_api_key(credentials = Depends(security)):
    if credentials.credentials != "your-api-key":
        raise HTTPException(status_code=403, detail="Invalid API key")
    return credentials.credentials
```

#### **JWT Authentication**
```python
# JWT authentication
from jose import JWTError, jwt
from fastapi import HTTPException, Depends

async def verify_jwt_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### **3. Data Encryption**

#### **TLS Configuration**
```python
# HTTPS configuration
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem"
    )
```

#### **Environment Variable Encryption**
```bash
# Use encrypted secrets
# For production, use your platform's secret management service
# AWS: AWS Secrets Manager
# GCP: Secret Manager
# Azure: Key Vault
# Kubernetes: Kubernetes Secrets
```

## 🚀 **Performance Optimization**

### **1. Resource Limits**

#### **Docker Resource Limits**
```yaml
# docker-compose.yml
services:
  tams-api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

#### **Kubernetes Resource Limits**
```yaml
# k8s/deployment.yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### **2. Scaling Configuration**

#### **Horizontal Pod Autoscaler**
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: tams-api-hpa
spec:
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

#### **Load Balancing**
```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
spec:
  type: LoadBalancer
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800
```

## 🔧 **Troubleshooting**

### **1. Common Issues**

#### **Connection Issues**
```bash
# Test VAST connection
python mgmt/test_diagnostics.py --check=db

# Test S3 connection
python mgmt/test_diagnostics.py --check=s3

# Check network connectivity
telnet your-vast-server 9090
telnet your-s3-server 9090
```

#### **Performance Issues**
```bash
# Check resource usage
docker stats tams-api
kubectl top pods -n tams

# Check logs for errors
docker-compose logs tams-api
kubectl logs -f deployment/tams-api -n tams
```

#### **Storage Issues**
```bash
# Check S3 bucket access
python mgmt/check_s3_direct.py

# Verify bucket permissions
aws s3 ls s3://your-bucket --endpoint-url http://your-s3-server:9090
```

### **2. Debug Mode**

#### **Enable Debug Logging**
```bash
# Set debug environment variable
export DEBUG=true
export LOG_LEVEL=DEBUG

# Restart application
docker-compose restart tams-api
# or
kubectl rollout restart deployment/tams-api -n tams
```

#### **Debug Endpoints**
```bash
# Debug information
curl http://your-api:8000/debug/info

# System status
curl http://your-api:8000/debug/status

# Performance metrics
curl http://your-api:8000/debug/performance
```

## 📚 **Additional Resources**

### **1. Documentation**
- **API Documentation**: http://your-api:8000/docs
- **Architecture Documentation**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Development Documentation**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

### **2. Support**
- **GitHub Issues**: Report bugs and request features
- **Community Discussions**: Join community discussions
- **Documentation**: Comprehensive deployment guides

### **3. Monitoring**
- **Grafana Dashboards**: Pre-configured monitoring dashboards
- **Prometheus Metrics**: Comprehensive system metrics
- **Health Checks**: Built-in health monitoring

This deployment documentation provides comprehensive guidance for deploying the TAMS API system across different environments, from local development to production Kubernetes clusters and cloud platforms.
