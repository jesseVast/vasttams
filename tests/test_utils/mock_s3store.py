"""
Shared Mock S3Store for Testing

This module provides a centralized mock implementation of the S3Store
that can be imported and used across all test modules to ensure consistency.
"""

from unittest.mock import MagicMock, AsyncMock
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, BinaryIO
import io
import json

from app.models.models import FlowSegment


class MockS3Store:
    """Mock implementation of S3Store for testing"""
    
    def __init__(self):
        """Initialize mock store with test data"""
        self.test_data = {
            'buckets': {},
            'objects': {},
            'presigned_urls': {}
        }
        self.endpoint_url = "http://test-endpoint"
        self.bucket_name = "test-bucket"
        self.access_key_id = "test-key"
        self.secret_access_key = "test-secret"
        self.use_ssl = False
        
        # Mock S3 client
        self.s3_client = MagicMock()
        
        # Setup mock methods
        self._setup_mock_methods()
    
    def _setup_mock_methods(self):
        """Setup all mock methods with realistic behavior"""
        # Bucket operations
        self._ensure_bucket_exists = MagicMock(side_effect=self._mock_ensure_bucket_exists)
        self.create_bucket = MagicMock(side_effect=self._mock_create_bucket)
        self.delete_bucket = MagicMock(side_effect=self._mock_delete_bucket)
        self.list_buckets = MagicMock(side_effect=self._mock_list_buckets)
        
        # Object operations
        self.upload_file = MagicMock(side_effect=self._mock_upload_file)
        self.upload_fileobj = MagicMock(side_effect=self._mock_upload_fileobj)
        self.download_file = MagicMock(side_effect=self._mock_download_file)
        self.download_fileobj = MagicMock(side_effect=self._mock_download_fileobj)
        self.delete_object = MagicMock(side_effect=self._mock_delete_object)
        self.list_objects = MagicMock(side_effect=self._mock_list_objects)
        self.get_object = MagicMock(side_effect=self._mock_get_object)
        self.head_object = MagicMock(side_effect=self._mock_head_object)
        
        # URL operations
        self.generate_presigned_url = MagicMock(side_effect=self._mock_generate_presigned_url)
        self.generate_presigned_post = MagicMock(side_effect=self._mock_generate_presigned_post)
        
        # Segment operations
        self.store_segment = MagicMock(side_effect=self._mock_store_segment)
        self.retrieve_segment = MagicMock(side_effect=self._mock_retrieve_segment)
        self.delete_segment = MagicMock(side_effect=self._mock_delete_segment)
        
        # Utility operations
        self.get_object_size = MagicMock(side_effect=self._mock_get_object_size)
        self.object_exists = MagicMock(side_effect=self._mock_object_exists)
        self.copy_object = MagicMock(side_effect=self._mock_copy_object)
    
    def _mock_ensure_bucket_exists(self):
        """Mock bucket existence check"""
        if self.bucket_name not in self.test_data['buckets']:
            self.test_data['buckets'][self.bucket_name] = {
                'name': self.bucket_name,
                'created_at': datetime.now(timezone.utc),
                'objects': {}
            }
        return True
    
    def _mock_create_bucket(self, bucket_name: str) -> bool:
        """Mock bucket creation"""
        if bucket_name not in self.test_data['buckets']:
            self.test_data['buckets'][bucket_name] = {
                'name': bucket_name,
                'created_at': datetime.now(timezone.utc),
                'objects': {}
            }
            return True
        return False
    
    def _mock_delete_bucket(self, bucket_name: str) -> bool:
        """Mock bucket deletion"""
        if bucket_name in self.test_data['buckets']:
            # Check if bucket is empty
            bucket = self.test_data['buckets'][bucket_name]
            if not bucket['objects']:
                del self.test_data['buckets'][bucket_name]
                return True
        return False
    
    def _mock_list_buckets(self) -> List[str]:
        """Mock bucket listing"""
        return list(self.test_data['buckets'].keys())
    
    def _mock_upload_file(self, file_path: str, object_key: str, **kwargs) -> bool:
        """Mock file upload"""
        # Simulate file content
        file_content = f"Mock content for {file_path}".encode('utf-8')
        
        object_data = {
            'key': object_key,
            'bucket': self.bucket_name,
            'content': file_content,
            'size': len(file_content),
            'content_type': kwargs.get('ContentType', 'application/octet-stream'),
            'metadata': kwargs.get('Metadata', {}),
            'uploaded_at': datetime.now(timezone.utc)
        }
        
        self.test_data['objects'][object_key] = object_data
        
        # Add to bucket objects
        if self.bucket_name in self.test_data['buckets']:
            self.test_data['buckets'][self.bucket_name]['objects'][object_key] = object_data
        
        return True
    
    def _mock_upload_fileobj(self, file_obj: BinaryIO, object_key: str, **kwargs) -> bool:
        """Mock file object upload"""
        # Read content from file object
        file_obj.seek(0)
        file_content = file_obj.read()
        
        object_data = {
            'key': object_key,
            'bucket': self.bucket_name,
            'content': file_content,
            'size': len(file_content),
            'content_type': kwargs.get('ContentType', 'application/octet-stream'),
            'metadata': kwargs.get('Metadata', {}),
            'uploaded_at': datetime.now(timezone.utc)
        }
        
        self.test_data['objects'][object_key] = object_data
        
        # Add to bucket objects
        if self.bucket_name in self.test_data['buckets']:
            self.test_data['buckets'][self.bucket_name]['objects'][object_key] = object_data
        
        return True
    
    def _mock_download_file(self, object_key: str, file_path: str) -> bool:
        """Mock file download"""
        if object_key in self.test_data['objects']:
            object_data = self.test_data['objects'][object_key]
            # In a real test, you might write to the file_path
            # For mock purposes, we just return success
            return True
        return False
    
    def _mock_download_fileobj(self, object_key: str, file_obj: BinaryIO) -> bool:
        """Mock file object download"""
        if object_key in self.test_data['objects']:
            object_data = self.test_data['objects'][object_key]
            # Write content to file object
            file_obj.write(object_data['content'])
            file_obj.seek(0)
            return True
        return False
    
    def _mock_delete_object(self, object_key: str) -> bool:
        """Mock object deletion"""
        if object_key in self.test_data['objects']:
            del self.test_data['objects'][object_key]
            
            # Remove from bucket objects
            for bucket_name in self.test_data['buckets']:
                if object_key in self.test_data['buckets'][bucket_name]['objects']:
                    del self.test_data['buckets'][bucket_name]['objects'][object_key]
            
            return True
        return False
    
    def _mock_list_objects(self, prefix: str = "", **kwargs) -> List[Dict[str, Any]]:
        """Mock object listing"""
        objects = []
        for key, obj_data in self.test_data['objects'].items():
            if key.startswith(prefix):
                objects.append({
                    'Key': key,
                    'Size': obj_data['size'],
                    'LastModified': obj_data['uploaded_at'],
                    'ETag': f'"{uuid.uuid4()}"'
                })
        return objects
    
    def _mock_get_object(self, object_key: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Mock object retrieval"""
        if object_key in self.test_data['objects']:
            obj_data = self.test_data['objects'][object_key]
            return {
                'Body': io.BytesIO(obj_data['content']),
                'ContentLength': obj_data['size'],
                'ContentType': obj_data['content_type'],
                'Metadata': obj_data['metadata'],
                'LastModified': obj_data['uploaded_at']
            }
        return None
    
    def _mock_head_object(self, object_key: str) -> Optional[Dict[str, Any]]:
        """Mock object metadata retrieval"""
        if object_key in self.test_data['objects']:
            obj_data = self.test_data['objects'][object_key]
            return {
                'ContentLength': obj_data['size'],
                'ContentType': obj_data['content_type'],
                'Metadata': obj_data['metadata'],
                'LastModified': obj_data['uploaded_at']
            }
        return None
    
    def _mock_generate_presigned_url(self, operation: str, object_key: str, 
                                   expiration: int = 3600, **kwargs) -> str:
        """Mock presigned URL generation"""
        url_id = str(uuid.uuid4())
        presigned_url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}?presigned={url_id}"
        
        self.test_data['presigned_urls'][url_id] = {
            'operation': operation,
            'object_key': object_key,
            'expiration': expiration,
            'created_at': datetime.now(timezone.utc),
            'url': presigned_url
        }
        
        return presigned_url
    
    def _mock_generate_presigned_post(self, object_key: str, expiration: int = 3600, 
                                    **kwargs) -> Dict[str, Any]:
        """Mock presigned POST generation"""
        url_id = str(uuid.uuid4())
        
        post_data = {
            'url': f"https://{self.bucket_name}.s3.amazonaws.com",
            'fields': {
                'key': object_key,
                'policy': f"mock-policy-{url_id}",
                'x-amz-algorithm': 'AWS4-HMAC-SHA256',
                'x-amz-credential': f"{self.access_key_id}/20240101/us-east-1/s3/aws4_request",
                'x-amz-date': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
                'x-amz-signature': f"mock-signature-{url_id}"
            }
        }
        
        self.test_data['presigned_urls'][url_id] = {
            'operation': 'post',
            'object_key': object_key,
            'expiration': expiration,
            'created_at': datetime.now(timezone.utc),
            'post_data': post_data
        }
        
        return post_data
    
    def _mock_store_segment(self, segment: FlowSegment, file_content: bytes, 
                           content_type: str = "video/mp4") -> str:
        """Mock segment storage"""
        object_key = f"segments/{segment.object_id}/segment"
        
        object_data = {
            'key': object_key,
            'bucket': self.bucket_name,
            'content': file_content,
            'size': len(file_content),
            'content_type': content_type,
            'metadata': {
                'segment_id': segment.object_id,
                'timerange': segment.timerange,
                'storage_path': segment.storage_path
            },
            'uploaded_at': datetime.now(timezone.utc)
        }
        
        self.test_data['objects'][object_key] = object_data
        
        # Add to bucket objects
        if self.bucket_name in self.test_data['buckets']:
            self.test_data['buckets'][self.bucket_name]['objects'][object_key] = object_data
        
        return object_key
    
    def _mock_retrieve_segment(self, segment: FlowSegment) -> Optional[bytes]:
        """Mock segment retrieval"""
        object_key = f"segments/{segment.object_id}/segment"
        
        if object_key in self.test_data['objects']:
            return self.test_data['objects'][object_key]['content']
        return None
    
    def _mock_delete_segment(self, segment: FlowSegment) -> bool:
        """Mock segment deletion"""
        object_key = f"segments/{segment.object_id}/segment"
        return self._mock_delete_object(object_key)
    
    def _mock_get_object_size(self, object_key: str) -> Optional[int]:
        """Mock object size retrieval"""
        if object_key in self.test_data['objects']:
            return self.test_data['objects'][object_key]['size']
        return None
    
    def _mock_object_exists(self, object_key: str) -> bool:
        """Mock object existence check"""
        return object_key in self.test_data['objects']
    
    def _mock_copy_object(self, source_key: str, dest_key: str, 
                         source_bucket: str = None, **kwargs) -> bool:
        """Mock object copying"""
        source_bucket = source_bucket or self.bucket_name
        
        # Find source object
        source_object = None
        if source_bucket == self.bucket_name and source_key in self.test_data['objects']:
            source_object = self.test_data['objects'][source_key]
        
        if source_object:
            # Create copy
            dest_object = source_object.copy()
            dest_object['key'] = dest_key
            dest_object['copied_at'] = datetime.now(timezone.utc)
            
            self.test_data['objects'][dest_key] = dest_object
            
            # Add to bucket objects
            if self.bucket_name in self.test_data['buckets']:
                self.test_data['buckets'][self.bucket_name]['objects'][dest_key] = dest_object
            
            return True
        
        return False
    
    def reset_test_data(self):
        """Reset all test data to empty state"""
        self.test_data = {
            'buckets': {},
            'objects': {},
            'presigned_urls': {}
        }
        # Recreate default bucket
        self._mock_ensure_bucket_exists()
    
    def add_test_data(self, data_type: str, items: List[Any]):
        """Add test data of specified type"""
        if data_type == 'objects':
            for item in items:
                self.test_data['objects'][item['key']] = item
        elif data_type == 'buckets':
            for item in items:
                self.test_data['buckets'][item['name']] = item


# Global mock instance for easy import
mock_s3store = MockS3Store()
