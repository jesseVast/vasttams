"""
Telemetry and Observability Module for TAMS API

This module provides comprehensive telemetry capabilities including:
- Prometheus metrics for monitoring and alerting
- OpenTelemetry tracing for distributed tracing
- Structured logging with correlation IDs
- Performance monitoring and business metrics
- Health check enhancements
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timezone

from prometheus_client import (
    Counter, Histogram, Gauge, Summary, 
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, multiprocess
)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from fastapi import Request, Response
from fastapi.responses import Response as FastAPIResponse

logger = logging.getLogger(__name__)

# Prometheus Metrics
class TAMSMetrics:
    """TAMS-specific Prometheus metrics"""
    
    def __init__(self):
        # HTTP metrics
        self.http_requests_total = Counter(
            'tams_http_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status_code']
        )
        
        self.http_request_duration_seconds = Histogram(
            'tams_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        # Business metrics
        self.sources_total = Gauge(
            'tams_sources_total',
            'Total number of sources'
        )
        
        self.flows_total = Gauge(
            'tams_flows_total',
            'Total number of flows'
        )
        
        self.segments_total = Gauge(
            'tams_segments_total',
            'Total number of flow segments'
        )
        
        self.storage_bytes_total = Gauge(
            'tams_storage_bytes_total',
            'Total storage usage in bytes'
        )
        
        # Operation metrics
        self.flow_operations_total = Counter(
            'tams_flow_operations_total',
            'Total number of flow operations',
            ['operation', 'format', 'status']
        )
        
        self.segment_operations_total = Counter(
            'tams_segment_operations_total',
            'Total number of segment operations',
            ['operation', 'status']
        )
        
        self.source_operations_total = Counter(
            'tams_source_operations_total',
            'Total number of source operations',
            ['operation', 'format', 'status']
        )
        
        # Error metrics
        self.errors_total = Counter(
            'tams_errors_total',
            'Total number of errors',
            ['type', 'endpoint']
        )
        
        # Performance metrics
        self.vast_query_duration_seconds = Histogram(
            'tams_vast_query_duration_seconds',
            'VAST database query duration in seconds',
            ['query_type'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
        )
        
        self.s3_operation_duration_seconds = Histogram(
            'tams_s3_operation_duration_seconds',
            'S3 operation duration in seconds',
            ['operation'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        # System metrics
        self.active_connections = Gauge(
            'tams_active_connections',
            'Number of active database connections'
        )
        
        self.memory_usage_bytes = Gauge(
            'tams_memory_usage_bytes',
            'Memory usage in bytes'
        )

# Global metrics instance
metrics = TAMSMetrics()

class TelemetryManager:
    """Manages telemetry and observability for TAMS API"""
    
    def __init__(self):
        self.tracer_provider = None
        self.tracer = None
        self.is_initialized = False
        
    def initialize(self, service_name: str = "tams-api", service_version: str = "6.0.0"):
        """Initialize telemetry components"""
        if self.is_initialized:
            return
            
        # Initialize OpenTelemetry
        self._setup_opentelemetry(service_name, service_version)
        
        # Initialize logging instrumentation
        LoggingInstrumentor().instrument()
        
        self.is_initialized = True
        logger.info("Telemetry initialized successfully")
    
    def _setup_opentelemetry(self, service_name: str, service_version: str):
        """Setup OpenTelemetry tracing"""
        # Create resource
        resource = Resource.create({
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": "production"
        })
        
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Add span processors
        # Prometheus metrics reader
        metric_reader = PrometheusMetricReader()
        self.tracer_provider.add_metric_reader(metric_reader)
        
        # Jaeger exporter (if configured)
        jaeger_endpoint = self._get_jaeger_endpoint()
        if jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name=jaeger_endpoint.split(':')[0],
                agent_port=int(jaeger_endpoint.split(':')[1])
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )
        
        # OTLP exporter (if configured)
        otlp_endpoint = self._get_otlp_endpoint()
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
        
        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        self.tracer = trace.get_tracer(__name__)
    
    def _get_jaeger_endpoint(self) -> Optional[str]:
        """Get Jaeger endpoint from environment"""
        import os
        return os.getenv("JAEGER_ENDPOINT")
    
    def _get_otlp_endpoint(self) -> Optional[str]:
        """Get OTLP endpoint from environment"""
        import os
        return os.getenv("OTLP_ENDPOINT")
    
    def instrument_fastapi(self, app):
        """Instrument FastAPI application with OpenTelemetry"""
        if not self.is_initialized:
            self.initialize()
        
        FastAPIInstrumentor.instrument_app(app)
    
    def get_tracer(self):
        """Get the OpenTelemetry tracer"""
        if not self.is_initialized:
            self.initialize()
        return self.tracer
    
    def record_http_metrics(self, request: Request, response: Response, duration: float):
        """Record HTTP request metrics"""
        method = request.method
        endpoint = request.url.path
        status_code = response.status_code
        
        # Record request count
        metrics.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        # Record request duration
        metrics.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        # Record errors
        if status_code >= 400:
            metrics.errors_total.labels(
                type="http_error",
                endpoint=endpoint
            ).inc()
    
    def record_business_metrics(self, metrics_data: Dict[str, Any]):
        """Record business metrics"""
        if 'sources_count' in metrics_data:
            metrics.sources_total.set(metrics_data['sources_count'])
        
        if 'flows_count' in metrics_data:
            metrics.flows_total.set(metrics_data['flows_count'])
        
        if 'segments_count' in metrics_data:
            metrics.segments_total.set(metrics_data['segments_count'])
        
        if 'storage_bytes' in metrics_data:
            metrics.storage_bytes_total.set(metrics_data['storage_bytes'])
    
    def record_operation_metrics(self, operation: str, entity_type: str, 
                               format_type: str = None, status: str = "success"):
        """Record operation metrics"""
        if entity_type == "flow":
            metrics.flow_operations_total.labels(
                operation=operation,
                format=format_type or "unknown",
                status=status
            ).inc()
        elif entity_type == "segment":
            metrics.segment_operations_total.labels(
                operation=operation,
                status=status
            ).inc()
        elif entity_type == "source":
            metrics.source_operations_total.labels(
                operation=operation,
                format=format_type or "unknown",
                status=status
            ).inc()
    
    def record_performance_metrics(self, operation: str, duration: float, 
                                 operation_type: str = "vast"):
        """Record performance metrics"""
        if operation_type == "vast":
            metrics.vast_query_duration_seconds.labels(
                query_type=operation
            ).observe(duration)
        elif operation_type == "s3":
            metrics.s3_operation_duration_seconds.labels(
                operation=operation
            ).observe(duration)
    
    def record_error(self, error_type: str, endpoint: str, error_message: str = None):
        """Record error metrics"""
        metrics.errors_total.labels(
            type=error_type,
            endpoint=endpoint
        ).inc()
        
        if error_message:
            logger.error(f"Error recorded: {error_type} at {endpoint}: {error_message}")

# Global telemetry manager
telemetry_manager = TelemetryManager()

# Decorators for easy telemetry integration
def trace_operation(operation_name: str):
    """Decorator to trace operations with OpenTelemetry"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = telemetry_manager.get_tracer()
            with tracer.start_as_current_span(operation_name) as span:
                try:
                    start_time = time.time()
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Record performance metrics
                    telemetry_manager.record_performance_metrics(
                        operation_name, duration
                    )
                    
                    span.set_attribute("duration", duration)
                    span.set_attribute("status", "success")
                    return result
                    
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator

def monitor_operation(operation: str, entity_type: str, format_type: str = None):
    """Decorator to monitor operations with metrics"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                telemetry_manager.record_operation_metrics(
                    operation, entity_type, format_type, "success"
                )
                return result
            except Exception as e:
                telemetry_manager.record_operation_metrics(
                    operation, entity_type, format_type, "error"
                )
                telemetry_manager.record_error(
                    f"{entity_type}_operation_error", 
                    operation, 
                    str(e)
                )
                raise
        return wrapper
    return decorator

# Middleware for HTTP request telemetry
async def telemetry_middleware(request: Request, call_next):
    """Middleware to add telemetry to HTTP requests"""
    # Generate correlation ID
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    # Add correlation ID to headers
    request.headers.__dict__["_list"].append(
        (b"x-correlation-id", correlation_id.encode())
    )
    
    # Start timing
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Record metrics
    telemetry_manager.record_http_metrics(request, response, duration)
    
    # Add correlation ID to response headers
    response.headers["x-correlation-id"] = correlation_id
    response.headers["x-request-duration"] = str(duration)
    
    return response

# Prometheus metrics endpoint
def metrics_endpoint():
    """Generate Prometheus metrics"""
    return FastAPIResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# Enhanced health check
def enhanced_health_check():
    """Enhanced health check with metrics"""
    import psutil
    
    # Get system metrics
    memory_info = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Update system metrics
    metrics.memory_usage_bytes.set(memory_info.used)
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "6.0.0",
        "system": {
            "memory_usage_bytes": memory_info.used,
            "memory_total_bytes": memory_info.total,
            "cpu_percent": cpu_percent,
            "uptime_seconds": time.time() - psutil.boot_time()
        },
        "telemetry": {
            "tracing_enabled": telemetry_manager.is_initialized,
            "metrics_enabled": True
        }
    }
    
    return health_status 