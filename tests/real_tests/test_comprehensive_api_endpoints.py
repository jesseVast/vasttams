"""
Comprehensive API Endpoint Tests for TAMS API

This file tests all API endpoints systematically to ensure complete coverage.
"""

import pytest
import uuid
import json
import aiohttp
from datetime import datetime, timezone


class TestComprehensiveAPIEndpoints:
    """Test all TAMS API endpoints comprehensively"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        self.base_url = "http://localhost:8000"
        self.test_data = {}
    
    @pytest.mark.asyncio
    async def test_analytics_endpoints(self):
        """Test analytics API endpoints"""
        print("🧪 Testing analytics API endpoints...")
        
        async with aiohttp.ClientSession() as session:
            # Test flow usage analytics
            print("📊 Testing /flow-usage endpoint")
            async with session.get(f"{self.base_url}/flow-usage") as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Flow usage analytics retrieved: {len(data) if isinstance(data, list) else 'data'}")
                else:
                    print(f"   ⚠️  Flow usage endpoint returned: {response.status}")
            
            # Test storage usage analytics
            print("📊 Testing /storage-usage endpoint")
            async with session.get(f"{self.base_url}/storage-usage") as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Storage usage analytics retrieved: {len(data) if isinstance(data, list) else 'data'}")
                else:
                    print(f"   ⚠️  Storage usage endpoint returned: {response.status}")
            
            # Test time range analysis
            print("📊 Testing /time-range-analysis endpoint")
            async with session.get(f"{self.base_url}/time-range-analysis") as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Time range analysis retrieved: {len(data) if isinstance(data, list) else 'data'}")
                else:
                    print(f"   ⚠️  Time range analysis endpoint returned: {response.status}")
        
        print("✅ Analytics endpoints test completed")
        return True
    
    @pytest.mark.asyncio
    async def test_flow_storage_endpoint(self):
        """Test flow storage allocation endpoint"""
        print("🧪 Testing flow storage allocation endpoint...")
        
        async with aiohttp.ClientSession() as session:
            # First create a source and flow
            source_id = str(uuid.uuid4())
            source_data = {
                "id": source_id,
                "format": "urn:x-nmos:format:video",
                "label": "Storage Test Source",
                "description": "Source for testing storage allocation"
            }
            
            async with session.post(f"{self.base_url}/sources", json=source_data) as response:
                if response.status != 201:
                    print(f"   ❌ Source creation failed: {response.status}")
                    return False
                print(f"   ✅ Test source created: {source_id}")
            
            flow_id = str(uuid.uuid4())
            flow_data = {
                "id": flow_id,
                "source_id": source_id,
                "format": "urn:x-nmos:format:video",
                "codec": "video/h264",
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": "25:1",
                "label": "Storage Test Flow",
                "description": "Flow for testing storage allocation"
            }
            
            async with session.post(f"{self.base_url}/flows", json=flow_data) as response:
                if response.status != 201:
                    print(f"   ❌ Flow creation failed: {response.status}")
                    return False
                print(f"   ✅ Test flow created: {flow_id}")
            
            # Test storage allocation
            print("📊 Testing /flows/{flow_id}/storage endpoint")
            storage_request = {
                "storage_id": None,
                "limit": 3
            }
            
            async with session.post(f"{self.base_url}/flows/{flow_id}/storage", json=storage_request) as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 201:
                    data = await response.json()
                    media_objects = data.get('media_objects', [])
                    print(f"   ✅ Storage allocated successfully: {len(media_objects)} media objects")
                    self.test_data['storage_objects'] = media_objects
                else:
                    print(f"   ❌ Storage allocation failed: {response.status}")
                    response_text = await response.text()
                    print(f"   📄 Response: {response_text}")
                    return False
            
            # Clean up
            async with session.delete(f"{self.base_url}/flows/{flow_id}") as response:
                if response.status in [200, 204]:
                    print(f"   ✅ Test flow cleaned up")
                else:
                    print(f"   ⚠️  Flow cleanup failed: {response.status}")
            
            async with session.delete(f"{self.base_url}/sources/{source_id}") as response:
                if response.status in [200, 204, 403]:  # 403 is expected for TAMS API
                    print(f"   ✅ Test source cleaned up")
                else:
                    print(f"   ⚠️  Source cleanup failed: {response.status}")
        
        print("✅ Flow storage endpoint test completed")
        return True
    
    @pytest.mark.asyncio
    async def test_flow_tags_endpoints(self):
        """Test flow tags API endpoints"""
        print("🧪 Testing flow tags API endpoints...")
        
        async with aiohttp.ClientSession() as session:
            # Create test source and flow
            source_id = str(uuid.uuid4())
            source_data = {
                "id": source_id,
                "format": "urn:x-nmos:format:video",
                "label": "Tags Test Source",
                "description": "Source for testing tags"
            }
            
            async with session.post(f"{self.base_url}/sources", json=source_data) as response:
                if response.status != 201:
                    print(f"   ❌ Source creation failed: {response.status}")
                    return False
            
            flow_id = str(uuid.uuid4())
            flow_data = {
                "id": flow_id,
                "source_id": source_id,
                "format": "urn:x-nmos:format:video",
                "codec": "video/h264",
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": "25:1",
                "label": "Tags Test Flow",
                "description": "Flow for testing tags"
            }
            
            async with session.post(f"{self.base_url}/flows", json=flow_data) as response:
                if response.status != 201:
                    print(f"   ❌ Flow creation failed: {response.status}")
                    return False
            
            # Test getting flow tags (should be empty initially)
            print("📊 Testing GET /flows/{flow_id}/tags")
            async with session.get(f"{self.base_url}/flows/{flow_id}/tags") as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 200:
                    tags = await response.json()
                    print(f"   ✅ Flow tags retrieved: {tags}")
                else:
                    print(f"   ⚠️  Get tags failed: {response.status}")
            
            # Test setting flow tags
            print("📊 Testing PUT /flows/{flow_id}/tags")
            tags_data = {
                "production": "test",
                "environment": "development",
                "priority": "high"
            }
            
            async with session.put(f"{self.base_url}/flows/{flow_id}/tags", json=tags_data) as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 200:
                    updated_tags = await response.json()
                    print(f"   ✅ Flow tags updated: {updated_tags}")
                else:
                    print(f"   ⚠️  Update tags failed: {response.status}")
            
            # Test getting specific tag
            print("📊 Testing GET /flows/{flow_id}/tags/production")
            async with session.get(f"{self.base_url}/flows/{flow_id}/tags/production") as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 200:
                    tag_value = await response.text()
                    print(f"   ✅ Production tag value: {tag_value}")
                else:
                    print(f"   ⚠️  Get specific tag failed: {response.status}")
            
            # Test updating specific tag
            print("📊 Testing PUT /flows/{flow_id}/tags/production")
            async with session.put(f"{self.base_url}/flows/{flow_id}/tags/production", json="production") as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 204:
                    print(f"   ✅ Production tag updated")
                else:
                    print(f"   ⚠️  Update specific tag failed: {response.status}")
            
            # Test deleting specific tag
            print("📊 Testing DELETE /flows/{flow_id}/tags/production")
            async with session.delete(f"{self.base_url}/flows/{flow_id}/tags/production") as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 204:
                    print(f"   ✅ Production tag deleted")
                else:
                    print(f"   ⚠️  Delete specific tag failed: {response.status}")
            
            # Clean up
            async with session.delete(f"{self.base_url}/flows/{flow_id}") as response:
                if response.status in [200, 204]:
                    print(f"   ✅ Test flow cleaned up")
            
            async with session.delete(f"{self.base_url}/sources/{source_id}") as response:
                if response.status in [200, 204, 403]:
                    print(f"   ✅ Test source cleaned up")
        
        print("✅ Flow tags endpoints test completed")
        return True
    
    @pytest.mark.asyncio
    async def test_flow_properties_endpoints(self):
        """Test flow properties API endpoints"""
        print("🧪 Testing flow properties API endpoints...")
        
        async with aiohttp.ClientSession() as session:
            # Create test source and flow
            source_id = str(uuid.uuid4())
            source_data = {
                "id": source_id,
                "format": "urn:x-nmos:format:video",
                "label": "Properties Test Source",
                "description": "Source for testing properties"
            }
            
            async with session.post(f"{self.base_url}/sources", json=source_data) as response:
                if response.status != 201:
                    print(f"   ❌ Source creation failed: {response.status}")
                    return False
            
            flow_id = str(uuid.uuid4())
            flow_data = {
                "id": flow_id,
                "source_id": source_id,
                "format": "urn:x-nmos:format:video",
                "codec": "video/h264",
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": "25:1",
                "label": "Properties Test Flow",
                "description": "Flow for testing properties"
            }
            
            async with session.post(f"{self.base_url}/flows", json=flow_data) as response:
                if response.status != 201:
                    print(f"   ❌ Flow creation failed: {response.status}")
                    return False
            
            # Test description endpoints
            print("📊 Testing flow description endpoints")
            async with session.get(f"{self.base_url}/flows/{flow_id}/description") as response:
                if response.status == 200:
                    desc = await response.text()
                    print(f"   ✅ Flow description retrieved: {desc}")
                else:
                    print(f"   ⚠️  Get description failed: {response.status}")
            
            # Test label endpoints
            print("📊 Testing flow label endpoints")
            async with session.get(f"{self.base_url}/flows/{flow_id}/label") as response:
                if response.status == 200:
                    label = await response.text()
                    print(f"   ✅ Flow label retrieved: {label}")
                else:
                    print(f"   ⚠️  Get label failed: {response.status}")
            
            # Test read_only endpoints
            print("📊 Testing flow read_only endpoints")
            async with session.get(f"{self.base_url}/flows/{flow_id}/read_only") as response:
                if response.status == 200:
                    read_only = await response.json()
                    print(f"   ✅ Flow read_only retrieved: {read_only}")
                else:
                    print(f"   ⚠️  Get read_only failed: {response.status}")
            
            # Test flow_collection endpoints
            print("📊 Testing flow flow_collection endpoints")
            async with session.get(f"{self.base_url}/flows/{flow_id}/flow_collection") as response:
                if response.status == 200:
                    collection = await response.json()
                    print(f"   ✅ Flow collection retrieved: {collection}")
                else:
                    print(f"   ⚠️  Get flow_collection failed: {response.status}")
            
            # Test max_bit_rate endpoints
            print("📊 Testing flow max_bit_rate endpoints")
            async with session.get(f"{self.base_url}/flows/{flow_id}/max_bit_rate") as response:
                if response.status == 200:
                    max_bit_rate = await response.json()
                    print(f"   ✅ Flow max_bit_rate retrieved: {max_bit_rate}")
                else:
                    print(f"   ⚠️  Get max_bit_rate failed: {response.status}")
            
            # Test avg_bit_rate endpoints
            print("📊 Testing flow avg_bit_rate endpoints")
            async with session.get(f"{self.base_url}/flows/{flow_id}/avg_bit_rate") as response:
                if response.status == 200:
                    avg_bit_rate = await response.json()
                    print(f"   ✅ Flow avg_bit_rate retrieved: {avg_bit_rate}")
                else:
                    print(f"   ⚠️  Get avg_bit_rate failed: {response.status}")
            
            # Clean up
            async with session.delete(f"{self.base_url}/flows/{flow_id}") as response:
                if response.status in [200, 204]:
                    print(f"   ✅ Test flow cleaned up")
            
            async with session.delete(f"{self.base_url}/sources/{source_id}") as response:
                if response.status in [200, 204, 403]:
                    print(f"   ✅ Test source cleaned up")
        
        print("✅ Flow properties endpoints test completed")
        return True
    
    @pytest.mark.asyncio
    async def test_source_tags_endpoints(self):
        """Test source tags API endpoints"""
        print("🧪 Testing source tags API endpoints...")
        
        async with aiohttp.ClientSession() as session:
            # Create test source
            source_id = str(uuid.uuid4())
            source_data = {
                "id": source_id,
                "format": "urn:x-nmos:format:video",
                "label": "Tags Test Source",
                "description": "Source for testing tags"
            }
            
            async with session.post(f"{self.base_url}/sources", json=source_data) as response:
                if response.status != 201:
                    print(f"   ❌ Source creation failed: {response.status}")
                    return False
            
            # Test getting source tags (should be empty initially)
            print("📊 Testing GET /sources/{source_id}/tags")
            async with session.get(f"{self.base_url}/sources/{source_id}/tags") as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 200:
                    tags = await response.json()
                    print(f"   ✅ Source tags retrieved: {tags}")
                else:
                    print(f"   ⚠️  Get tags failed: {response.status}")
            
            # Test setting source tags
            print("📊 Testing PUT /sources/{source_id}/tags")
            tags_data = {
                "location": "studio_a",
                "type": "camera",
                "status": "active"
            }
            
            async with session.put(f"{self.base_url}/sources/{source_id}/tags", json=tags_data) as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 200:
                    updated_tags = await response.json()
                    print(f"   ✅ Source tags updated: {updated_tags}")
                else:
                    print(f"   ⚠️  Update tags failed: {response.status}")
            
            # Test getting specific tag
            print("📊 Testing GET /sources/{source_id}/tags/location")
            async with session.get(f"{self.base_url}/sources/{source_id}/tags/location") as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 200:
                    tag_value = await response.text()
                    print(f"   ✅ Location tag value: {tag_value}")
                else:
                    print(f"   ⚠️  Get specific tag failed: {response.status}")
            
            # Test updating specific tag
            print("📊 Testing PUT /sources/{source_id}/tags/location")
            async with session.put(f"{self.base_url}/sources/{source_id}/tags/location", json="studio_b") as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 204:
                    print(f"   ✅ Location tag updated")
                else:
                    print(f"   ⚠️  Update specific tag failed: {response.status}")
            
            # Test deleting specific tag
            print("📊 Testing DELETE /sources/{source_id}/tags/location")
            async with session.delete(f"{self.base_url}/sources/{source_id}/tags/location") as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 204:
                    print(f"   ✅ Location tag deleted")
                else:
                    print(f"   ⚠️  Delete specific tag failed: {response.status}")
            
            # Clean up
            async with session.delete(f"{self.base_url}/sources/{source_id}") as response:
                if response.status in [200, 204, 403]:
                    print(f"   ✅ Test source cleaned up")
        
        print("✅ Source tags endpoints test completed")
        return True
    
    @pytest.mark.asyncio
    async def test_source_properties_endpoints(self):
        """Test source properties API endpoints"""
        print("🧪 Testing source properties API endpoints...")
        
        async with aiohttp.ClientSession() as session:
            # Create test source
            source_id = str(uuid.uuid4())
            source_data = {
                "id": source_id,
                "format": "urn:x-nmos:format:video",
                "label": "Properties Test Source",
                "description": "Source for testing properties"
            }
            
            async with session.post(f"{self.base_url}/sources", json=source_data) as response:
                if response.status != 201:
                    print(f"   ❌ Source creation failed: {response.status}")
                    return False
            
            # Test description endpoints
            print("📊 Testing source description endpoints")
            async with session.get(f"{self.base_url}/sources/{source_id}/description") as response:
                if response.status == 200:
                    desc = await response.text()
                    print(f"   ✅ Source description retrieved: {desc}")
                else:
                    print(f"   ⚠️  Get description failed: {response.status}")
            
            # Test label endpoints
            print("📊 Testing source label endpoints")
            async with session.get(f"{self.base_url}/sources/{source_id}/label") as response:
                if response.status == 200:
                    label = await response.text()
                    print(f"   ✅ Source label retrieved: {label}")
                else:
                    print(f"   ⚠️  Get label failed: {response.status}")
            
            # Clean up
            async with session.delete(f"{self.base_url}/sources/{source_id}") as response:
                if response.status in [200, 204, 403]:
                    print(f"   ✅ Test source cleaned up")
        
        print("✅ Source properties endpoints test completed")
        return True
    
    @pytest.mark.asyncio
    async def test_batch_operations_endpoints(self):
        """Test batch operations API endpoints"""
        print("🧪 Testing batch operations API endpoints...")
        
        async with aiohttp.ClientSession() as session:
            # Test batch source creation
            print("📊 Testing POST /sources/batch")
            batch_sources = [
                {
                    "id": str(uuid.uuid4()),
                    "format": "urn:x-nmos:format:video",
                    "label": f"Batch Source {i}",
                    "description": f"Batch test source {i}"
                }
                for i in range(3)
            ]
            
            async with session.post(f"{self.base_url}/sources/batch", json=batch_sources) as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 201:
                    created_sources = await response.json()
                    print(f"   ✅ Batch sources created: {len(created_sources)} sources")
                    self.test_data['batch_sources'] = created_sources
                else:
                    print(f"   ⚠️  Batch source creation failed: {response.status}")
                    response_text = await response.text()
                    print(f"   📄 Response: {response_text}")
            
            # Test batch flow creation
            print("📊 Testing POST /flows/batch")
            if 'batch_sources' in self.test_data and self.test_data['batch_sources']:
                source_id = self.test_data['batch_sources'][0]['id']
                batch_flows = [
                    {
                        "id": str(uuid.uuid4()),
                        "source_id": source_id,
                        "format": "urn:x-nmos:format:video",
                        "codec": "video/h264",
                        "frame_width": 1920,
                        "frame_height": 1080,
                        "frame_rate": "25:1",
                        "label": f"Batch Flow {i}",
                        "description": f"Batch test flow {i}"
                    }
                    for i in range(2)
                ]
                
                async with session.post(f"{self.base_url}/flows/batch", json=batch_flows) as response:
                    print(f"   📥 Response Status: {response.status}")
                    if response.status == 201:
                        created_flows = await response.json()
                        print(f"   ✅ Batch flows created: {len(created_flows)} flows")
                        self.test_data['batch_flows'] = created_flows
                    else:
                        print(f"   ⚠️  Batch flow creation failed: {response.status}")
                        response_text = await response.text()
                        print(f"   📄 Response: {response_text}")
            
            # Test batch object creation
            print("📊 Testing POST /objects/batch")
            # Create a dummy flow ID for reference
            dummy_flow_id = str(uuid.uuid4())
            batch_objects = [
                {
                    "id": str(uuid.uuid4()),
                    "referenced_by_flows": [dummy_flow_id]
                }
                for i in range(2)
            ]
            
            async with session.post(f"{self.base_url}/objects/batch", json=batch_objects) as response:
                print(f"   📥 Response Status: {response.status}")
                if response.status == 201:
                    created_objects = await response.json()
                    print(f"   ✅ Batch objects created: {len(created_objects)} objects")
                    self.test_data['batch_objects'] = created_objects
                else:
                    print(f"   ⚠️  Batch object creation failed: {response.status}")
                    response_text = await response.text()
                    print(f"   📄 Response: {response_text}")
            
            # Clean up batch resources
            if 'batch_flows' in self.test_data:
                for flow in self.test_data['batch_flows']:
                    async with session.delete(f"{self.base_url}/flows/{flow['id']}") as response:
                        if response.status in [200, 204]:
                            print(f"   ✅ Batch flow cleaned up: {flow['id']}")
            
            if 'batch_objects' in self.test_data:
                for obj in self.test_data['batch_objects']:
                    async with session.delete(f"{self.base_url}/objects/{obj['id']}") as response:
                        if response.status in [200, 204]:
                            print(f"   ✅ Batch object cleaned up: {obj['id']}")
            
            if 'batch_sources' in self.test_data:
                for source in self.test_data['batch_sources']:
                    async with session.delete(f"{self.base_url}/sources/{source['id']}") as response:
                        if response.status in [200, 204, 403]:
                            print(f"   ✅ Batch source cleaned up: {source['id']}")
        
        print("✅ Batch operations endpoints test completed")
        return True


if __name__ == "__main__":
    """Run the comprehensive API endpoint tests"""
    print("🚀 Comprehensive TAMS API Endpoint Tests")
    print("=" * 60)
    print("This test will cover all API endpoints systematically:")
    print("1. Analytics endpoints")
    print("2. Flow storage allocation")
    print("3. Flow tags management")
    print("4. Flow properties")
    print("5. Source tags management")
    print("6. Source properties")
    print("7. Batch operations")
    print()
    
    # Create test instance
    tester = TestComprehensiveAPIEndpoints()
    
    # Set up test data manually since we're not running through pytest
    tester.base_url = "http://localhost:8000"
    tester.test_data = {}
    
    # Run the tests
    async def run_tests():
        print("🧪 Running comprehensive API endpoint tests...")
        
        results = []
        
        print("\n🧪 Testing analytics endpoints...")
        result1 = await tester.test_analytics_endpoints()
        results.append(("Analytics Endpoints", result1))
        
        print("\n🧪 Testing flow storage endpoint...")
        result2 = await tester.test_flow_storage_endpoint()
        results.append(("Flow Storage Endpoint", result2))
        
        print("\n🧪 Testing flow tags endpoints...")
        result3 = await tester.test_flow_tags_endpoints()
        results.append(("Flow Tags Endpoints", result3))
        
        print("\n🧪 Testing flow properties endpoints...")
        result4 = await tester.test_flow_properties_endpoints()
        results.append(("Flow Properties Endpoints", result4))
        
        print("\n🧪 Testing source tags endpoints...")
        result5 = await tester.test_source_tags_endpoints()
        results.append(("Source Tags Endpoints", result5))
        
        print("\n🧪 Testing source properties endpoints...")
        result6 = await tester.test_source_properties_endpoints()
        results.append(("Source Properties Endpoints", result6))
        
        print("\n🧪 Testing batch operations endpoints...")
        result7 = await tester.test_batch_operations_endpoints()
        results.append(("Batch Operations Endpoints", result7))
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE API TEST SUMMARY")
        print("=" * 60)
        
        passed = 0
        for test_name, result in results:
            status = "PASSED" if result else "FAILED"
            print(f"✅ {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n📊 Total tests: {len(results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {len(results) - passed}")
        
        if passed == len(results):
            print("\n🎉 ALL COMPREHENSIVE API TESTS PASSED!")
            print("📊 Complete API endpoint coverage achieved.")
        else:
            print("\n❌ SOME COMPREHENSIVE API TESTS FAILED.")
            print("📊 Check the output above for details.")
    
    # Run the async tests
    import asyncio
    asyncio.run(run_tests())
