"""
Core S3 operations without any TAMS-specific logic

This module provides pure S3 infrastructure operations that can be used
by any application, not just TAMS.
"""

import boto3
import logging
from typing import Optional, Dict, Any, List, BinaryIO, Union
from botocore.exceptions import ClientError, NoCredentialsError
import json
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class S3Core:
    """
    Core S3 operations without any TAMS-specific logic
    
    This class provides pure S3 infrastructure operations that can be used
    by any application. It handles only S3-specific concerns like:
    - Connection management
    - Basic CRUD operations
    - Presigned URL generation
    - Bucket management
    """
    
    # Configuration Constants - Easy to adjust for troubleshooting
    DEFAULT_S3_TIMEOUT = 30  # Default S3 operation timeout in seconds
    DEFAULT_UPLOAD_TIMEOUT = 3600  # 1 hour for uploads
    DEFAULT_DOWNLOAD_TIMEOUT = 3600  # 1 hour for downloads
    DEFAULT_MAX_RETRIES = 3  # Default maximum retry attempts for S3 operations
    DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024  # Default chunk size for multipart uploads (8MB)
    DEFAULT_MAX_CONCURRENT_PARTS = 10  # Default maximum concurrent parts for multipart uploads
    
    def __init__(self, endpoint_url: str, access_key_id: str, secret_access_key: str, 
                 bucket_name: str, use_ssl: bool = True):
        """
        Initialize S3 Core with connection parameters
        
        Args:
            endpoint_url: S3 endpoint URL
            access_key_id: S3 access key ID
            secret_access_key: S3 secret access key
            bucket_name: S3 bucket name
            use_ssl: Whether to use SSL for connections
        """
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        self.use_ssl = use_ssl
        
        logger.info("S3Core initialization - Endpoint: %s, Bucket: %s, Access Key: %s", 
                   self.endpoint_url, self.bucket_name, self.access_key_id)
        
        # Initialize S3 client
        try:
            session = boto3.session.Session()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Created boto3 session: %s", session)
            
            self.s3_client = session.client(
                service_name='s3',
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                endpoint_url=self.endpoint_url,
                config=boto3.session.Config(
                    s3={'addressing_style': 'path'}
                )
            )
            logger.info("Created S3 client: %s", self.s3_client)
            
            self._ensure_bucket_exists()
            logger.info("S3 Core initialized with endpoint: %s, bucket: %s", 
                       self.endpoint_url, self.bucket_name)
        except Exception as e:
            logger.error("Failed to initialize S3 Core: %s", e)
            import traceback
            logger.error("Traceback: %s", traceback.format_exc())
            raise
    
    def _ensure_bucket_exists(self):
        """Ensure the S3 bucket exists, create if it doesn't"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info("Bucket '%s' already exists", self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info("Created bucket '%s'", self.bucket_name)
                except ClientError as create_error:
                    logger.error("Failed to create bucket '%s': %s", self.bucket_name, create_error)
                    raise
            else:
                logger.error("Error checking bucket '%s': %s", self.bucket_name, e)
                raise
    
    def upload_object(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        """
        Upload data to S3 with the specified key
        
        Args:
            key: S3 object key
            data: Data to upload
            content_type: MIME type of the data
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type
            )
            logger.info("Successfully uploaded object: %s (%d bytes)", key, len(data))
            return True
        except Exception as e:
            logger.error("Failed to upload object %s: %s", key, e)
            return False
    
    def download_object(self, key: str) -> Optional[bytes]:
        """
        Download data from S3 with the specified key
        
        Args:
            key: S3 object key
            
        Returns:
            bytes: Downloaded data or None if failed
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            data = response['Body'].read()
            logger.info("Successfully downloaded object: %s (%d bytes)", key, len(data))
            return data
        except Exception as e:
            logger.error("Failed to download object %s: %s", key, e)
            return None
    
    def delete_object(self, key: str) -> bool:
        """
        Delete object from S3 with the specified key
        
        Args:
            key: S3 object key
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info("Successfully deleted object: %s", key)
            return True
        except Exception as e:
            logger.error("Failed to delete object %s: %s", key, e)
            return False
    
    def object_exists(self, key: str) -> bool:
        """
        Check if object exists in S3
        
        Args:
            key: S3 object key
            
        Returns:
            bool: True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error("Error checking object existence for %s: %s", key, e)
                return False
        except Exception as e:
            logger.error("Unexpected error checking object existence for %s: %s", key, e)
            return False
    
    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[str]:
        """
        List objects in S3 with the specified prefix
        
        Args:
            prefix: Object key prefix to filter by
            max_keys: Maximum number of keys to return
            
        Returns:
            List[str]: List of object keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            if 'Contents' in response:
                keys = [obj['Key'] for obj in response['Contents']]
                logger.info("Listed %d objects with prefix '%s'", len(keys), prefix)
                return keys
            else:
                logger.info("No objects found with prefix '%s'", prefix)
                return []
        except Exception as e:
            logger.error("Failed to list objects with prefix '%s': %s", prefix, e)
            return []
    
    def generate_presigned_url(self, key: str, operation: str = "get_object", 
                              expires: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for S3 operations
        
        Args:
            key: S3 object key
            operation: S3 operation (get_object, put_object, etc.)
            expires: URL expiration time in seconds
            
        Returns:
            str: Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires
            )
            logger.info("Generated presigned URL for %s operation on %s (expires in %d seconds)", 
                       operation, key, expires)
            return url
        except Exception as e:
            logger.error("Failed to generate presigned URL for %s operation on %s: %s", 
                        operation, key, e)
            return None
    
    def get_object_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for an S3 object
        
        Args:
            key: S3 object key
            
        Returns:
            Dict: Object metadata or None if failed
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            metadata = {
                'content_length': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {})
            }
            logger.info("Retrieved metadata for object: %s", key)
            return metadata
        except Exception as e:
            logger.error("Failed to get metadata for object %s: %s", key, e)
            return None
    
    def copy_object(self, source_key: str, destination_key: str) -> bool:
        """
        Copy an object within the same bucket
        
        Args:
            source_key: Source object key
            destination_key: Destination object key
            
        Returns:
            bool: True if copy successful, False otherwise
        """
        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=destination_key
            )
            logger.info("Successfully copied object from %s to %s", source_key, destination_key)
            return True
        except Exception as e:
            logger.error("Failed to copy object from %s to %s: %s", source_key, destination_key, e)
            return False
    
    def get_bucket_info(self) -> Dict[str, Any]:
        """
        Get information about the S3 bucket
        
        Returns:
            Dict: Bucket information
        """
        try:
            response = self.s3_client.head_bucket(Bucket=self.bucket_name)
            return {
                'bucket_name': self.bucket_name,
                'endpoint_url': self.endpoint_url,
                'region': response.get('ResponseMetadata', {}).get('HTTPHeaders', {}).get('x-amz-bucket-region'),
                'exists': True
            }
        except Exception as e:
            logger.error("Failed to get bucket info for %s: %s", self.bucket_name, e)
            return {
                'bucket_name': self.bucket_name,
                'endpoint_url': self.endpoint_url,
                'exists': False,
                'error': str(e)
            }
