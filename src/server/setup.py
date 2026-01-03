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
    project_urls={
        "Homepage": "https://github.com/jesseVast/vasttams",
        "Documentation": "https://github.com/jesseVast/vasttams",
        "Repository": "https://github.com/jesseVast/vasttams",
    },
    package_dir={"": "."},
    packages=find_packages(where=".", exclude=["tests", "tests.*", "*.tests", "*.tests.*", "mgmt", "mgmt.*"]),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        # FastAPI and web framework
        # https://pypi.org/project/fastapi/
        "fastapi>=0.115.0",
        # https://pypi.org/project/uvicorn/
        "uvicorn[standard]>=0.34.0",
        # https://pypi.org/project/python-multipart/
        "python-multipart>=0.0.20",
        # https://pypi.org/project/starlette/
        "starlette>=0.45.0",
        
        # Data validation and settings
        # https://pypi.org/project/pydantic/
        "pydantic>=2.11.0",
        # https://pypi.org/project/pydantic-settings/
        "pydantic-settings>=2.10.0",
        # https://pypi.org/project/pydantic-core/
        "pydantic-core>=2.33.0",
        
        # Authentication and security
        # https://pypi.org/project/bcrypt/
        "bcrypt>=4.1.0",
        # https://pypi.org/project/PyJWT/
        "PyJWT>=2.8.0",
        # https://pypi.org/project/python-jose/
        "python-jose[cryptography]>=3.3.0",
        # https://pypi.org/project/passlib/
        "passlib[bcrypt]>=1.7.0",
        
        # Environment and configuration
        # https://pypi.org/project/python-dotenv/
        "python-dotenv>=1.0.0",
        # https://pypi.org/project/click/
        "click>=8.1.0",
        
        # Database and ORM
        # https://pypi.org/project/alembic/
        "alembic>=1.16.0",
        # https://pypi.org/project/psycopg2-binary/
        "psycopg2-binary>=2.9.0",
        
        # Caching and HTTP
        # https://pypi.org/project/redis/
        "redis>=5.0.0",
        # https://pypi.org/project/httpx/
        "httpx>=0.28.0",
        
        # VAST database and analytics
        # https://pypi.org/project/vastdb/
        "vastdb>=1.3.10",
        # https://pypi.org/project/ibis-framework/
        "ibis-framework>=9.0.0",
        # https://pypi.org/project/pyarrow/
        "pyarrow>=16.0.0",
        # https://pypi.org/project/pandas/
        "pandas>=2.3.0",
        # https://pypi.org/project/duckdb/
        "duckdb>=0.9.0",
        
        # VastStore dependencies
        # https://pypi.org/project/pymilvus/
        "pymilvus>=2.5.0",
        # https://pypi.org/project/aioboto3/
        "aioboto3>=15.0.0",
        # https://pypi.org/project/aiofiles/
        "aiofiles>=24.0.0",
        # https://pypi.org/project/trino/
        "trino>=0.336.0",
        
        # AWS/S3 storage
        # https://pypi.org/project/boto3/
        "boto3>=1.39.0",
        # https://pypi.org/project/botocore/
        "botocore>=1.39.0",
        # https://pypi.org/project/aiobotocore/
        "aiobotocore>=2.24.0",
        
        # Additional utilities
        # https://pypi.org/project/python-dateutil/
        "python-dateutil>=2.9.0",
        # https://pypi.org/project/pytz/
        "pytz>=2025.0",
        # https://pypi.org/project/deprecated/
        "deprecated>=1.2.0",
        # https://pypi.org/project/six/
        "six>=1.16.0",
        
        # Telemetry and Observability
        # https://pypi.org/project/prometheus-client/
        "prometheus-client>=0.22.0",
        # https://pypi.org/project/opentelemetry-api/
        "opentelemetry-api>=1.35.0",
        # https://pypi.org/project/opentelemetry-sdk/
        "opentelemetry-sdk>=1.35.0",
        # https://pypi.org/project/opentelemetry-instrumentation-fastapi/
        "opentelemetry-instrumentation-fastapi>=0.56b0",
        # https://pypi.org/project/opentelemetry-instrumentation-httpx/
        "opentelemetry-instrumentation-httpx>=0.56b0",
        # https://pypi.org/project/opentelemetry-instrumentation-logging/
        "opentelemetry-instrumentation-logging>=0.56b0",
        # https://pypi.org/project/opentelemetry-exporter-prometheus/
        "opentelemetry-exporter-prometheus>=0.56b0",
        # https://pypi.org/project/opentelemetry-exporter-jaeger/
        "opentelemetry-exporter-jaeger>=1.21.0",
        # https://pypi.org/project/opentelemetry-exporter-otlp-proto-http/
        "opentelemetry-exporter-otlp-proto-http>=1.15.0",
        # https://pypi.org/project/psutil/
        "psutil>=7.0.0",
        
        # Private dependencies (available from GitHub releases)
        # vastdbmanager>=2.0.0 - https://github.com/jesseVast/vast/releases/download/vastdbmanager-v2.0.0/vastdbmanager-2.0.0-py3-none-any.whl
        # vasts3>=1.1.18 - https://github.com/jesseVast/vast/releases/download/vasts3-1.1.18/vasts3-1.1.18-py3-none-any.whl
        # aifuel>=0.3.3 - https://github.com/jesseVast/vast/releases/download/aifuel-v0.3.3/aifuel-0.3.3-py3-none-any.whl
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

