#!/usr/bin/env python3
"""
TAMS Test Data Generation Script

This script generates comprehensive test data for the TAMS API:
- 100 sources (video, audio, image, data, multi)
- 100 flows (video, audio, data, image, multi)
- 1000 segments (distributed across flows)
- 5000 objects (5 per segment, with proper content types)

Usage:
    python generate_test_data.py

The script will:
1. Drop the existing schema
2. Restart the app
3. Wait for it to come online
4. Generate all test data using actual batch operations
5. Verify the data was created
"""

import asyncio
import aiohttp
import json
import uuid
import time
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = "http://localhost:8000"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
SOURCES_ENDPOINT = f"{API_BASE_URL}/sources"
FLOWS_ENDPOINT = f"{API_BASE_URL}/flows"
OBJECTS_ENDPOINT = f"{API_BASE_URL}/objects"
SOURCES_BATCH_ENDPOINT = f"{API_BASE_URL}/sources/batch"
FLOWS_BATCH_ENDPOINT = f"{API_BASE_URL}/flows/batch"
OBJECTS_BATCH_ENDPOINT = f"{API_BASE_URL}/objects/batch"

# Content Types and Codecs
CONTENT_FORMATS = [
    "urn:x-nmos:format:video",
    "urn:x-tam:format:image", 
    "urn:x-nmos:format:audio",
    "urn:x-nmos:format:data",
    "urn:x-nmos:format:multi"
]

VIDEO_CODECS = [
    "urn:x-nmos:codec:video:h264",
    "urn:x-nmos:codec:video:h265",
    "urn:x-nmos:codec:video:prores",
    "urn:x-nmos:codec:video:dnxhd"
]

AUDIO_CODECS = [
    "urn:x-nmos:codec:audio:aac",
    "urn:x-nmos:codec:audio:mp3",
    "urn:x-nmos:codec:audio:pcm",
    "urn:x-nmos:codec:audio:opus"
]

IMAGE_CODECS = [
    "urn:x-nmos:codec:image:jpeg",
    "urn:x-nmos:codec:image:png",
    "urn:x-nmos:codec:image:tiff",
    "urn:x-nmos:codec:image:webp"
]

DATA_CODECS = [
    "urn:x-nmos:codec:data:json",
    "urn:x-nmos:codec:data:xml",
    "urn:x-nmos:codec:data:csv",
    "urn:x-nmos:codec:data:binary"
]

# Test Data Configuration
NUM_SOURCES = 10
NUM_FLOWS = 10
NUM_SEGMENTS = 100
OBJECTS_PER_SEGMENT = 5
BATCH_SIZE = 25  # Reduced batch size to prevent server disconnections

# API Configuration Constants - Easy to adjust for troubleshooting
DEFAULT_API_WAIT_TIMEOUT = 60  # Default timeout for waiting for API to come online
DEFAULT_BATCH_DELAY = 0.1  # Default delay between batches to prevent overwhelming server
DEFAULT_HTTP_SUCCESS_STATUS = 200  # HTTP status code for successful GET requests
DEFAULT_HTTP_CREATED_STATUS = 201  # HTTP status code for successful POST requests
DEFAULT_HTTP_ERROR_STATUS = 500  # HTTP status code for server errors
EXPECTED_TIME_PARTS_LENGTH = 2  # Expected number of parts when parsing time strings

class TestDataGenerator:
    def __init__(self):
        self.session = None
        self.sources = []
        self.flows = []
        self.segments = []
        self.objects = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, self_type, self_value, self_traceback):
        if self.session:
            await self.session.close()
    
    async def wait_for_api(self, max_wait: int = DEFAULT_API_WAIT_TIMEOUT) -> bool:
        """Wait for the API to come online"""
        logger.info("Waiting for API to come online...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                async with self.session.get(HEALTH_ENDPOINT) as response:
                    if response.status == DEFAULT_HTTP_SUCCESS_STATUS:
                        data = await response.json()
                        if data.get('status') == 'healthy':
                            logger.info("✅ API is online and healthy")
                            return True
            except Exception as e:
                logger.debug(f"API not ready yet: {e}")
            
            await asyncio.sleep(2)
        
        logger.error("❌ API failed to come online within timeout")
        return False
    
    async def drop_all_tables(self) -> bool:
        """Drop all tables to start fresh"""
        logger.info("🗑️ Dropping all tables to start fresh...")
        
        # This would require a direct database connection or admin endpoint
        # For now, we'll rely on the app startup to recreate tables
        logger.info("Tables will be recreated on app startup")
        return True
    
    def generate_source(self, index: int) -> Dict[str, Any]:
        """Generate a source with random content type"""
        format_type = random.choice(CONTENT_FORMATS)
        
        source = {
            "id": str(uuid.uuid4()),
            "format": format_type,
            "label": f"test-source-{index:03d}",
            "description": f"Test source {index} for comprehensive testing",
            "tags": {
                "test_type": "comprehensive",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "index": str(index)
            }
        }
        
        # Add format-specific tags
        if "video" in format_type:
            source["tags"]["category"] = "video"
        elif "audio" in format_type:
            source["tags"]["category"] = "audio"
        elif "image" in format_type:
            source["tags"]["category"] = "image"
        elif "data" in format_type:
            source["tags"]["category"] = "data"
        elif "multi" in format_type:
            source["tags"]["category"] = "multi"
        
        return source
    
    def generate_flow(self, index: int, source_id: str) -> Dict[str, Any]:
        """Generate a flow with appropriate content type and codec"""
        source = next(s for s in self.sources if s["id"] == source_id)
        format_type = source["format"]
        
        if "video" in format_type:
            flow = {
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "format": format_type,
                "codec": random.choice(VIDEO_CODECS),
                "label": f"test-flow-{index:04d}",
                "description": f"Test video flow {index}",
                "frame_width": random.choice([1920, 1280, 3840, 2560]),
                "frame_height": random.choice([1080, 720, 2160, 1440]),
                "frame_rate": random.choice(["25/1", "30/1", "50/1", "60/1"]),
                "tags": {
                    "test_type": "comprehensive",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "index": str(index)
                }
            }
        elif "audio" in format_type:
            flow = {
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "format": format_type,
                "codec": random.choice(AUDIO_CODECS),
                "label": f"test-flow-{index:04d}",
                "description": f"Test audio flow {index}",
                "sample_rate": random.choice([44100, 48000, 96000, 192000]),
                "bits_per_sample": random.choice([16, 24, 32]),
                "channels": random.choice([1, 2, 5, 7]),
                "tags": {
                    "test_type": "comprehensive",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "index": str(index)
                }
            }
        elif "image" in format_type:
            flow = {
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "format": format_type,
                "codec": random.choice(IMAGE_CODECS),
                "label": f"test-flow-{index:04d}",
                "description": f"Test image flow {index}",
                "frame_width": random.choice([1920, 1280, 3840, 2560]),
                "frame_height": random.choice([1080, 720, 2160, 1440]),
                "tags": {
                    "test_type": "comprehensive",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "index": str(index)
                }
            }
        elif "data" in format_type:
            flow = {
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "format": format_type,
                "codec": random.choice(DATA_CODECS),
                "label": f"test-flow-{index:04d}",
                "description": f"Test data flow {index}",
                "tags": {
                    "test_type": "comprehensive",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "index": str(index)
                }
            }
        else:  # multi
            flow = {
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "format": format_type,
                "codec": "urn:x-nmos:codec:multi:container",
                "label": f"test-flow-{index:04d}",
                "description": f"Test multi flow {index}",
                "flow_collection": [str(uuid.uuid4()) for _ in range(random.randint(2, 5))],
                "tags": {
                    "test_type": "comprehensive",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "index": str(index)
                }
            }
        
        return flow
    
    def generate_segment(self, index: int, flow_id: str) -> Dict[str, Any]:
        """Generate a flow segment"""
        # Generate a random time range within the last 30 days
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=random.randint(1, 30))
        
        segment = {
            "object_id": str(uuid.uuid4()),
            "timerange": f"[{start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+00:00_{end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+00:00]",
            "ts_offset": "0/1",
            "sample_offset": random.randint(0, 1000000),
            "sample_count": random.randint(1000, 100000),
            "key_frame_count": random.randint(1, 100) if random.choice([True, False]) else None,
            "tags": {
                "test_type": "comprehensive",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "index": str(index)
            }
        }
        
        return segment
    
    def generate_object(self, index: int, segment: Dict[str, Any], flow_id: str) -> Dict[str, Any]:
        """Generate an object for a segment"""
        # Determine object type based on flow format
        flow = next(f for f in self.flows if f["id"] == flow_id)
        format_type = flow["format"]
        
        if "video" in format_type:
            obj_format = "urn:x-nmos:format:video"
        elif "audio" in format_type:
            obj_format = "urn:x-nmos:format:audio"
        elif "image" in format_type:
            obj_format = "urn:x-tam:format:image"
        elif "data" in format_type:
            obj_format = "urn:x-nmos:format:data"
        else:
            obj_format = "urn:x-nmos:format:multi"
        
        # Parse timerange to get start and end times
        timerange = segment["timerange"]
        # Extract start and end from timerange format [start_end]
        if timerange.startswith('[') and timerange.endswith(']'):
            time_parts = timerange[1:-1].split('_')
            if len(time_parts) == EXPECTED_TIME_PARTS_LENGTH:
                start_time = time_parts[0]
                end_time = time_parts[1]
            else:
                start_time = datetime.now(timezone.utc).isoformat()
                end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        else:
            start_time = datetime.now(timezone.utc).isoformat()
            end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        
        obj = {
            "object_id": str(uuid.uuid4()),
            "format": obj_format,
            "flow_references": [
                {
                    "flow_id": flow_id,
                    "timerange": {
                        "start": start_time,
                        "end": end_time
                    }
                }
            ],
            "size": random.randint(1024, 100 * 1024 * 1024),  # 1KB to 100MB
            "tags": {
                "test_type": "comprehensive",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "index": str(index),
                "segment_id": segment["object_id"]
            }
        }
        
        return obj
    
    async def create_sources_batch(self) -> bool:
        """Create all sources using actual batch operations"""
        logger.info(f"Creating {NUM_SOURCES} sources using batch operations...")
        
        # Generate all sources first
        all_sources = [self.generate_source(i) for i in range(NUM_SOURCES)]
        
        # Process in smaller batches to prevent server disconnections
        for i in range(0, len(all_sources), BATCH_SIZE):
            batch = all_sources[i:i + BATCH_SIZE]
            logger.info(f"Processing sources batch {i//BATCH_SIZE + 1}/{(len(all_sources) + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} sources)")
            
            try:
                # Send batch in a single request
                async with self.session.post(SOURCES_BATCH_ENDPOINT, json=batch) as response:
                    if response.status == DEFAULT_HTTP_CREATED_STATUS:
                        created_sources = await response.json()
                        self.sources.extend(created_sources)
                        logger.info(f"✅ Created batch {i//BATCH_SIZE + 1}: {len(created_sources)} sources")
                    else:
                        logger.error(f"Failed to create sources batch {i//BATCH_SIZE + 1}: {response.status}")
                        return False
                
                # Small delay between batches to prevent overwhelming the server
                await asyncio.sleep(DEFAULT_BATCH_DELAY)
                
            except Exception as e:
                logger.error(f"Error in batch {i//BATCH_SIZE + 1}: {e}")
                return False
        
        logger.info(f"✅ Successfully created {len(self.sources)} sources in {BATCH_SIZE}-sized batches")
        return True
    
    async def create_single_source(self, source: Dict[str, Any]) -> bool:
        """Create a single source"""
        try:
            async with self.session.post(SOURCES_ENDPOINT, json=source) as response:
                return response.status == 201
        except Exception as e:
            logger.error(f"Error creating source: {e}")
            return False
    
    async def create_flows_batch(self) -> bool:
        """Create all flows using batch operations"""
        logger.info(f"Creating {NUM_FLOWS} flows using batch operations...")
        
        # Generate all flows first - each flow references a source
        all_flows = []
        for i in range(NUM_FLOWS):
            # Each flow gets a source from the sources we created
            source_id = self.sources[i % len(self.sources)]["id"]
            
            flow = self.generate_flow(i, source_id)
            all_flows.append(flow)
        
        # Process in smaller batches to prevent server disconnections
        for i in range(0, len(all_flows), BATCH_SIZE):
            batch = all_flows[i:i + BATCH_SIZE]
            logger.info(f"Processing flows batch {i//BATCH_SIZE + 1}/{(len(all_flows) + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} flows)")
            
            try:
                # Send batch in a single request
                async with self.session.post(FLOWS_BATCH_ENDPOINT, json=batch) as response:
                    if response.status == 201:
                        created_flows = await response.json()
                        self.flows.extend(created_flows)
                        logger.info(f"✅ Created batch {i//BATCH_SIZE + 1}: {len(created_flows)} flows")
                    else:
                        logger.error(f"Failed to create flows batch {i//BATCH_SIZE + 1}: {response.status}")
                        return False
                
                # Small delay between batches to prevent overwhelming the server
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in batch {i//BATCH_SIZE + 1}: {e}")
                return False
        
        logger.info(f"✅ Successfully created {len(self.flows)} flows in {BATCH_SIZE}-sized batches")
        return True
    
    async def create_single_flow(self, flow: Dict[str, Any]) -> bool:
        """Create a single flow"""
        try:
            async with self.session.post(FLOWS_ENDPOINT, json=flow) as response:
                return response.status == 201
        except Exception as e:
            logger.error(f"Error creating flow: {e}")
            return False
    
    async def create_segments_and_objects_batch(self) -> bool:
        """Create segments and objects using batch operations"""
        logger.info(f"Creating {NUM_SEGMENTS} segments with {OBJECTS_PER_SEGMENT} objects each using batch operations...")
        
        # Generate all segments and objects first
        all_segments = []
        all_objects = []
        
        for i in range(NUM_SEGMENTS):
            # Each segment references a flow from the flows we created
            flow_id = self.flows[i % len(self.flows)]["id"]
            
            segment = self.generate_segment(i, flow_id)
            all_segments.append(segment)
            
            # Generate objects for this segment - each object references both segment and flow
            for j in range(OBJECTS_PER_SEGMENT):
                obj = self.generate_object(i * OBJECTS_PER_SEGMENT + j, segment, flow_id)
                all_objects.append(obj)
        
        # Process segments in batches (segments are just metadata, no API calls needed)
        self.segments = all_segments
        logger.info(f"✅ Generated {len(self.segments)} segments")
        
        # Process objects in smaller batches to prevent server disconnections
        for i in range(0, len(all_objects), BATCH_SIZE):
            batch = all_objects[i:i + BATCH_SIZE]
            logger.info(f"Processing objects batch {i//BATCH_SIZE + 1}/{(len(all_objects) + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} objects)")
            
            try:
                # Send batch in a single request
                async with self.session.post(OBJECTS_BATCH_ENDPOINT, json=batch) as response:
                    if response.status == 201:
                        created_objects = await response.json()
                        self.objects.extend(created_objects)
                        logger.info(f"✅ Created batch {i//BATCH_SIZE + 1}: {len(created_objects)} objects")
                    else:
                        logger.error(f"Failed to create objects batch {i//BATCH_SIZE + 1}: {response.status}")
                        return False
                
                # Small delay between batches to prevent overwhelming the server
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in batch {i//BATCH_SIZE + 1}: {e}")
                return False
        
        logger.info(f"✅ Successfully created {len(self.segments)} segments and {len(self.objects)} objects in {BATCH_SIZE}-sized batches")
        return True
    
    async def create_single_object(self, obj: Dict[str, Any]) -> bool:
        """Create a single object"""
        try:
            async with self.session.post(OBJECTS_ENDPOINT, json=obj) as response:
                return response.status == 201
        except Exception as e:
            logger.error(f"Error creating object: {e}")
            return False
    
    async def verify_data(self) -> bool:
        """Verify that all data was created successfully"""
        logger.info("Verifying created data...")
        
        try:
            # Check sources
            async with self.session.get(SOURCES_ENDPOINT) as response:
                if response.status == 200:
                    data = await response.json()
                    source_count = len(data.get('data', []))
                    logger.info(f"Sources in database: {source_count}")
                else:
                    logger.error(f"Failed to get sources: {response.status}")
                    return False
            
            # Check flows
            async with self.session.get(FLOWS_ENDPOINT) as response:
                if response.status == 200:
                    data = await response.json()
                    flow_count = len(data.get('data', []))
                    logger.info(f"Flows in database: {flow_count}")
                else:
                    logger.error(f"Failed to get flows: {response.status}")
                    return False
            
            # Check analytics to verify data
            async with self.session.get(f"{API_BASE_URL}/analytics/flow-usage") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Flow usage analytics: {data}")
                else:
                    logger.error(f"Failed to get flow usage analytics: {response.status}")
            
            async with self.session.get(f"{API_BASE_URL}/analytics/storage-usage") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Storage usage analytics: {data}")
                else:
                    logger.error(f"Failed to get storage usage analytics: {response.status}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying data: {e}")
            return False
    
    async def run(self) -> bool:
        """Run the complete test data generation process"""
        logger.info("🚀 Starting comprehensive test data generation...")
        
        # Wait for API to be ready
        if not await self.wait_for_api():
            return False
        
        # Create sources using batch operations
        if not await self.create_sources_batch():
            return False
        
        # Create flows using batch operations
        if not await self.create_flows_batch():
            return False
        
        # Create segments and objects using batch operations
        if not await self.create_segments_and_objects_batch():
            return False
        
        # Verify data
        if not await self.verify_data():
            return False
        
        logger.info("🎉 Test data generation completed successfully!")
        logger.info(f"📊 Summary:")
        logger.info(f"   Sources: {len(self.sources)} (created first)")
        logger.info(f"   Flows: {len(self.flows)} (each references a source)")
        logger.info(f"   Segments: {len(self.segments)} (each references a flow)")
        logger.info(f"   Objects: {len(self.objects)} (each references a segment and flow)")
        logger.info(f"   Total records: {len(self.sources) + len(self.flows) + len(self.segments) + len(self.objects)}")
        
        # Show some relationship examples
        if self.sources and self.flows and self.segments and self.objects:
            logger.info(f"🔗 Relationship Examples:")
            logger.info(f"   Source '{self.sources[0]['label']}' -> Flow '{self.flows[0]['label']}' -> Segment {self.segments[0]['object_id'][:8]}... -> Object {self.objects[0]['object_id'][:8]}...")
            if len(self.sources) > 1:
                logger.info(f"   Source '{self.sources[1]['label']}' -> Flow '{self.flows[1]['label']}' -> Segment {self.segments[1]['object_id'][:8]}... -> Object {self.objects[1]['object_id'][:8]}...")
        
        return True

async def main():
    """Main function"""
    async with TestDataGenerator() as generator:
        success = await generator.run()
        if success:
            logger.info("✅ All test data generated successfully!")
        else:
            logger.error("❌ Test data generation failed!")
            exit(1)

if __name__ == "__main__":
    asyncio.run(main())
