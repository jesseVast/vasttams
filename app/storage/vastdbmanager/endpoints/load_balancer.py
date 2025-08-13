"""Load balancing for VastDBManager endpoints"""

import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LoadBalancer:
    """Intelligent load balancing for VAST endpoints"""
    
    def __init__(self, endpoint_manager):
        """Initialize load balancer with endpoint manager"""
        self.endpoint_manager = endpoint_manager
        self.current_endpoint_index = 0
        self.last_round_robin = datetime.now()
        self.round_robin_interval = timedelta(seconds=1)  # Switch endpoints every second
    
    def get_endpoint(self, operation_type: str = "read", 
                     prefer_fastest: bool = True) -> Optional[str]:
        """
        Get the best endpoint for an operation
        
        Args:
            operation_type: Type of operation ('read', 'write', 'analytics')
            prefer_fastest: Whether to prefer fastest endpoints
            
        Returns:
            Selected endpoint URL
        """
        try:
            healthy_endpoints = self.endpoint_manager.get_healthy_endpoints()
            
            if not healthy_endpoints:
                logger.warning("No healthy endpoints available for load balancing")
                return None
            
            if len(healthy_endpoints) == 1:
                return healthy_endpoints[0]
            
            # Select endpoint based on operation type and strategy
            if operation_type == "read":
                return self._select_read_endpoint(healthy_endpoints, prefer_fastest)
            elif operation_type == "write":
                return self._select_write_endpoint(healthy_endpoints)
            elif operation_type == "analytics":
                return self._select_analytics_endpoint(healthy_endpoints)
            else:
                return self._select_default_endpoint(healthy_endpoints)
                
        except Exception as e:
            logger.error(f"Error in load balancer: {e}")
            # Fallback to first healthy endpoint
            healthy_endpoints = self.endpoint_manager.get_healthy_endpoints()
            return healthy_endpoints[0] if healthy_endpoints else None
    
    def _select_read_endpoint(self, healthy_endpoints: List[str], prefer_fastest: bool) -> str:
        """Select endpoint for read operations"""
        if prefer_fastest:
            # Sort by response time (fastest first)
            sorted_endpoints = sorted(
                healthy_endpoints,
                key=lambda ep: self.endpoint_manager.endpoint_health[ep].response_time
            )
            return sorted_endpoints[0]
        else:
            # Use round-robin for read distribution
            return self._round_robin_select(healthy_endpoints)
    
    def _select_write_endpoint(self, healthy_endpoints: List[str]) -> str:
        """Select endpoint for write operations"""
        # For writes, prefer endpoints with fewer errors and better reliability
        sorted_endpoints = sorted(
            healthy_endpoints,
            key=lambda ep: (
                self.endpoint_manager.endpoint_health[ep].error_count,
                self.endpoint_manager.endpoint_health[ep].response_time
            )
        )
        return sorted_endpoints[0]
    
    def _select_analytics_endpoint(self, healthy_endpoints: List[str]) -> str:
        """Select endpoint for analytics operations"""
        # Analytics operations can be distributed across endpoints
        # Use round-robin with longer intervals to avoid switching too frequently
        if datetime.now() - self.last_round_robin > timedelta(seconds=5):
            self.last_round_robin = datetime.now()
            return self._round_robin_select(healthy_endpoints)
        else:
            # Stick with current endpoint for analytics
            return self._get_current_analytics_endpoint(healthy_endpoints)
    
    def _select_default_endpoint(self, healthy_endpoints: List[str]) -> str:
        """Select endpoint using default strategy"""
        return self._round_robin_select(healthy_endpoints)
    
    def _round_robin_select(self, healthy_endpoints: List[str]) -> str:
        """Round-robin endpoint selection"""
        if not healthy_endpoints:
            return None
        
        # Update round-robin index
        self.current_endpoint_index = (self.current_endpoint_index + 1) % len(healthy_endpoints)
        selected_endpoint = healthy_endpoints[self.current_endpoint_index]
        
        logger.debug(f"Round-robin selected endpoint: {selected_endpoint}")
        return selected_endpoint
    
    def _get_current_analytics_endpoint(self, healthy_endpoints: List[str]) -> str:
        """Get current analytics endpoint or select new one"""
        if not healthy_endpoints:
            return None
        
        # Try to maintain current endpoint if it's still healthy
        if hasattr(self, '_current_analytics_endpoint') and self._current_analytics_endpoint in healthy_endpoints:
            return self._current_analytics_endpoint
        
        # Select new analytics endpoint
        self._current_analytics_endpoint = random.choice(healthy_endpoints)
        return self._current_analytics_endpoint
    
    def get_endpoint_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        try:
            healthy_endpoints = self.endpoint_manager.get_healthy_endpoints()
            
            # Calculate load distribution
            endpoint_loads = {}
            for endpoint in healthy_endpoints:
                health = self.endpoint_manager.endpoint_health[endpoint]
                endpoint_loads[endpoint] = {
                    "response_time": health.response_time,
                    "error_count": health.error_count,
                    "is_healthy": health.is_healthy,
                    "last_check": health.last_check.isoformat()
                }
            
            return {
                "total_healthy_endpoints": len(healthy_endpoints),
                "current_round_robin_index": self.current_endpoint_index,
                "round_robin_interval_seconds": self.round_robin_interval.total_seconds(),
                "endpoint_loads": endpoint_loads,
                "load_balancing_strategy": "adaptive_round_robin"
            }
            
        except Exception as e:
            logger.error(f"Error getting load balancer stats: {e}")
            return {"error": str(e)}
    
    def update_endpoint_performance(self, endpoint: str, response_time: float, success: bool):
        """Update endpoint performance metrics"""
        try:
            if success:
                self.endpoint_manager.mark_endpoint_success(endpoint, response_time)
            else:
                self.endpoint_manager.mark_endpoint_error(endpoint, f"Operation failed after {response_time:.3f}s")
                
        except Exception as e:
            logger.error(f"Error updating endpoint performance: {e}")
    
    def get_optimal_endpoint_for_query(self, query_complexity: str = "medium",
                                      estimated_rows: int = 1000) -> Optional[str]:
        """
        Get optimal endpoint based on query characteristics
        
        Args:
            query_complexity: Query complexity ('simple', 'medium', 'complex')
            estimated_rows: Estimated number of rows to process
            
        Returns:
            Optimal endpoint for the query
        """
        try:
            healthy_endpoints = self.endpoint_manager.get_healthy_endpoints()
            
            if not healthy_endpoints:
                return None
            
            if query_complexity == "simple":
                # Simple queries can use any endpoint
                return self._round_robin_select(healthy_endpoints)
            
            elif query_complexity == "medium":
                # Medium complexity: prefer endpoints with good response times
                sorted_endpoints = sorted(
                    healthy_endpoints,
                    key=lambda ep: self.endpoint_manager.endpoint_health[ep].response_time
                )
                return sorted_endpoints[0]
            
            elif query_complexity == "complex":
                # Complex queries: prefer endpoints with fewest errors
                sorted_endpoints = sorted(
                    healthy_endpoints,
                    key=lambda ep: self.endpoint_manager.endpoint_health[ep].error_count
                )
                return sorted_endpoints[0]
            
            else:
                return self._round_robin_select(healthy_endpoints)
                
        except Exception as e:
            logger.error(f"Error selecting optimal endpoint: {e}")
            return None
