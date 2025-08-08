"""
TAMS (Time-addressable Media Store) API

A comprehensive FastAPI implementation with VAST database integration
for storing and managing time-addressable media flows.

This package is organized into the following modules:
- core: Configuration, dependencies, utilities, and telemetry
- models: Pydantic data models for the API
- api: API routers and business logic
- storage: VAST database and S3 storage implementations
- auth: Authentication system for TAMS API 7.0
- analytics: Analytics and reporting functionality
"""

__version__ = "6.0"
__author__ = "TAMS Team"
__description__ = "Time-addressable Media Store API" 