"""
Setup configuration for TAMS (Time-addressable Media Store) API

A FastAPI implementation for storing and managing time-addressable media flows
with VAST database integration.
"""

from setuptools import setup, find_packages
import os

# Read version from app/__init__.py
version = "8.0.0"

# Read README for long description
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
long_description = ""
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()

setup(
    name="vasttamsserver",
    version=version,
    author="Jesse Thaloor",
    author_email="jthaloor@vastdata.com",
    description="Time-addressable Media Store API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jesseVast/vasttams",
    package_dir={"": "."},
    packages=find_packages(where=".", exclude=["tests", "tests.*", "*.tests", "*.tests.*", "mgmt", "mgmt.*"]),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        # FastAPI and web framework
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.34.0",
        "python-multipart>=0.0.20",
        "starlette>=0.45.0",
        
        # Data validation and settings
        "pydantic>=2.11.0",
        "pydantic-settings>=2.10.0",
        "pydantic-core>=2.33.0",
        
        # Authentication and security
        "bcrypt>=4.1.0",
        "PyJWT>=2.8.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.0",
        
        # Environment and configuration
        "python-dotenv>=1.0.0",
        "click>=8.1.0",
        
        # Database and ORM
        "alembic>=1.16.0",
        "psycopg2-binary>=2.9.0",
        
        # Caching and HTTP
        "redis>=5.0.0",
        "httpx>=0.28.0",
        
        # VAST database and analytics
        "vastdb>=1.3.10",
        "ibis-framework>=9.0.0",
        "pyarrow>=16.0.0",
        "pandas>=2.3.0",
        "duckdb>=0.9.0",
        
        # VastStore dependencies
        "pymilvus>=2.5.0",
        "aioboto3>=15.0.0",
        "aiofiles>=24.0.0",
        "trino>=0.336.0",
        
        # AWS/S3 storage
        "boto3>=1.39.0",
        "botocore>=1.39.0",
        "aiobotocore>=2.24.0",
        
        # Additional utilities
        "python-dateutil>=2.9.0",
        "pytz>=2025.0",
        "deprecated>=1.2.0",
        "six>=1.16.0",
        
        # Telemetry and Observability
        "prometheus-client>=0.22.0",
        "opentelemetry-api>=1.35.0",
        "opentelemetry-sdk>=1.35.0",
        "opentelemetry-instrumentation-fastapi>=0.56b0",
        "opentelemetry-instrumentation-httpx>=0.56b0",
        "opentelemetry-instrumentation-logging>=0.56b0",
        "opentelemetry-exporter-prometheus>=0.56b0",
        "opentelemetry-exporter-jaeger>=1.21.0",
        "opentelemetry-exporter-otlp-proto-http>=1.15.0",
        "psutil>=7.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=24.0.0",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "tams=vasttamsserver.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)

