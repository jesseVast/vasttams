#!/Users/jesse.thaloor/Developer/python/bbctams/bin/python
"""
Comprehensive end-to-end test for TAMS API with tag functionality and segment downloads.

This script tests the complete TAMS API workflow including:
- Source creation and tag filtering
- Flow creation and tag filtering  
- Segment creation and tag filtering
- URL generation and access
- Segment download functionality
- Tag-based search and filtering across all resource types
"""

import requests
import json
import sys
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

# Test data constants
TEST_SOURCE_ID = "550e8400-e29b-41d4-a716-446655440001"
TEST_FLOW_ID = "550e8400-e29b-41d4-a716-446655440002"
TEST_SEGMENT_1_ID = "seg_001"
TEST_SEGMENT_2_ID = "seg_002"

# Test tags
SOURCE_TAGS = {
    "environment": "production",
    "location": "studio-a",
    "quality": "hd",
    "department": "engineering"
}

FLOW_TAGS = {
    "environment": "production", 
    "priority": "high",
    "stream_type": "live",
    "department": "engineering"
}

SEGMENT_TAGS_1 = {
    "environment": "production",
    "quality": "hd",
    "segment_type": "keyframe"
}

SEGMENT_TAGS_2 = {
    "environment": "staging",
    "quality": "sd", 
    "segment_type": "delta"
}


class TAMSTestRunner:
    """Main test runner class for TAMS API workflow testing with downloads."""
    
    def __init__(self, base_url: str = BASE_URL):
        """Initialize the test runner."""
        self.base_url = base_url
        self.headers = HEADERS
        self.test_results = []
        self.created_resources = []
        self.downloaded_files = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results."""
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def cleanup_resources(self):
        """Clean up all created test resources."""
        print("\n🧹 Cleaning up test resources...")
        
        # Delete downloaded files
        for file_path in self.downloaded_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"   Deleted downloaded file: {file_path}")
            except Exception as e:
                print(f"   Warning: Could not delete {file_path}: {e}")
        
        # Delete segments
        try:
            requests.delete(f"{self.base_url}/flows/{TEST_FLOW_ID}/segments/{TEST_SEGMENT_1_ID}")
            requests.delete(f"{self.base_url}/flows/{TEST_FLOW_ID}/segments/{TEST_SEGMENT_2_ID}")
            self.log_test("Segment cleanup", True, "Deleted test segments")
        except Exception as e:
            self.log_test("Segment cleanup", False, str(e))
        
        # Delete flow
        try:
            requests.delete(f"{self.base_url}/flows/{TEST_FLOW_ID}")
            self.log_test("Flow cleanup", True, "Deleted test flow")
        except Exception as e:
            self.log_test("Flow cleanup", False, str(e))
        
        # Delete source
        try:
            requests.delete(f"{self.base_url}/sources/{TEST_SOURCE_ID}")
            self.log_test("Source cleanup", True, "Deleted test source")
        except Exception as e:
            self.log_test("Source cleanup", False, str(e))
    
    def test_api_health(self) -> bool:
        """Test API health and availability."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                self.log_test("API Health Check", True, "API is responding")
                return True
            else:
                self.log_test("API Health Check", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Health Check", False, str(e))
            return False
    
    def test_source_creation(self) -> bool:
        """Test source creation with tags."""
        print("\n🎬 Testing Source Creation with Tags")
        print("=" * 50)
        
        source_data = {
            "id": TEST_SOURCE_ID,
            "format": "urn:x-nmos:format:video",
            "label": "Test Camera Feed",
            "description": "Test source for tag workflow validation",
            "tags": SOURCE_TAGS,
            "source_collection": [],
            "collected_by": []
        }
        
        try:
            response = requests.post(f"{self.base_url}/sources", json=source_data, headers=self.headers)
            if response.status_code == 201:
                data = response.json()
                self.log_test("Source Creation", True, f"Created source: {data['label']}")
                self.created_resources.append(("source", TEST_SOURCE_ID))
                return True
            else:
                self.log_test("Source Creation", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Source Creation", False, str(e))
            return False
    
    def test_source_tag_filtering(self) -> bool:
        """Test source tag filtering functionality."""
        print("\n🔍 Testing Source Tag Filtering")
        print("=" * 50)
        
        test_cases = [
            ("tag.environment=production", "sources with environment=production"),
            ("tag.location=studio-a", "sources with location=studio-a"),
            ("tag_exists.quality=true", "sources that have quality tag"),
            ("tag.environment=production&tag.department=engineering", "sources with multiple tag filters"),
        ]
        
        all_passed = True
        for query, description in test_cases:
            try:
                response = requests.get(f"{self.base_url}/sources?{query}", headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    count = len(data.get('data', []))
                    success = count > 0
                    self.log_test(f"Source Filter: {description}", success, f"Found {count} sources")
                    if not success:
                        all_passed = False
                else:
                    self.log_test(f"Source Filter: {description}", False, f"Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Source Filter: {description}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_flow_creation(self) -> bool:
        """Test flow creation with tags."""
        print("\n🎬 Testing Flow Creation with Tags")
        print("=" * 50)
        
        flow_data = {
            "id": TEST_FLOW_ID,
            "source_id": TEST_SOURCE_ID,
            "format": "urn:x-nmos:format:video",
            "codec": "video/mp4",
            "label": "Test HD Video Stream",
            "description": "Test flow for tag workflow validation",
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": "25/1",
            "tags": FLOW_TAGS
        }
        
        try:
            response = requests.post(f"{self.base_url}/flows", json=flow_data, headers=self.headers)
            if response.status_code == 201:
                data = response.json()
                self.log_test("Flow Creation", True, f"Created flow: {data['label']}")
                self.created_resources.append(("flow", TEST_FLOW_ID))
                return True
            else:
                self.log_test("Flow Creation", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Flow Creation", False, str(e))
            return False
    
    def test_flow_tag_filtering(self) -> bool:
        """Test flow tag filtering functionality."""
        print("\n🔍 Testing Flow Tag Filtering")
        print("=" * 50)
        
        test_cases = [
            ("tag.environment=production", "flows with environment=production"),
            ("tag.priority=high", "flows with priority=high"),
            ("tag_exists.stream_type=true", "flows that have stream_type tag"),
            ("tag.environment=production&tag.department=engineering", "flows with multiple tag filters"),
        ]
        
        all_passed = True
        for query, description in test_cases:
            try:
                response = requests.get(f"{self.base_url}/flows?{query}", headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    count = len(data.get('data', []))
                    success = count > 0
                    self.log_test(f"Flow Filter: {description}", success, f"Found {count} flows")
                    if not success:
                        all_passed = False
                else:
                    self.log_test(f"Flow Filter: {description}", False, f"Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Flow Filter: {description}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_segment_creation(self) -> bool:
        """Test segment creation with tags."""
        print("\n📹 Testing Segment Creation with Tags")
        print("=" * 50)
        
        # Create test media file
        test_content = "This is test media content for TAMS API testing with tags and downloads"
        with open("test_media.txt", "w") as f:
            f.write(test_content)
        
        segments_data = [
            {
                "object_id": TEST_SEGMENT_1_ID,
                "timerange": "[0:0_10:0)",
                "sample_offset": 0,
                "sample_count": 250,
                "key_frame_count": 10
            },
            {
                "object_id": TEST_SEGMENT_2_ID,
                "timerange": "[10:0_20:0)",
                "sample_offset": 250,
                "sample_count": 250,
                "key_frame_count": 10
            }
        ]
        
        all_passed = True
        for i, segment_data in enumerate(segments_data, 1):
            try:
                # Create segment with file upload using multipart form
                with open("test_media.txt", "rb") as f:
                    files = {"file": ("test_media.txt", f, "text/plain")}
                    data = {"segment_data": json.dumps(segment_data)}
                    
                    response = requests.post(
                        f"{self.base_url}/flows/{TEST_FLOW_ID}/segments",
                        data=data,
                        files=files
                    )
                
                if response.status_code == 201:
                    self.log_test(f"Segment {i} Creation", True, f"Created segment: {segment_data['object_id']}")
                    self.created_resources.append(("segment", segment_data['object_id']))
                    
                    # Add tags to segment
                    segment_id = segment_data["object_id"]
                    tags = SEGMENT_TAGS_1 if i == 1 else SEGMENT_TAGS_2
                    
                    for tag_name, tag_value in tags.items():
                        tag_response = requests.put(
                            f"{self.base_url}/flows/{TEST_FLOW_ID}/segments/{segment_id}/tags/{tag_name}",
                            data=tag_value,
                            headers={"Content-Type": "text/plain"}
                        )
                        if tag_response.status_code == 200:
                            self.log_test(f"Segment {i} Tag: {tag_name}", True, f"Added {tag_name}={tag_value}")
                        else:
                            self.log_test(f"Segment {i} Tag: {tag_name}", False, f"Status: {tag_response.status_code}")
                            all_passed = False
                else:
                    self.log_test(f"Segment {i} Creation", False, f"Status: {response.status_code}, Response: {response.text}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Segment {i} Creation", False, str(e))
                all_passed = False
        
        # Clean up test file
        try:
            os.remove("test_media.txt")
        except:
            pass
        
        return all_passed
    
    def test_segment_tag_filtering(self) -> bool:
        """Test segment tag filtering functionality."""
        print("\n🔍 Testing Segment Tag Filtering")
        print("=" * 50)
        
        test_cases = [
            ("tag.environment=production", "segments with environment=production"),
            ("tag.quality=hd", "segments with quality=hd"),
            ("tag_exists.segment_type=true", "segments that have segment_type tag"),
            ("tag.environment=production&tag.quality=hd", "segments with multiple tag filters"),
        ]
        
        all_passed = True
        for query, description in test_cases:
            try:
                response = requests.get(f"{self.base_url}/flows/{TEST_FLOW_ID}/segments?{query}", headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    count = len(data)
                    success = count > 0
                    self.log_test(f"Segment Filter: {description}", success, f"Found {count} segments")
                    if not success:
                        all_passed = False
                else:
                    self.log_test(f"Segment Filter: {description}", False, f"Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Segment Filter: {description}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_url_generation(self) -> bool:
        """Test URL generation for segments."""
        print("\n🔗 Testing URL Generation")
        print("=" * 50)
        
        try:
            response = requests.get(f"{self.base_url}/flows/{TEST_FLOW_ID}/segments", headers=self.headers)
            if response.status_code == 200:
                segments = response.json()
                if segments and len(segments) > 0:
                    segment = segments[0]
                    if 'get_urls' in segment and segment['get_urls']:
                        # get_urls is an array of objects with 'url' and 'label' fields
                        get_urls = segment['get_urls']
                        get_url = None
                        head_url = None
                        
                        for url_obj in get_urls:
                            if 'GET' in url_obj.get('label', ''):
                                get_url = url_obj.get('url')
                            elif 'HEAD' in url_obj.get('label', ''):
                                head_url = url_obj.get('url')
                        
                        if get_url:
                            self.log_test("GET URL Generation", True, f"Generated GET URL: {get_url[:50]}...")
                        else:
                            self.log_test("GET URL Generation", False, "No GET URL found")
                        
                        if head_url:
                            self.log_test("HEAD URL Generation", True, f"Generated HEAD URL: {head_url[:50]}...")
                        else:
                            self.log_test("HEAD URL Generation", False, "No HEAD URL found")
                        
                        return get_url is not None and head_url is not None
                    else:
                        self.log_test("URL Generation", False, "No URLs found in segment")
                        return False
                else:
                    self.log_test("URL Generation", False, "No segments found")
                    return False
            else:
                self.log_test("URL Generation", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("URL Generation", False, str(e))
            return False
    
    def test_segment_download(self) -> bool:
        """Test segment download functionality."""
        print("\n⬇️ Testing Segment Download")
        print("=" * 50)
        
        try:
            # Get segments to find download URLs
            response = requests.get(f"{self.base_url}/flows/{TEST_FLOW_ID}/segments", headers=self.headers)
            if response.status_code != 200:
                self.log_test("Segment Download", False, f"Failed to get segments: {response.status_code}")
                return False
            
            segments = response.json()
            if not segments or len(segments) == 0:
                self.log_test("Segment Download", False, "No segments found for download")
                return False
            
            all_passed = True
            for i, segment in enumerate(segments[:2]):  # Test first 2 segments
                segment_id = segment.get('object_id', f'segment_{i}')
                
                # Test GET URL download
                if 'get_urls' in segment and segment['get_urls']:
                    get_urls = segment['get_urls']
                    get_url = None
                    head_url = None
                    
                    for url_obj in get_urls:
                        if 'GET' in url_obj.get('label', ''):
                            get_url = url_obj.get('url')
                        elif 'HEAD' in url_obj.get('label', ''):
                            head_url = url_obj.get('url')
                    
                    if get_url:
                        try:
                            # Download the segment
                            download_response = requests.get(get_url, timeout=30)
                            if download_response.status_code == 200:
                                # Save downloaded content
                                download_filename = f"downloaded_segment_{segment_id}.txt"
                                with open(download_filename, 'wb') as f:
                                    f.write(download_response.content)
                                
                                self.downloaded_files.append(download_filename)
                                
                                # Verify content
                                content = download_response.text
                                if "test media content" in content:
                                    self.log_test(f"Segment {i+1} Download (GET)", True, f"Downloaded {len(content)} bytes")
                                else:
                                    self.log_test(f"Segment {i+1} Download (GET)", False, "Downloaded content doesn't match expected")
                                    all_passed = False
                            else:
                                self.log_test(f"Segment {i+1} Download (GET)", False, f"Download failed: {download_response.status_code}")
                                all_passed = False
                        except Exception as e:
                            self.log_test(f"Segment {i+1} Download (GET)", False, f"Download error: {str(e)}")
                            all_passed = False
                    else:
                        self.log_test(f"Segment {i+1} Download (GET)", False, "No GET URL available")
                        all_passed = False
                
                # Test HEAD URL
                if head_url:
                    try:
                        head_response = requests.head(head_url, timeout=10)
                        if head_response.status_code == 200:
                            content_length = head_response.headers.get('content-length', 'unknown')
                            self.log_test(f"Segment {i+1} HEAD Request", True, f"Content-Length: {content_length}")
                        else:
                            self.log_test(f"Segment {i+1} HEAD Request", False, f"HEAD failed: {head_response.status_code}")
                            all_passed = False
                    except Exception as e:
                        self.log_test(f"Segment {i+1} HEAD Request", False, f"HEAD error: {str(e)}")
                        all_passed = False
                else:
                    self.log_test(f"Segment {i+1} HEAD Request", False, "No HEAD URL available")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.log_test("Segment Download", False, str(e))
            return False
    
    def test_cross_resource_tag_filtering(self) -> bool:
        """Test tag filtering across different resource types."""
        print("\n🔄 Testing Cross-Resource Tag Filtering")
        print("=" * 50)
        
        test_cases = [
            ("sources", "tag.environment=production", "production sources"),
            ("flows", "tag.environment=production", "production flows"),
            ("sources", "tag.department=engineering", "engineering sources"),
            ("flows", "tag.department=engineering", "engineering flows"),
        ]
        
        all_passed = True
        for resource_type, query, description in test_cases:
            try:
                if resource_type == "sources":
                    url = f"{self.base_url}/sources?{query}"
                elif resource_type == "flows":
                    url = f"{self.base_url}/flows?{query}"
                else:
                    continue
                
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    count = len(data.get('data', [])) if 'data' in data else len(data)
                    success = count > 0
                    self.log_test(f"Cross-Resource Filter: {description}", success, f"Found {count} {resource_type}")
                    if not success:
                        all_passed = False
                else:
                    self.log_test(f"Cross-Resource Filter: {description}", False, f"Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Cross-Resource Filter: {description}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def run_full_test(self) -> bool:
        """Run the complete end-to-end test suite."""
        print("🚀 TAMS API Full Workflow Test with Tags and Downloads")
        print("=" * 70)
        print(f"Testing against: {self.base_url}")
        print(f"Test started at: {datetime.now().isoformat()}")
        print()
        
        # Test sequence
        tests = [
            ("API Health Check", self.test_api_health),
            ("Source Creation", self.test_source_creation),
            ("Source Tag Filtering", self.test_source_tag_filtering),
            ("Flow Creation", self.test_flow_creation),
            ("Flow Tag Filtering", self.test_flow_tag_filtering),
            ("Segment Creation", self.test_segment_creation),
            ("Segment Tag Filtering", self.test_segment_tag_filtering),
            ("URL Generation", self.test_url_generation),
            ("Segment Download", self.test_segment_download),
            ("Cross-Resource Tag Filtering", self.test_cross_resource_tag_filtering),
        ]
        
        all_passed = True
        for test_name, test_func in tests:
            try:
                result = test_func()
                if not result:
                    all_passed = False
            except Exception as e:
                self.log_test(test_name, False, f"Exception: {str(e)}")
                all_passed = False
        
        # Cleanup
        self.cleanup_resources()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        passed_tests = sum(1 for result in self.test_results if result['success'])
        total_tests = len(self.test_results)
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if all_passed:
            print("\n🎉 All tests passed! TAMS API with tag functionality and downloads is working correctly.")
        else:
            print("\n⚠️ Some tests failed. Check the details above.")
        
        return all_passed


def main():
    """Main function to run the test suite."""
    try:
        runner = TAMSTestRunner()
        success = runner.run_full_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        runner.cleanup_resources()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
