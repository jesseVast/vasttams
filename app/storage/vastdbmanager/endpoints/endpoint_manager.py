"""Endpoint management for VastDBManager"""

import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class EndpointHealth:
    """Endpoint health status"""
    endpoint: str
    last_check: datetime
    is_healthy: bool
    response_time: float
    error_count: int
    last_error: Optional[str] = None


class EndpointManager:
    """Manages multiple VAST endpoints and their health"""
    
    def __init__(self, endpoints: List[str]):
        """Initialize endpoint manager with list of endpoints"""
        self.endpoints = endpoints
        self.endpoint_health: Dict[str, EndpointHealth] = {}
        self.health_check_interval = timedelta(minutes=5)
        self.last_health_check = datetime.now()
        
        # Initialize health status for all endpoints
        for endpoint in endpoints:
            self.endpoint_health[endpoint] = EndpointHealth(
                endpoint=endpoint,
                last_check=datetime.now(),
                is_healthy=True,
                response_time=0.0,
                error_count=0
            )
        
        logger.info(f"Initialized endpoint manager with {len(endpoints)} endpoints")
    
    def get_healthy_endpoints(self) -> List[str]:
        """Get list of currently healthy endpoints"""
        return [
            endpoint for endpoint, health in self.endpoint_health.items()
            if health.is_healthy
        ]
    
    def get_all_endpoints(self) -> List[str]:
        """Get all endpoints regardless of health"""
        return self.endpoints.copy()
    
    def mark_endpoint_error(self, endpoint: str, error_message: str):
        """Mark an endpoint as having an error"""
        if endpoint in self.endpoint_health:
            health = self.endpoint_health[endpoint]
            health.error_count += 1
            health.last_error = error_message
            health.last_check = datetime.now()
            
            # Mark as unhealthy after multiple errors
            if health.error_count >= 3:
                health.is_healthy = False
                logger.warning(f"Endpoint {endpoint} marked as unhealthy after {health.error_count} errors")
            
            logger.debug(f"Recorded error for endpoint {endpoint}: {error_message}")
    
    def mark_endpoint_success(self, endpoint: str, response_time: float):
        """Mark an endpoint as successful"""
        if endpoint in self.endpoint_health:
            health = self.endpoint_health[endpoint]
            health.is_healthy = True
            health.response_time = response_time
            health.last_check = datetime.now()
            health.error_count = 0
            health.last_error = None
            
            logger.debug(f"Endpoint {endpoint} marked as healthy (response time: {response_time:.3f}s)")
    
    def get_endpoint_stats(self) -> Dict[str, Any]:
        """Get statistics for all endpoints"""
        try:
            total_endpoints = len(self.endpoints)
            healthy_endpoints = len(self.get_healthy_endpoints())
            unhealthy_endpoints = total_endpoints - healthy_endpoints
            
            # Calculate average response time for healthy endpoints
            healthy_response_times = [
                health.response_time for health in self.endpoint_health.values()
                if health.is_healthy and health.response_time > 0
            ]
            avg_response_time = sum(healthy_response_times) / len(healthy_response_times) if healthy_response_times else 0
            
            # Get endpoint details
            endpoint_details = {}
            for endpoint, health in self.endpoint_health.items():
                endpoint_details[endpoint] = {
                    "is_healthy": health.is_healthy,
                    "last_check": health.last_check.isoformat(),
                    "response_time": health.response_time,
                    "error_count": health.error_count,
                    "last_error": health.last_error
                }
            
            return {
                "total_endpoints": total_endpoints,
                "healthy_endpoints": healthy_endpoints,
                "unhealthy_endpoints": unhealthy_endpoints,
                "health_percentage": (healthy_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0,
                "avg_response_time": avg_response_time,
                "endpoints": endpoint_details
            }
            
        except Exception as e:
            logger.error(f"Error getting endpoint stats: {e}")
            return {"error": str(e)}
    
    def should_perform_health_check(self) -> bool:
        """Check if it's time to perform a health check"""
        return datetime.now() - self.last_health_check > self.health_check_interval
    
    def update_health_check_time(self):
        """Update the last health check time"""
        self.last_health_check = datetime.now()
    
    def get_endpoint_for_operation(self, operation_type: str = "read") -> Optional[str]:
        """Get an appropriate endpoint for a specific operation"""
        healthy_endpoints = self.get_healthy_endpoints()
        
        if not healthy_endpoints:
            logger.warning("No healthy endpoints available")
            return None
        
        # For now, use round-robin selection
        # This could be enhanced with load balancing logic
        if operation_type == "read":
            # Prefer endpoints with lower response times for reads
            healthy_endpoints.sort(key=lambda ep: self.endpoint_health[ep].response_time)
        elif operation_type == "write":
            # For writes, prefer endpoints with fewer errors
            healthy_endpoints.sort(key=lambda ep: self.endpoint_health[ep].error_count)
        
        return healthy_endpoints[0] if healthy_endpoints else None
    
    def add_endpoint(self, endpoint: str):
        """Add a new endpoint to the manager"""
        if endpoint not in self.endpoints:
            self.endpoints.append(endpoint)
            self.endpoint_health[endpoint] = EndpointHealth(
                endpoint=endpoint,
                last_check=datetime.now(),
                is_healthy=True,
                response_time=0.0,
                error_count=0
            )
            logger.info(f"Added new endpoint: {endpoint}")
    
    def remove_endpoint(self, endpoint: str):
        """Remove an endpoint from the manager"""
        if endpoint in self.endpoints:
            self.endpoints.remove(endpoint)
            if endpoint in self.endpoint_health:
                del self.endpoint_health[endpoint]
            logger.info(f"Removed endpoint: {endpoint}")
    
    def reset_endpoint_health(self, endpoint: str):
        """Reset health status for an endpoint"""
        if endpoint in self.endpoint_health:
            health = self.endpoint_health[endpoint]
            health.is_healthy = True
            health.error_count = 0
            health.last_error = None
            health.response_time = 0.0
            health.last_check = datetime.now()
            logger.info(f"Reset health status for endpoint: {endpoint}")
