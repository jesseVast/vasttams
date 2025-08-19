#!/usr/bin/env python3
"""
Comprehensive Integration Test for TAMS API

This script tests all API endpoints systematically and then runs stress tests
against the generated data.
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, List, Any
import uuid
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 30
MAX_RETRIES = 3

# Test data configuration
TEST_SOURCES_COUNT = 10
TEST_FLOWS_COUNT = 20
TEST_SEGMENTS_COUNT = 50
TEST_OBJECTS_COUNT = 100

# Setup logging
# Configure logging based on environment
env = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if env == "development" else logging.INFO
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" if env == "development" else "%(asctime)s - %(levelname)s - %(message)s"

logging.basicConfig(level=log_level, format=log_format)
logger = logging.getLogger(__name__)

class TAMSIntegrationTester:
    """Comprehensive integration tester for TAMS API"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = None
        self.test_data = {
            'sources': [],
            'flows': [],
            'segments': [],
            'objects': []
        }
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=TIMEOUT))
        return self
    
    async def __aexit__(self, self_exc_type, self_exc_val, self_exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, data: Dict = None, 
                          expected_status: int = 200, description: str = "") -> bool:
        """Make HTTP request and validate response"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == 'GET':
                async with self.session.get(url) as response:
                    status = response.status
                    content = await response.text()
            elif method.upper() == 'POST':
                async with self.session.post(url, json=data) as response:
                    status = response.status
                    content = await response.text()
            elif method.upper() == 'PUT':
                async with self.session.put(url, json=data) as response:
                    status = response.status
                    content = await response.text()
            elif method.upper() == 'DELETE':
                async with self.session.delete(url) as response:
                    status = response.status
                    content = await response.text()
            else:
                logger.error(f"Unsupported method: {method}")
                return False
            
            success = status == expected_status
            if success:
                logger.info(f"✅ {description} - {method} {endpoint} - Status: {status}")
                self.test_results['passed'] += 1
            else:
                logger.error(f"❌ {description} - {method} {endpoint} - Expected: {expected_status}, Got: {status}")
                logger.error(f"Response: {content}")
                self.test_results['failed'] += 1
            
            self.test_results['details'].append({
                'method': method,
                'endpoint': endpoint,
                'expected_status': expected_status,
                'actual_status': status,
                'success': success,
                'description': description,
                'response': content[:200] if content else ""
            })
            
            return success
            
        except Exception as e:
            logger.error(f"❌ {description} - {method} {endpoint} - Exception: {e}")
            self.test_results['failed'] += 1
            self.test_results['details'].append({
                'method': method,
                'endpoint': endpoint,
                'expected_status': expected_status,
                'actual_status': None,
                'success': False,
                'description': description,
                'response': str(e)
            })
            return False
    
    async def test_health_endpoints(self):
        """Test health and metrics endpoints"""
        logger.info("🔍 Testing Health Endpoints...")
        
        await self.make_request('GET', '/health', description="Health check")
        await self.make_request('GET', '/metrics', description="Metrics endpoint")
        await self.make_request('GET', '/', description="Root endpoint")
        await self.make_request('GET', '/openapi.json', description="OpenAPI specification")
    
    async def test_service_endpoints(self):
        """Test service-related endpoints"""
        logger.info("🔍 Testing Service Endpoints...")
        
        await self.make_request('GET', '/service', description="Service info")
        await self.make_request('GET', '/service/storage-backends', description="Storage backends")
        await self.make_request('GET', '/service/webhooks', description="Webhooks info")
    
    async def test_sources_endpoints(self):
        """Test sources endpoints"""
        logger.info("🔍 Testing Sources Endpoints...")
        
        # Test empty sources list
        await self.make_request('GET', '/sources', description="Get sources (empty)")
        
        # Test batch creation
        sources_data = []
        for i in range(TEST_SOURCES_COUNT):
            source = {
                "id": str(uuid.uuid4()),
                "format": "urn:x-nmos:format:video",
                "label": f"Test Source {i+1}",
                "description": f"Integration test source {i+1}",
                "tags": {"test": "integration", "source_id": str(i+1)}
            }
            sources_data.append(source)
        
        # Create sources in batch - API expects array directly, not wrapped
        success = await self.make_request(
            'POST', '/sources/batch', 
            data=sources_data,  # Send array directly, not wrapped in object
            expected_status=201,  # POST operations return 201 Created
            description="Create sources batch"
        )
        
        if success:
            self.test_data['sources'] = sources_data
            
            # Test individual source retrieval
            for source in sources_data[:3]:  # Test first 3
                await self.make_request(
                    'GET', f"/sources/{source['id']}", 
                    description=f"Get source {source['id']}"
                )
            
            # Test sources list (should now have data)
            await self.make_request('GET', '/sources', description="Get sources (with data)")
            
            # Test update endpoints (these expect query parameters, not body)
            for source in sources_data[:2]:  # Test first 2
                # Update label using query parameter
                await self.make_request(
                    'PUT', f"/sources/{source['id']}/label?label=Updated%20Label%20{source['id'][:8]}", 
                    expected_status=200,
                    description=f"Update source {source['id'][:8]} label"
                )
                
                # Update description using query parameter
                await self.make_request(
                    'PUT', f"/sources/{source['id']}/description?description=Updated%20Description%20{source['id'][:8]}", 
                    expected_status=200,
                    description=f"Update source {source['id'][:8]} description"
                )
                
                # Update tags using request body (not query parameter)
                updated_tags = {"test": "integration", "updated": "true", "source_id": str(source['id'][:8])}
                await self.make_request(
                    'PUT', f"/sources/{source['id']}/tags", 
                    data=updated_tags,
                    expected_status=200,
                    description=f"Update source {source['id'][:8]} tags"
                )
        else:
            logger.warning("⚠️ Sources creation failed, skipping related tests")
            self.test_results['skipped'] += 8  # Count of skipped tests
    
    async def test_flows_endpoints(self):
        """Test flows endpoints"""
        logger.info("🔍 Testing Flows Endpoints...")
        
        if not self.test_data['sources']:
            logger.warning("⚠️ No sources available, skipping flows tests")
            self.test_results['skipped'] += 13  # Count of skipped tests (removed max_bit_rate and avg_bit_rate)
            return
        
        # Test empty flows list
        await self.make_request('GET', '/flows', description="Get flows (empty)")
        
        # Test batch creation
        flows_data = []
        for i in range(TEST_FLOWS_COUNT):
            source_id = self.test_data['sources'][i % len(self.test_data['sources'])]['id']
            # Create proper VideoFlow objects with all required fields
            flow = {
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "format": "urn:x-nmos:format:video",
                "label": f"Test Flow {i+1}",
                "description": f"Integration test flow {i+1}",
                "tags": {"test": "integration", "flow_id": str(i+1)},
                # Required VideoFlow fields
                "codec": "H.264",
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {"numerator": 25, "denominator": 1},  # Fixed: TAMS object format
                # Optional fields
                "read_only": False
            }
            flows_data.append(flow)
        
        # Create flows in batch - API expects array directly, not wrapped
        success = await self.make_request(
            'POST', '/flows/batch', 
            data=flows_data,  # Send array directly, not wrapped in object
            expected_status=201,  # POST operations return 201 Created
            description="Create flows batch"
        )
        
        if success:
            self.test_data['flows'] = flows_data
            
            # Test individual flow retrieval
            for flow in flows_data[:3]:  # Test first 3
                await self.make_request(
                    'GET', f"/flows/{flow['id']}", 
                    description=f"Get flow {flow['id']}"
                )
            
            # Test flows list (should now have data)
            await self.make_request('GET', '/flows', description="Get flows (with data)")
            
            # Test update endpoints (these expect query parameters, not body)
            for flow in flows_data[:2]:  # Test first 2
                # Update label using query parameter
                await self.make_request(
                    'PUT', f"/flows/{flow['id']}/label?label=Updated%20Flow%20Label%20{flow['id'][:8]}", 
                    expected_status=200,
                    description=f"Update flow {flow['id'][:8]} label"
                )
                
                # Update description using query parameter
                await self.make_request(
                    'PUT', f"/flows/{flow['id']}/description?description=Updated%20Flow%20Description%20{flow['id'][:8]}", 
                    expected_status=200,
                    description=f"Update flow {flow['id'][:8]} description"
                )
                
                # Update tags using request body (not query parameter)
                updated_tags = {"test": "integration", "updated": "true", "flow_id": str(flow['id'][:8])}
                await self.make_request(
                    'PUT', f"/flows/{flow['id']}/tags", 
                    data=updated_tags,
                    expected_status=200,
                    description=f"Update flow {flow['id'][:8]} tags"
                )
                
                # Update other flow fields using request body (not query parameters)
                await self.make_request(
                    'PUT', f"/flows/{flow['id']}/flow_collection", 
                    data=[str(uuid.uuid4()), str(uuid.uuid4())],  # API expects array of strings, not objects
                    expected_status=200,
                    description=f"Update flow {flow['id'][:8]} flow_collection"
                )
                
                await self.make_request(
                    'PUT', f"/flows/{flow['id']}/read_only", 
                    data=False,
                    expected_status=200,
                    description=f"Update flow {flow['id'][:8]} read_only"
                )
        else:
            logger.warning("⚠️ Flows creation failed, skipping related tests")
            self.test_results['skipped'] += 13  # Count of skipped tests (removed max_bit_rate and avg_bit_rate)
    
    async def test_objects_endpoints(self):
        """Test objects endpoints"""
        logger.info("🔍 Testing Objects Endpoints...")
        
        # Test objects endpoint - only supports POST, not GET
        # Note: Objects are created and retrieved individually by ID, not as a list
        
        # Test batch creation
        objects_data = []
        for i in range(TEST_OBJECTS_COUNT):
            obj = {
                "id": str(uuid.uuid4()),  # TAMS API expects 'id', not 'object_id'
                # Only include required fields from the schema
                "referenced_by_flows": [str(uuid.uuid4())]  # TAMS API expects array of UUID strings
            }
            objects_data.append(obj)
        
        # Create objects in batch - API expects array directly, not wrapped
        success = await self.make_request(
            'POST', '/objects/batch', 
            data=objects_data,  # Send array directly, not wrapped in object
            expected_status=201,  # POST operations return 201 Created
            description="Create objects batch"
        )
        
        if success:
            self.test_data['objects'] = objects_data
            
            # Test individual object retrieval
            for obj in objects_data[:3]:  # Test first 3
                await self.make_request(
                    'GET', f"/objects/{obj['id']}",  # Use 'id' for retrieval
                    description=f"Get object {obj['id']}"
                )
        else:
            logger.warning("⚠️ Objects creation failed, skipping related tests")
            self.test_results['skipped'] += 0  # No tests skipped
    
    async def test_analytics_endpoints(self):
        """Test analytics endpoints"""
        logger.info("🔍 Testing Analytics Endpoints...")
        
        # Test analytics endpoints (may return empty results initially)
        await self.make_request('GET', '/analytics/flow-usage', description="Flow usage analytics")
        await self.make_request('GET', '/analytics/storage-usage', description="Storage usage analytics")
        await self.make_request('GET', '/analytics/time-range-analysis', description="Time range analysis")
    
    async def test_flow_delete_requests(self):
        """Test flow delete request endpoints"""
        logger.info("🔍 Testing Flow Delete Request Endpoints...")
        
        # Test empty list
        await self.make_request('GET', '/flow-delete-requests', description="Get flow delete requests (empty)")
        
        # Create a flow delete request with all required fields
        if self.test_data['flows']:
            flow_id = self.test_data['flows'][0]['id']
            delete_request = {
                "request_id": str(uuid.uuid4()),
                "flow_id": flow_id,
                "timerange": "2024-01-01T00:00:00Z/2024-12-31T23:59:59Z",
                "status": "pending",
                "created": datetime.now().isoformat() + "Z"
            }
            
            await self.make_request(
                'POST', '/flow-delete-requests', 
                data=delete_request,
                expected_status=201,
                description="Create flow delete request"
            )
            
            # Test retrieval (we'd need to get the request ID from response)
            await self.make_request('GET', '/flow-delete-requests', description="Get flow delete requests (with data)")
        else:
            logger.warning("⚠️ No flows available, skipping delete request tests")
            self.test_results['skipped'] += 2
    
    async def run_stress_test(self):
        """Run stress test against the generated data"""
        logger.info("🚀 Running Stress Test...")
        
        if not self.test_data['sources'] or not self.test_data['flows']:
            logger.warning("⚠️ Insufficient test data for stress test")
            return
        
        stress_results = {
            'concurrent_requests': 0,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_time': 0,
            'avg_response_time': 0
        }
        
        # Test concurrent reads
        start_time = time.time()
        concurrent_tasks = []
        
        # Create 50 concurrent requests
        for i in range(50):
            if i % 2 == 0:
                task = self.make_request('GET', '/sources', description=f"Stress test sources {i}")
            else:
                task = self.make_request('GET', '/flows', description=f"Stress test flows {i}")
            concurrent_tasks.append(task)
        
        # Execute concurrent requests
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        end_time = time.time()
        stress_results['total_time'] = end_time - start_time
        stress_results['concurrent_requests'] = len(concurrent_tasks)
        stress_results['total_requests'] = len(results)
        
        # Count results
        for result in results:
            if isinstance(result, Exception):
                stress_results['failed_requests'] += 1
            elif result:
                stress_results['successful_requests'] += 1
            else:
                stress_results['failed_requests'] += 1
        
        stress_results['avg_response_time'] = stress_results['total_time'] / stress_results['total_requests']
        
        # Log stress test results
        logger.info("📊 Stress Test Results:")
        logger.info(f"   Concurrent Requests: {stress_results['concurrent_requests']}")
        logger.info(f"   Total Requests: {stress_results['total_requests']}")
        logger.info(f"   Successful: {stress_results['successful_requests']}")
        logger.info(f"   Failed: {stress_results['failed_requests']}")
        logger.info(f"   Total Time: {stress_results['total_time']:.2f}s")
        logger.info(f"   Avg Response Time: {stress_results['avg_response_time']:.3f}s")
        
        return stress_results
    
    async def run_full_integration_test(self):
        """Run the complete integration test suite"""
        logger.info("🚀 Starting Full Integration Test Suite...")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Test Configuration: {TEST_SOURCES_COUNT} sources, {TEST_FLOWS_COUNT} flows, {TEST_OBJECTS_COUNT} objects")
        
        start_time = time.time()
        
        # Run all test categories
        await self.test_health_endpoints()
        await self.test_service_endpoints()
        await self.test_sources_endpoints()
        await self.test_flows_endpoints()
        await self.test_objects_endpoints()
        await self.test_analytics_endpoints()
        await self.test_flow_delete_requests()
        
        # Run stress test
        stress_results = await self.run_stress_test()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Print final results
        logger.info("=" * 60)
        logger.info("📋 INTEGRATION TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total Test Time: {total_time:.2f}s")
        logger.info(f"Tests Passed: {self.test_results['passed']}")
        logger.info(f"Tests Failed: {self.test_results['failed']}")
        logger.info(f"Tests Skipped: {self.test_results['skipped']}")
        logger.info(f"Success Rate: {(self.test_results['passed'] / (self.test_results['passed'] + self.test_results['failed'])) * 100:.1f}%")
        
        if self.test_results['failed'] > 0:
            logger.error("❌ Some tests failed. Details:")
            for detail in self.test_results['details']:
                if not detail['success']:
                    logger.error(f"   {detail['method']} {detail['endpoint']}: {detail['description']}")
        else:
            logger.info("✅ All tests passed successfully!")
        
        return self.test_results, stress_results

async def main():
    """Main function to run the integration test"""
    async with TAMSIntegrationTester() as tester:
        results, stress_results = await tester.run_full_integration_test()
        
        # Save results to file
        with open('integration_test_results.json', 'w') as f:
            json.dump({
                'test_results': results,
                'stress_results': stress_results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        logger.info("💾 Test results saved to integration_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
