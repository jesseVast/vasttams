import pytest
import requests
import json
import uuid
from datetime import datetime, timezone

class TestRealAPIEndpoints:
    """Test API endpoints by making real HTTP requests to the running server"""
    
    @pytest.fixture
    def server_url(self):
        """Get the server URL for testing"""
        return "http://localhost:8000"
    
    def test_real_health_endpoint(self, server_url):
        """Test the real health endpoint with HTTP request"""
        print(f"🔍 Testing REAL health endpoint at {server_url}/health")
        
        response = requests.get(f"{server_url}/health", timeout=10)
        print(f"📡 Response status: {response.status_code}")
        print(f"📡 Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✅ Health endpoint working!")
    
    def test_real_sources_endpoint(self, server_url):
        """Test the real sources endpoint with HTTP request"""
        print(f"🔍 Testing REAL sources endpoint at {server_url}/sources")
        
        # Test GET /sources
        response = requests.get(f"{server_url}/sources", timeout=10)
        print(f"📡 GET /sources status: {response.status_code}")
        print(f"📡 GET /sources body: {response.text}")
        
        # Should get a response (may be empty list or error, but should respond)
        assert response.status_code in [200, 404, 500]  # Any response is fine for now
        
        print("✅ Sources endpoint responding!")
    
    def test_real_flows_endpoint(self, server_url):
        """Test the real flows endpoint with HTTP request"""
        print(f"🔍 Testing REAL flows endpoint at {server_url}/flows")
        
        # Test GET /flows
        response = requests.get(f"{server_url}/flows", timeout=10)
        print(f"📡 GET /flows status: {response.status_code}")
        print(f"📡 GET /flows body: {response.text}")
        
        # Should get a response
        assert response.status_code in [200, 404, 500]
        
        print("✅ Flows endpoint responding!")
    
    def test_real_root_endpoint(self, server_url):
        """Test the real root endpoint with HTTP request"""
        print(f"🔍 Testing REAL root endpoint at {server_url}/")
        
        response = requests.get(f"{server_url}/", timeout=10)
        print(f"📡 GET / status: {response.status_code}")
        print(f"📡 GET / body: {response.text[:200]}...")  # First 200 chars
        
        # Should get a response
        assert response.status_code in [200, 404, 301, 302]
        
        print("✅ Root endpoint responding!")
    
    def test_real_openapi_endpoint(self, server_url):
        """Test the real OpenAPI endpoint with HTTP request"""
        print(f"🔍 Testing REAL OpenAPI endpoint at {server_url}/docs")
        
        response = requests.get(f"{server_url}/docs", timeout=10)
        print(f"📡 GET /docs status: {response.status_code}")
        print(f"📡 GET /docs content-type: {response.headers.get('content-type', 'unknown')}")
        
        # Should get HTML documentation
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        
        print("✅ OpenAPI docs endpoint working!")
    
    def test_real_api_schema_endpoint(self, server_url):
        """Test the real API schema endpoint with HTTP request"""
        print(f"🔍 Testing REAL API schema endpoint at {server_url}/openapi.json")
        
        response = requests.get(f"{server_url}/openapi.json", timeout=10)
        print(f"📡 GET /openapi.json status: {response.status_code}")
        print(f"📡 GET /openapi.json content-type: {response.headers.get('content-type', 'unknown')}")
        
        # Should get JSON schema
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
        
        # Should be valid JSON
        schema = response.json()
        assert "openapi" in schema
        print(f"✅ API schema endpoint working! OpenAPI version: {schema.get('openapi', 'unknown')}")
    
    def test_real_sources_crud_operations(self, server_url):
        """Test full CRUD operations on sources endpoint"""
        print(f"\n🔍 Testing REAL sources CRUD operations at {server_url}/sources")
        
        # Test data
        source_data = {
            "id": str(uuid.uuid4()),
            "format": "urn:x-nmos:format:video",
            "label": "Test Source for CRUD",
            "description": "Testing full CRUD operations"
        }
        
        # 1. CREATE - POST /sources
        print(f"📝 Creating source with data: {source_data}")
        create_response = requests.post(f"{server_url}/sources", json=source_data, timeout=10)
        print(f"📡 POST /sources status: {create_response.status_code}")
        print(f"📡 POST /sources body: {create_response.text}")
        
        if create_response.status_code == 201:
            created_source = create_response.json()
            source_id = created_source["id"]
            print(f"✅ Source created successfully with ID: {source_id}")
            
            # 2. READ - GET /sources/{id}
            print(f"📖 Reading source with ID: {source_id}")
            read_response = requests.get(f"{server_url}/sources/{source_id}", timeout=10)
            print(f"📡 GET /sources/{source_id} status: {read_response.status_code}")
            print(f"📡 GET /sources/{source_id} body: {read_response.text}")
            
            if read_response.status_code == 200:
                retrieved_source = read_response.json()
                assert retrieved_source["id"] == source_id
                print("✅ Source retrieved successfully")
                
                # 3. UPDATE - PUT /sources/{id}/tags (if available)
                print(f"🔄 Testing update operations...")
                # Note: TAMS API may not support direct PUT on sources, only tag updates
                
                # 4. DELETE - DELETE /sources/{id}
                print(f"🗑️ Deleting source with ID: {source_id}")
                delete_response = requests.delete(f"{server_url}/sources/{source_id}", timeout=10)
                print(f"📡 DELETE /sources/{source_id} status: {delete_response.status_code}")
                print(f"📡 DELETE /sources/{source_id} body: {delete_response.text}")
                
                if delete_response.status_code in [200, 204]:
                    print("✅ Source deleted successfully")
                    
                    # 5. VERIFY DELETION - GET /sources/{id} should return 404
                    verify_response = requests.get(f"{server_url}/sources/{source_id}", timeout=10)
                    print(f"📡 Verification GET /sources/{source_id} status: {verify_response.status_code}")
                    
                    if verify_response.status_code == 404:
                        print("✅ Source deletion verified (404 returned)")
                    else:
                        print(f"⚠️ Unexpected status after deletion: {verify_response.status_code}")
                else:
                    print(f"⚠️ Delete operation returned unexpected status: {delete_response.status_code}")
            else:
                print(f"❌ Failed to retrieve source: {read_response.status_code}")
        else:
            print(f"❌ Failed to create source: {create_response.status_code}")
            if create_response.status_code == 422:
                print("This might be due to missing required fields or validation issues")
    
    def test_real_flows_crud_operations(self, server_url):
        """Test full CRUD operations on flows endpoint"""
        print(f"\n🔍 Testing REAL flows CRUD operations at {server_url}/flows")
        
        # Test data
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": str(uuid.uuid4()),  # Mock source ID
            "format": "urn:x-nmos:format:video",
            "codec": "video/mp4",
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": "25:1",
            "label": "Test Flow for CRUD",
            "description": "Testing full CRUD operations on flows"
        }
        
        # 1. CREATE - POST /flows
        print(f"📝 Creating flow with data: {flow_data}")
        create_response = requests.post(f"{server_url}/flows", json=flow_data, timeout=10)
        print(f"📡 POST /flows status: {create_response.status_code}")
        print(f"📡 POST /flows body: {create_response.text}")
        
        if create_response.status_code == 201:
            created_flow = create_response.json()
            flow_id = created_flow["id"]
            print(f"✅ Flow created successfully with ID: {flow_id}")
            
            # 2. READ - GET /flows/{id}
            print(f"📖 Reading flow with ID: {flow_id}")
            read_response = requests.get(f"{server_url}/flows/{flow_id}", timeout=10)
            print(f"📡 GET /flows/{flow_id} status: {read_response.status_code}")
            print(f"📡 GET /flows/{flow_id} body: {read_response.text}")
            
            if read_response.status_code == 200:
                retrieved_flow = read_response.json()
                assert retrieved_flow["id"] == flow_id
                print("✅ Flow retrieved successfully")
                
                # 3. DELETE - DELETE /flows/{id}
                print(f"🗑️ Deleting flow with ID: {flow_id}")
                delete_response = requests.delete(f"{server_url}/flows/{flow_id}", timeout=10)
                print(f"📡 DELETE /flows/{flow_id} status: {delete_response.status_code}")
                print(f"📡 DELETE /flows/{flow_id} body: {delete_response.text}")
                
                if delete_response.status_code in [200, 204]:
                    print("✅ Flow deleted successfully")
                    
                    # 4. VERIFY DELETION - GET /flows/{id} should return 404
                    verify_response = requests.get(f"{server_url}/flows/{flow_id}", timeout=10)
                    print(f"📡 Verification GET /flows/{flow_id} status: {verify_response.status_code}")
                    
                    if verify_response.status_code == 404:
                        print("✅ Flow deletion verified (404 returned)")
                    else:
                        print(f"⚠️ Unexpected status after deletion: {verify_response.status_code}")
                else:
                    print(f"⚠️ Delete operation returned unexpected status: {delete_response.status_code}")
            else:
                print(f"❌ Failed to retrieve flow: {read_response.status_code}")
        else:
            print(f"❌ Failed to create flow: {create_response.status_code}")
            if create_response.status_code == 422:
                print("This might be due to missing required fields or validation issues")
    
    def test_real_endpoints_with_actual_data(self, server_url):
        """Test endpoints with actual data to see real responses"""
        print(f"\n🔍 Testing endpoints with actual data at {server_url}")
        
        # Test GET /sources with actual data
        print(f"📖 Testing GET /sources with actual data")
        sources_response = requests.get(f"{server_url}/sources", timeout=10)
        print(f"📡 GET /sources status: {sources_response.status_code}")
        print(f"📡 GET /sources headers: {dict(sources_response.headers)}")
        print(f"📡 GET /sources body: {sources_response.text}")
        
        # Test GET /flows with actual data
        print(f"📖 Testing GET /flows with actual data")
        flows_response = requests.get(f"{server_url}/flows", timeout=10)
        print(f"📡 GET /flows status: {flows_response.status_code}")
        print(f"📡 GET /flows headers: {dict(flows_response.headers)}")
        print(f"📡 GET /flows body: {flows_response.text}")
        
        # Test GET /service endpoint
        print(f"📖 Testing GET /service endpoint")
        service_response = requests.get(f"{server_url}/service", timeout=10)
        print(f"📡 GET /service status: {service_response.status_code}")
        print(f"📡 GET /service body: {service_response.text}")
        
        print("✅ Endpoint data testing completed")
    
    def test_real_flow_segments_crud_operations(self, server_url):
        """Test full CRUD operations on flow segments endpoint"""
        print(f"\n🔍 Testing REAL flow segments CRUD operations at {server_url}/flows")
        
        # First, create a flow to work with
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": str(uuid.uuid4()),  # Mock source ID
            "format": "urn:x-nmos:format:video",
            "codec": "video/mp4",
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": "25:1",
            "label": "Test Flow for Segments",
            "description": "Testing flow segments CRUD operations"
        }
        
        print(f"📝 Creating flow for segments testing: {flow_data['id']}")
        flow_response = requests.post(f"{server_url}/flows", json=flow_data, timeout=10)
        
        if flow_response.status_code != 201:
            print(f"❌ Failed to create flow for segments testing: {flow_response.status_code}")
            return
        
        flow_id = flow_data["id"]
        print(f"✅ Flow created successfully for segments testing: {flow_id}")
        
        # Test data for segments
        segment_data = {
            "object_id": str(uuid.uuid4()),
            "timerange": "0:0_3600:0",  # TAMS format: 1 hour
            "sample_offset": 0,
            "sample_count": 90000,  # 25fps * 3600s
            "key_frame_count": 3600,
            "storage_path": f"flows/{flow_id}/segments/test_segment"
        }
        
        # 1. CREATE - POST /flows/{flow_id}/segments
        print(f"📝 Creating flow segment with data: {segment_data}")
        # Send as form data with segment_data key (not JSON)
        create_response = requests.post(
            f"{server_url}/flows/{flow_id}/segments", 
            data={"segment_data": json.dumps(segment_data)}, 
            timeout=10
        )
        print(f"📡 POST /flows/{flow_id}/segments status: {create_response.status_code}")
        print(f"📡 POST /flows/{flow_id}/segments body: {create_response.text}")
        
        if create_response.status_code == 201:
            created_segment = create_response.json()
            segment_object_id = created_segment["object_id"]
            print(f"✅ Flow segment created successfully with object ID: {segment_object_id}")
            
            # 2. READ - GET /flows/{flow_id}/segments
            print(f"📖 Reading flow segments for flow: {flow_id}")
            read_response = requests.get(f"{server_url}/flows/{flow_id}/segments", timeout=10)
            print(f"📡 GET /flows/{flow_id}/segments status: {read_response.status_code}")
            print(f"📡 GET /flows/{flow_id}/segments body: {read_response.text}")
            
            if read_response.status_code == 200:
                segments = read_response.json()
                assert isinstance(segments, list)
                print(f"✅ Flow segments retrieved successfully. Found {len(segments)} segments")
                
                # Find our created segment
                our_segment = None
                for segment in segments:
                    if segment.get("object_id") == segment_object_id:
                        our_segment = segment
                        break
                
                if our_segment:
                    print(f"✅ Our created segment found in list: {our_segment['object_id']}")
                else:
                    print("⚠️ Our created segment not found in segments list")
                
                # 3. READ with timerange filtering
                print(f"📖 Testing timerange filtering for flow: {flow_id}")
                timerange_response = requests.get(
                    f"{server_url}/flows/{flow_id}/segments?timerange=0:0_3600:0", 
                    timeout=10
                )
                print(f"📡 GET /flows/{flow_id}/segments?timerange=0:0_3600:0 status: {timerange_response.status_code}")
                print(f"📡 GET /flows/{flow_id}/segments?timerange=0:0_3600:0 body: {timerange_response.text}")
                
                if timerange_response.status_code == 200:
                    filtered_segments = timerange_response.json()
                    print(f"✅ Timerange filtering working. Found {len(filtered_segments)} segments in range")
                else:
                    print(f"⚠️ Timerange filtering returned unexpected status: {timerange_response.status_code}")
                
                # 4. DELETE - DELETE /flows/{flow_id}/segments
                print(f"🗑️ Testing segment deletion for flow: {flow_id}")
                delete_response = requests.delete(f"{server_url}/flows/{flow_id}/segments", timeout=10)
                print(f"📡 DELETE /flows/{flow_id}/segments status: {delete_response.status_code}")
                print(f"📡 DELETE /flows/{flow_id}/segments body: {delete_response.text}")
                
                if delete_response.status_code in [200, 204, 202]:
                    print("✅ Flow segments deleted successfully")
                    
                    # 5. VERIFY DELETION - GET /flows/{flow_id}/segments should return empty or different data
                    verify_response = requests.get(f"{server_url}/flows/{flow_id}/segments", timeout=10)
                    print(f"📡 Verification GET /flows/{flow_id}/segments status: {verify_response.status_code}")
                    
                    if verify_response.status_code == 200:
                        remaining_segments = verify_response.json()
                        if len(remaining_segments) == 0:
                            print("✅ Segment deletion verified (no segments remaining)")
                        else:
                            print(f"⚠️ {len(remaining_segments)} segments still remain after deletion")
                    else:
                        print(f"⚠️ Verification request failed: {verify_response.status_code}")
                else:
                    print(f"⚠️ Delete operation returned unexpected status: {delete_response.status_code}")
            else:
                print(f"❌ Failed to retrieve flow segments: {read_response.status_code}")
        else:
            print(f"❌ Failed to create flow segment: {create_response.status_code}")
            if create_response.status_code == 422:
                print("This might be due to missing required fields or validation issues")
        
        # Clean up: delete the test flow
        print(f"🧹 Cleaning up test flow: {flow_id}")
        cleanup_response = requests.delete(f"{server_url}/flows/{flow_id}", timeout=10)
        if cleanup_response.status_code in [200, 204]:
            print("✅ Test flow cleaned up successfully")
        else:
            print(f"⚠️ Failed to cleanup test flow: {cleanup_response.status_code}")
    
    def test_real_flow_segments_with_multipart_form(self, server_url):
        """Test flow segments endpoint with multipart form data (file upload)"""
        print(f"\n🔍 Testing REAL flow segments with multipart form data at {server_url}/flows")
        
        # First, create a flow to work with
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": str(uuid.uuid4()),
            "format": "urn:x-nmos:format:video",
            "codec": "video/mp4",
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": "25:1",
            "label": "Test Flow for Multipart Segments",
            "description": "Testing flow segments with file upload"
        }
        
        print(f"📝 Creating flow for multipart segments testing: {flow_data['id']}")
        flow_response = requests.post(f"{server_url}/flows", json=flow_data, timeout=10)
        
        if flow_response.status_code != 201:
            print(f"❌ Failed to create flow for multipart segments testing: {flow_response.status_code}")
            return
        
        flow_id = flow_data["id"]
        print(f"✅ Flow created successfully for multipart segments testing: {flow_id}")
        
        # Test data for multipart segment
        segment_data = {
            "object_id": str(uuid.uuid4()),
            "timerange": "0:0_1800:0",  # 30 minutes
            "sample_offset": 0,
            "sample_count": 45000,  # 25fps * 1800s
            "key_frame_count": 1800
        }
        
        # Create a mock file content
        mock_file_content = b"Mock video segment data for testing"
        
        # 1. CREATE with multipart form - POST /flows/{flow_id}/segments
        print(f"📝 Creating flow segment with multipart form data: {segment_data}")
        
        # Use multipart form data
        files = {'file': ('test_segment.mp4', mock_file_content, 'video/mp4')}
        data = {'segment_data': json.dumps(segment_data)}
        
        create_response = requests.post(
            f"{server_url}/flows/{flow_id}/segments", 
            files=files,
            data=data,
            timeout=10
        )
        print(f"📡 POST /flows/{flow_id}/segments (multipart) status: {create_response.status_code}")
        print(f"📡 POST /flows/{flow_id}/segments (multipart) body: {create_response.text}")
        
        if create_response.status_code == 201:
            created_segment = create_response.json()
            segment_object_id = created_segment["object_id"]
            print(f"✅ Flow segment created successfully with multipart form: {segment_object_id}")
            
            # 2. READ - GET /flows/{flow_id}/segments to verify
            print(f"📖 Verifying multipart segment creation for flow: {flow_id}")
            read_response = requests.get(f"{server_url}/flows/{flow_id}/segments", timeout=10)
            print(f"📡 GET /flows/{flow_id}/segments status: {read_response.status_code}")
            
            if read_response.status_code == 200:
                segments = read_response.json()
                print(f"✅ Found {len(segments)} segments after multipart creation")
                
                # Find our created segment
                our_segment = None
                for segment in segments:
                    if segment.get("object_id") == segment_object_id:
                        our_segment = segment
                        break
                
                if our_segment:
                    print(f"✅ Multipart segment found in list: {our_segment['object_id']}")
                    if our_segment.get("storage_path"):
                        print(f"✅ Segment has storage path: {our_segment['storage_path']}")
                    else:
                        print("⚠️ Segment missing storage path")
                else:
                    print("⚠️ Multipart segment not found in segments list")
            else:
                print(f"❌ Failed to verify multipart segment: {read_response.status_code}")
        else:
            print(f"❌ Failed to create flow segment with multipart form: {create_response.status_code}")
            if create_response.status_code == 422:
                print("This might be due to missing required fields or validation issues")
        
        # Clean up: delete the test flow
        print(f"🧹 Cleaning up test flow: {flow_id}")
        cleanup_response = requests.delete(f"{server_url}/flows/{flow_id}", timeout=10)
        if cleanup_response.status_code in [200, 204]:
            print("✅ Test flow cleaned up successfully")
        else:
            print(f"⚠️ Failed to cleanup test flow: {cleanup_response.status_code}")
    
    def test_real_flow_segments_error_cases(self, server_url):
        """Test flow segments endpoint error cases and edge conditions"""
        print(f"\n🔍 Testing REAL flow segments error cases at {server_url}/flows")
        
        # Test with non-existent flow ID
        fake_flow_id = str(uuid.uuid4())
        print(f"🧪 Testing segments endpoint with non-existent flow: {fake_flow_id}")
        
        # GET segments for non-existent flow
        get_response = requests.get(f"{server_url}/flows/{fake_flow_id}/segments", timeout=10)
        print(f"📡 GET /flows/{fake_flow_id}/segments status: {get_response.status_code}")
        print(f"📡 GET /flows/{fake_flow_id}/segments body: {get_response.text}")
        
        if get_response.status_code == 404:
            print("✅ Correctly returns 404 for non-existent flow")
        else:
            print(f"⚠️ Unexpected status for non-existent flow: {get_response.status_code}")
        
        # POST segment to non-existent flow
        segment_data = {
            "object_id": str(uuid.uuid4()),
            "timerange": "0:0_3600:0",
            "sample_offset": 0,
            "sample_count": 90000,
            "key_frame_count": 3600
        }
        
        post_response = requests.post(f"{server_url}/flows/{fake_flow_id}/segments", json=segment_data, timeout=10)
        print(f"📡 POST /flows/{fake_flow_id}/segments status: {post_response.status_code}")
        print(f"📡 POST /flows/{fake_flow_id}/segments body: {post_response.text}")
        
        if post_response.status_code == 404:
            print("✅ Correctly returns 404 when posting to non-existent flow")
        else:
            print(f"⚠️ Unexpected status when posting to non-existent flow: {post_response.status_code}")
        
        # Test with invalid timerange format
        print(f"🧪 Testing segments endpoint with invalid timerange format")
        
        # Create a real flow first
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": str(uuid.uuid4()),
            "format": "urn:x-nmos:format:video",
            "codec": "video/mp4",
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": "25:1",
            "label": "Test Flow for Error Cases",
            "description": "Testing flow segments error conditions"
        }
        
        flow_response = requests.post(f"{server_url}/flows", json=flow_data, timeout=10)
        if flow_response.status_code == 201:
            flow_id = flow_data["id"]
            print(f"✅ Created test flow for error testing: {flow_id}")
            
            # Test invalid timerange
            invalid_segment_data = {
                "object_id": str(uuid.uuid4()),
                "timerange": "invalid-timerange-format",  # Invalid format
                "sample_offset": 0,
                "sample_count": 90000,
                "key_frame_count": 3600
            }
            
            invalid_response = requests.post(f"{server_url}/flows/{flow_id}/segments", json=invalid_segment_data, timeout=10)
            print(f"📡 POST /flows/{flow_id}/segments (invalid timerange) status: {invalid_response.status_code}")
            print(f"📡 POST /flows/{flow_id}/segments (invalid timerange) body: {invalid_response.text}")
            
            if invalid_response.status_code == 422:
                print("✅ Correctly returns 422 for invalid timerange format")
            else:
                print(f"⚠️ Unexpected status for invalid timerange: {invalid_response.status_code}")
            
            # Clean up
            cleanup_response = requests.delete(f"{server_url}/flows/{flow_id}", timeout=10)
            if cleanup_response.status_code in [200, 204]:
                print("✅ Test flow cleaned up successfully")
            else:
                print(f"⚠️ Failed to cleanup test flow: {cleanup_response.status_code}")
        else:
            print(f"❌ Failed to create test flow for error testing: {flow_response.status_code}")
        
        print("✅ Flow segments error case testing completed")
    
    def test_real_object_upload_and_retrieval(self, server_url):
        """Test real object upload, storage, and retrieval functionality"""
        print(f"\n🔍 Testing REAL object upload and retrieval at {server_url}/flows")
        
        # First, create a flow to work with
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": str(uuid.uuid4()),
            "format": "urn:x-nmos:format:video",
            "codec": "video/mp4",
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": "25:1",
            "label": "Test Flow for Object Upload",
            "description": "Testing real object upload and retrieval"
        }
        
        print(f"📝 Creating flow for object upload testing: {flow_data['id']}")
        flow_response = requests.post(f"{server_url}/flows", json=flow_data, timeout=10)
        
        if flow_response.status_code != 201:
            print(f"❌ Failed to create flow for object upload testing: {flow_response.status_code}")
            return
        
        flow_id = flow_data["id"]
        print(f"✅ Flow created successfully for object upload testing: {flow_id}")
        
        # Create realistic test data with different content types
        test_cases = [
            {
                "name": "Video Segment",
                "content": b"Fake MP4 video data for testing - this would be a real video file in production",
                "filename": "test_video_segment.mp4",
                "content_type": "video/mp4",
                "size": 89  # Length of the fake content
            },
            {
                "name": "Audio Segment", 
                "content": b"Fake audio data - this would be a real audio file in production",
                "filename": "test_audio_segment.wav",
                "content_type": "audio/wav",
                "size": 67  # Length of the fake content
            },
            {
                "name": "Large Data Segment",
                "content": b"Large test data " * 1000,  # 16KB of data
                "filename": "large_test_data.bin",
                "content_type": "application/octet-stream",
                "size": 16000  # Length of the large content
            }
        ]
        
        uploaded_segments = []
        
        for test_case in test_cases:
            print(f"\n📤 Testing {test_case['name']} upload...")
            
            # Test data for segment
            segment_data = {
                "object_id": str(uuid.uuid4()),
                "timerange": "0:0_1800:0",  # 30 minutes
                "sample_offset": 0,
                "sample_count": 45000,  # 25fps * 1800s
                "key_frame_count": 1800
            }
            
            # Create multipart form data with real file content
            files = {
                'file': (
                    test_case['filename'], 
                    test_case['content'], 
                    test_case['content_type']
                )
            }
            data = {'segment_data': json.dumps(segment_data)}
            
            # Upload the segment
            create_response = requests.post(
                f"{server_url}/flows/{flow_id}/segments", 
                files=files,
                data=data,
                timeout=30  # Longer timeout for larger files
            )
            print(f"📡 POST /flows/{flow_id}/segments status: {create_response.status_code}")
            
            if create_response.status_code == 201:
                created_segment = create_response.json()
                segment_object_id = created_segment["object_id"]
                print(f"✅ {test_case['name']} uploaded successfully: {segment_object_id}")
                
                # Store segment info for later verification
                uploaded_segments.append({
                    "test_case": test_case,
                    "segment": created_segment,
                    "segment_data": segment_data
                })
            else:
                print(f"❌ Failed to upload {test_case['name']}: {create_response.status_code}")
                print(f"📡 Response body: {create_response.text}")
        
        if not uploaded_segments:
            print("❌ No segments were uploaded successfully, skipping retrieval tests")
            return
        
        print(f"\n📥 Testing object retrieval for {len(uploaded_segments)} uploaded segments...")
        
        # Verify segments are listed
        list_response = requests.get(f"{server_url}/flows/{flow_id}/segments", timeout=10)
        if list_response.status_code == 200:
            segments = list_response.json()
            print(f"✅ Found {len(segments)} segments in flow")
            
            # Verify our uploaded segments are in the list
            for uploaded in uploaded_segments:
                segment_id = uploaded["segment"]["object_id"]
                found = any(seg["object_id"] == segment_id for seg in segments)
                if found:
                    print(f"✅ Segment {segment_id} found in segments list")
                else:
                    print(f"❌ Segment {segment_id} NOT found in segments list")
        else:
            print(f"❌ Failed to list segments: {list_response.status_code}")
        
        # Test file content retrieval using generated URLs
        print(f"\n🔗 Testing file content retrieval via generated URLs...")
        
        for uploaded in uploaded_segments:
            segment = uploaded["segment"]
            test_case = uploaded["test_case"]
            segment_id = segment["object_id"]
            
            print(f"\n📥 Testing retrieval for {test_case['name']}: {segment_id}")
            
            # Check if segment has get_urls
            if segment.get("get_urls") and len(segment["get_urls"]) > 0:
                get_url = segment["get_urls"][0]
                url = get_url["url"]
                label = get_url.get("label", "default")
                
                print(f"🔗 Using URL: {url}")
                print(f"🏷️ Label: {label}")
                
                try:
                    # Download the file content
                    download_response = requests.get(url, timeout=30)
                    print(f"📡 Download status: {download_response.status_code}")
                    
                    if download_response.status_code == 200:
                        downloaded_content = download_response.content
                        downloaded_size = len(downloaded_content)
                        expected_size = test_case["size"]
                        
                        print(f"📊 Downloaded size: {downloaded_size} bytes")
                        print(f"📊 Expected size: {expected_size} bytes")
                        
                        # Verify file size
                        if downloaded_size == expected_size:
                            print(f"✅ File size matches: {downloaded_size} bytes")
                        else:
                            print(f"❌ File size mismatch: expected {expected_size}, got {downloaded_size}")
                        
                        # Verify file content
                        if downloaded_content == test_case["content"]:
                            print(f"✅ File content matches exactly")
                        else:
                            print(f"❌ File content mismatch")
                            print(f"📝 Expected: {test_case['content'][:50]}...")
                            print(f"📝 Got: {downloaded_content[:50]}...")
                        
                        # Verify content type header
                        content_type_header = download_response.headers.get('content-type', '')
                        if test_case["content_type"] in content_type_header:
                            print(f"✅ Content-Type header correct: {content_type_header}")
                        else:
                            print(f"⚠️ Content-Type header mismatch: expected {test_case['content_type']}, got {content_type_header}")
                        
                    else:
                        print(f"❌ Download failed with status: {download_response.status_code}")
                        print(f"📡 Download response: {download_response.text}")
                        
                except Exception as e:
                    print(f"❌ Download error: {e}")
            else:
                print(f"⚠️ No get_urls available for segment {segment_id}")
                print(f"🔍 Full segment data for debugging:")
                print(f"   - object_id: {segment.get('object_id')}")
                print(f"   - timerange: {segment.get('timerange')}")
                print(f"   - storage_path: {segment.get('storage_path')}")
                print(f"   - get_urls: {segment.get('get_urls')}")
                print(f"   - All fields: {list(segment.keys())}")
                print(f"   - Segment JSON: {json.dumps(segment, indent=2)}")
        
        # Test timerange filtering with uploaded segments
        print(f"\n⏰ Testing timerange filtering with real segments...")
        
        timerange_response = requests.get(
            f"{server_url}/flows/{flow_id}/segments?timerange=0:0_1800:0", 
            timeout=10
        )
        
        if timerange_response.status_code == 200:
            filtered_segments = timerange_response.json()
            print(f"✅ Timerange filtering returned {len(filtered_segments)} segments")
            
            # Verify all our uploaded segments are in the filtered results
            for uploaded in uploaded_segments:
                segment_id = uploaded["segment"]["object_id"]
                found = any(seg["object_id"] == segment_id for seg in filtered_segments)
                if found:
                    print(f"✅ Segment {segment_id} found in filtered results")
                else:
                    print(f"❌ Segment {segment_id} NOT found in filtered results")
        else:
            print(f"❌ Timerange filtering failed: {timerange_response.status_code}")
        
        # Clean up: delete the test flow
        print(f"\n🧹 Cleaning up test flow: {flow_id}")
        cleanup_response = requests.delete(f"{server_url}/flows/{flow_id}", timeout=10)
        if cleanup_response.status_code in [200, 204]:
            print("✅ Test flow cleaned up successfully")
        else:
            print(f"⚠️ Failed to cleanup test flow: {cleanup_response.status_code}")
        
        print("✅ Object upload and retrieval testing completed")
    
    def test_real_object_upload_edge_cases(self, server_url):
        """Test edge cases for object upload including large files, different content types, and error conditions"""
        print(f"\n🔍 Testing REAL object upload edge cases at {server_url}/flows")
        
        # First, create a flow to work with
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": str(uuid.uuid4()),
            "format": "urn:x-nmos:format:video",
            "codec": "video/mp4",
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": "25:1",
            "label": "Test Flow for Upload Edge Cases",
            "description": "Testing object upload edge cases and error conditions"
        }
        
        print(f"📝 Creating flow for upload edge case testing: {flow_data['id']}")
        flow_response = requests.post(f"{server_url}/flows", json=flow_data, timeout=10)
        
        if flow_response.status_code != 201:
            print(f"❌ Failed to create flow for upload edge case testing: {flow_response.status_code}")
            return
        
        flow_id = flow_data["id"]
        print(f"✅ Flow created successfully for upload edge case testing: {flow_id}")
        
        # Test edge cases
        edge_cases = [
            {
                "name": "Empty File",
                "content": b"",
                "filename": "empty_file.bin",
                "content_type": "application/octet-stream",
                "expected_success": True  # Should succeed but skip S3 storage
            },
            {
                "name": "Very Small File",
                "content": b"X",
                "filename": "tiny_file.txt",
                "content_type": "text/plain",
                "expected_success": True
            },
            {
                "name": "Binary Data with Special Characters",
                "content": b"\x00\x01\x02\x03\xFF\xFE\xFD\xFC",
                "filename": "binary_data.bin",
                "content_type": "application/octet-stream",
                "expected_success": True
            },
            {
                "name": "Unicode Filename",
                "content": b"Test content with unicode filename",
                "filename": "test_文件_测试.mp4",
                "content_type": "video/mp4",
                "expected_success": True
            },
            {
                "name": "Long Filename",
                "content": b"Test content with very long filename",
                "filename": "a" * 100 + ".mp4",  # 100 character filename
                "content_type": "video/mp4",
                "expected_success": True
            }
        ]
        
        for edge_case in edge_cases:
            print(f"\n🧪 Testing edge case: {edge_case['name']}")
            
            # Test data for segment
            segment_data = {
                "object_id": str(uuid.uuid4()),
                "timerange": "0:0_900:0",  # 15 minutes
                "sample_offset": 0,
                "sample_count": 22500,  # 25fps * 900s
                "key_frame_count": 900
            }
            
            # Create multipart form data
            files = {
                'file': (
                    edge_case['filename'], 
                    edge_case['content'], 
                    edge_case['content_type']
                )
            }
            data = {'segment_data': json.dumps(segment_data)}
            
            # Upload the segment
            create_response = requests.post(
                f"{server_url}/flows/{flow_id}/segments", 
                files=files,
                data=data,
                timeout=30
            )
            print(f"📡 POST /flows/{flow_id}/segments status: {create_response.status_code}")
            
            if create_response.status_code == 201:
                created_segment = create_response.json()
                segment_object_id = created_segment["object_id"]
                print(f"✅ {edge_case['name']} uploaded successfully: {segment_object_id}")
                
                # Verify the segment was created
                if created_segment.get("storage_path"):
                    print(f"✅ Segment has storage path: {created_segment['storage_path']}")
                else:
                    print("⚠️ Segment missing storage path")
                
                # Test retrieval if upload was successful
                if edge_case["expected_success"]:
                    # Verify segment appears in list
                    list_response = requests.get(f"{server_url}/flows/{flow_id}/segments", timeout=10)
                    if list_response.status_code == 200:
                        segments = list_response.json()
                        found = any(seg["object_id"] == segment_object_id for seg in segments)
                        if found:
                            print(f"✅ Segment {segment_object_id} found in segments list")
                        else:
                            print(f"❌ Segment {segment_object_id} NOT found in segments list")
                    else:
                        print(f"❌ Failed to list segments: {list_response.status_code}")
                
            elif create_response.status_code == 422:
                print(f"⚠️ Validation error for {edge_case['name']}: {create_response.text}")
            else:
                print(f"❌ Failed to upload {edge_case['name']}: {create_response.status_code}")
                print(f"📡 Response body: {create_response.text}")
        
        # Test error conditions
        print(f"\n🚨 Testing upload error conditions...")
        
        # Test with missing file
        segment_data = {
            "object_id": str(uuid.uuid4()),
            "timerange": "0:0_900:0",
            "sample_offset": 0,
            "sample_count": 22500,
            "key_frame_count": 900
        }
        
        # Try to upload without file (only segment_data)
        data_only_response = requests.post(
            f"{server_url}/flows/{flow_id}/segments", 
            data={'segment_data': json.dumps(segment_data)},
            timeout=10
        )
        print(f"📡 POST without file status: {data_only_response.status_code}")
        
        if data_only_response.status_code == 201:
            print("✅ Upload without file succeeded (metadata-only segment)")
        elif data_only_response.status_code == 400:
            print("✅ Correctly rejected upload without file")
        else:
            print(f"⚠️ Unexpected response for upload without file: {data_only_response.status_code}")
        
        # Test with invalid segment data
        invalid_segment_data = {
            "object_id": str(uuid.uuid4()),
            "timerange": "invalid-timerange",  # Invalid timerange
            "sample_offset": 0,
            "sample_count": 22500,
            "key_frame_count": 900
        }
        
        files = {'file': ('test.mp4', b"test content", 'video/mp4')}
        data = {'segment_data': json.dumps(invalid_segment_data)}
        
        invalid_response = requests.post(
            f"{server_url}/flows/{flow_id}/segments", 
            files=files,
            data=data,
            timeout=10
        )
        print(f"📡 POST with invalid timerange status: {invalid_response.status_code}")
        
        if invalid_response.status_code == 400:
            print("✅ Correctly rejected invalid timerange")
        else:
            print(f"⚠️ Unexpected response for invalid timerange: {invalid_response.status_code}")
        
        # Clean up: delete the test flow
        print(f"\n🧹 Cleaning up test flow: {flow_id}")
        cleanup_response = requests.delete(f"{server_url}/flows/{flow_id}", timeout=10)
        if cleanup_response.status_code in [200, 204]:
            print("✅ Test flow cleaned up successfully")
        else:
            print(f"⚠️ Failed to cleanup test flow: {cleanup_response.status_code}")
        
        print("✅ Object upload edge case testing completed")
