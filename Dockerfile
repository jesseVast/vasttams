# TAMS FastAPI Application Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies and create user
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r tamsuser \
    && useradd -r -g tamsuser -s /bin/bash -d /app tamsuser

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate OpenAPI specification
RUN python generate_openapi.py

# Create data directories and set permissions
RUN mkdir -p /app/vast_data /app/logs /app/temp \
    && chown -R tamsuser:tamsuser /app \
    && chmod -R 755 /app

# Switch to non-root user
USER tamsuser

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "run.py"]