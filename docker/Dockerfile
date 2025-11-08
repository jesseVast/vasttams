# TAMS FastAPI Server Dockerfile
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

# Copy server requirements first for better caching
COPY src/server/requirements.txt /app/requirements.txt

# Copy private dependency wheels (vastdbmanager and vasts3)
# These are built from local GitLab packages using scripts/build_private_wheels.sh
# If wheels directory exists and contains .whl files, they will be installed
COPY wheels/ /tmp/wheels/

# Install Python dependencies
# First install private wheels if available, then install from requirements.txt
RUN pip install --no-cache-dir --upgrade pip build wheel \
    && if [ -n "$(ls -A /tmp/wheels/*.whl 2>/dev/null)" ]; then \
        echo "Installing private dependency wheels..."; \
        pip install --no-cache-dir /tmp/wheels/*.whl; \
    else \
        echo "No wheels found, will install from requirements.txt (may require GitLab auth)"; \
    fi \
    && pip install --no-cache-dir -r requirements.txt

# Copy server application code
COPY src/server /app/src/server
COPY run.py /app/run.py

# Copy management scripts (for OpenAPI generation)
COPY mgmt /app/mgmt

# Set environment variables for build
ENV PYTHONPATH=/app/src/server

# Generate OpenAPI specification
RUN python mgmt/generate_openapi.py || echo "OpenAPI generation skipped (may fail if app not fully initialized)"

# Create data directories and set permissions
RUN mkdir -p /app/vast_data /app/logs /app/temp /etc/tams \
    && chown -R tamsuser:tamsuser /app \
    && chmod -R 755 /app

# Switch to non-root user
USER tamsuser

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app/src/server
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "run.py"]
