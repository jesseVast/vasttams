#!/usr/bin/env python3
"""
Service Layer Tests for Tag Storage Service

Tests common/tags/service.py to achieve coverage.
Uses mocks to test business logic without database dependencies.
"""

import pytest
import sys
import json
import uuid
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.common.tags.service import TagStorageService
from vasttamsserver.common.models import Tags


# Helper to generate TAMS-compliant UUIDs
def tams_uuid():
    """Generate a TAMS-compliant UUID string"""
    return str(uuid.uuid4())


class TestTagStorageService:
    """Test TagStorageService business logic"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database"""
        db = Mock()
        db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        db.execute_sql = Mock()
        db.insert_record = Mock()
        return db
    
    @pytest.fixture
    def mock_s3(self):
        """Create a mock S3 client"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db, mock_s3):
        """Create TagStorageService instance"""
        return TagStorageService(mock_db, mock_s3)
    
    @pytest.fixture
    def source_id(self):
        """Generate a TAMS-compliant source ID"""
        return tams_uuid()
    
    @pytest.fixture
    def flow_id(self):
        """Generate a TAMS-compliant flow ID"""
        return tams_uuid()
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_columnar_format(self, service, mock_db, source_id):
        """Test get_entity_tags with columnar format (Trino)"""
        # Columnar format result
        mock_db.execute_sql.return_value = {
            'data': {
                'tag_name': ['environment', 'version'],
                'tag_value': ['production', '1.0.0']
            }
        }
        
        tags = await service.get_entity_tags("source", source_id)
        
        assert tags is not None
        assert tags.root['environment'] == 'production'
        assert tags.root['version'] == '1.0.0'
        mock_db.execute_sql.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_columnar_format_with_json_array(self, service, mock_db, source_id):
        """Test get_entity_tags with JSON array values"""
        # Columnar format with JSON array
        mock_db.execute_sql.return_value = {
            'data': {
                'tag_name': ['categories'],
                'tag_value': ['["news", "sports"]']
            }
        }
        
        tags = await service.get_entity_tags("source", source_id)
        
        assert tags is not None
        assert tags.root['categories'] == ["news", "sports"]
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_row_format(self, service, mock_db, source_id):
        """Test get_entity_tags with row-oriented format"""
        # Row-oriented format result
        mock_db.execute_sql.return_value = {
            'data': [
                {'tag_name': 'environment', 'tag_value': 'production'},
                {'tag_name': 'version', 'tag_value': '1.0.0'}
            ]
        }
        
        tags = await service.get_entity_tags("source", source_id)
        
        assert tags is not None
        assert tags.root['environment'] == 'production'
        assert tags.root['version'] == '1.0.0'
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_empty_result(self, service, mock_db, source_id):
        """Test get_entity_tags with empty result"""
        mock_db.execute_sql.return_value = {'data': {}}
        
        tags = await service.get_entity_tags("source", source_id)
        
        assert tags is None
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_no_data(self, service, mock_db, source_id):
        """Test get_entity_tags with no data"""
        mock_db.execute_sql.return_value = {}
        
        tags = await service.get_entity_tags("source", source_id)
        
        assert tags is None
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_exception(self, service, mock_db, source_id):
        """Test get_entity_tags handles exceptions"""
        mock_db.execute_sql.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            await service.get_entity_tags("source", source_id)
    
    @pytest.mark.asyncio
    async def test_update_entity_tags_success(self, service, mock_db, source_id):
        """Test update_entity_tags successfully updates tags"""
        tags = Tags({"environment": "production", "version": "1.0.0"})
        
        result = await service.update_entity_tags("source", source_id, tags)
        
        assert result is True
        # Should delete existing tags first
        assert mock_db.execute_sql.call_count >= 1
        # Should insert new tags
        assert mock_db.insert_record.call_count == 2
    
    @pytest.mark.asyncio
    async def test_update_entity_tags_with_array_values(self, service, mock_db, source_id):
        """Test update_entity_tags with array tag values"""
        tags = Tags({"categories": ["news", "sports"]})
        
        result = await service.update_entity_tags("source", source_id, tags)
        
        assert result is True
        # Check that array was serialized to JSON
        insert_calls = mock_db.insert_record.call_args_list
        assert len(insert_calls) == 1
        tag_data = insert_calls[0][0][1]
        assert tag_data['tag_value'] == '["news", "sports"]'
    
    @pytest.mark.asyncio
    async def test_update_entity_tags_empty_tags(self, service, mock_db, source_id):
        """Test update_entity_tags with empty tags"""
        tags = Tags({})
        
        result = await service.update_entity_tags("source", source_id, tags)
        
        assert result is True
        # Should delete existing tags but not insert any
        assert mock_db.execute_sql.call_count >= 1
        assert mock_db.insert_record.call_count == 0
    
    @pytest.mark.asyncio
    async def test_update_entity_tags_invalid_tags(self, service, mock_db, source_id):
        """Test update_entity_tags with invalid tags raises ValueError"""
        # Mock validate_tags to return invalid
        with patch('vasttams.common.tags.service.validate_tags') as mock_validate:
            mock_validate.return_value = (False, ["Invalid tag name"])
            tags = Tags({"invalid!tag": "value"})
            
            with pytest.raises(ValueError):
                await service.update_entity_tags("source", source_id, tags)
    
    @pytest.mark.asyncio
    async def test_get_entity_tag_success(self, service, source_id):
        """Test get_entity_tag retrieves a specific tag"""
        tags = Tags({"environment": "production"})
        
        with patch.object(service, 'get_entity_tags', return_value=tags):
            tag_value = await service.get_entity_tag("source", source_id, "environment")
            
            assert tag_value == "production"
    
    @pytest.mark.asyncio
    async def test_get_entity_tag_not_found(self, service, source_id):
        """Test get_entity_tag returns None when tag doesn't exist"""
        tags = Tags({"version": "1.0.0"})
        
        with patch.object(service, 'get_entity_tags', return_value=tags):
            tag_value = await service.get_entity_tag("source", source_id, "environment")
            
            assert tag_value is None
    
    @pytest.mark.asyncio
    async def test_get_entity_tag_no_tags(self, service, source_id):
        """Test get_entity_tag returns None when entity has no tags"""
        with patch.object(service, 'get_entity_tags', return_value=None):
            tag_value = await service.get_entity_tag("source", source_id, "environment")
            
            assert tag_value is None
    
    @pytest.mark.asyncio
    async def test_update_entity_tag_success(self, service, source_id):
        """Test update_entity_tag updates a specific tag"""
        existing_tags = Tags({"environment": "staging"})
        
        with patch.object(service, 'get_entity_tags', return_value=existing_tags):
            with patch.object(service, 'update_entity_tags', return_value=True) as mock_update:
                result = await service.update_entity_tag("source", source_id, "environment", "production")
                
                assert result is True
                mock_update.assert_called_once()
                # Check that the tag was updated in the tags object
                updated_tags = mock_update.call_args[0][2]
                assert updated_tags.root["environment"] == "production"
    
    @pytest.mark.asyncio
    async def test_update_entity_tag_new_tag(self, service, source_id):
        """Test update_entity_tag creates new tag if it doesn't exist"""
        with patch.object(service, 'get_entity_tags', return_value=None):
            with patch.object(service, 'update_entity_tags', return_value=True) as mock_update:
                result = await service.update_entity_tag("source", source_id, "environment", "production")
                
                assert result is True
                mock_update.assert_called_once()
                updated_tags = mock_update.call_args[0][2]
                assert updated_tags.root["environment"] == "production"
    
    @pytest.mark.asyncio
    async def test_delete_entity_tag_success(self, service, source_id):
        """Test delete_entity_tag removes a tag"""
        existing_tags = Tags({"environment": "production", "version": "1.0.0"})
        
        with patch.object(service, 'get_entity_tags', return_value=existing_tags):
            with patch.object(service, 'update_entity_tags', return_value=True) as mock_update:
                result = await service.delete_entity_tag("source", source_id, "environment")
                
                assert result is True
                mock_update.assert_called_once()
                updated_tags = mock_update.call_args[0][2]
                assert "environment" not in updated_tags.root
                assert "version" in updated_tags.root
    
    @pytest.mark.asyncio
    async def test_delete_entity_tag_not_found(self, service, source_id):
        """Test delete_entity_tag returns False when tag doesn't exist"""
        existing_tags = Tags({"version": "1.0.0"})
        
        with patch.object(service, 'get_entity_tags', return_value=existing_tags):
            result = await service.delete_entity_tag("source", source_id, "environment")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_entity_tag_no_tags(self, service, source_id):
        """Test delete_entity_tag returns False when entity has no tags"""
        with patch.object(service, 'get_entity_tags', return_value=None):
            result = await service.delete_entity_tag("source", source_id, "environment")
            
            assert result is False
    
    # Convenience method tests
    @pytest.mark.asyncio
    async def test_get_source_tags(self, service, source_id):
        """Test get_source_tags convenience method"""
        tags = Tags({"environment": "production"})
        
        with patch.object(service, 'get_entity_tags', return_value=tags) as mock_get:
            result = await service.get_source_tags(source_id)
            
            assert result == tags
            mock_get.assert_called_once_with("source", source_id)
    
    @pytest.mark.asyncio
    async def test_get_flow_tags(self, service, flow_id):
        """Test get_flow_tags convenience method"""
        tags = Tags({"format": "video"})
        
        with patch.object(service, 'get_entity_tags', return_value=tags) as mock_get:
            result = await service.get_flow_tags(flow_id)
            
            assert result == tags
            mock_get.assert_called_once_with("flow", flow_id)
    
    @pytest.mark.asyncio
    async def test_query_entities_by_tags(self, service, mock_db):
        """Test query_entities_by_tags"""
        source_id_1 = tams_uuid()
        source_id_2 = tams_uuid()
        mock_db.execute_sql.return_value = {
            'data': [
                {'id': source_id_1, 'label': 'Source 1'},
                {'id': source_id_2, 'label': 'Source 2'}
            ]
        }
        
        # Mock the function that's imported inside the method
        with patch('vasttams.common.tags.manager.generate_sql_tag_query') as mock_generate:
            mock_generate.return_value = "SELECT * FROM sources WHERE ..."
            
            results = await service.query_entities_by_tags("source", {"environment": "production"})
            
            assert len(results) == 2
            assert results[0]['id'] == source_id_1
    
    @pytest.mark.asyncio
    async def test_query_sources_by_tags(self, service, source_id):
        """Test query_sources_by_tags convenience method"""
        with patch.object(service, 'query_entities_by_tags', return_value=[]) as mock_query:
            await service.query_sources_by_tags({"environment": "production"})
            
            mock_query.assert_called_once_with("source", {"environment": "production"}, 100)
    
    @pytest.mark.asyncio
    async def test_query_flows_by_tags(self, service, source_id):
        """Test query_flows_by_tags convenience method"""
        with patch.object(service, 'query_entities_by_tags', return_value=[]) as mock_query:
            await service.query_flows_by_tags({"format": "video"})
            
            mock_query.assert_called_once_with("flow", {"format": "video"}, 100)
    
    @pytest.mark.asyncio
    async def test_get_tag_analytics(self, service, mock_db):
        """Test get_tag_analytics"""
        source_id_1 = tams_uuid()
        source_id_2 = tams_uuid()
        mock_db.query.return_value.select.return_value.execute.return_value = [
            {'id': source_id_1, 'tags': {'environment': 'production'}},
            {'id': source_id_2, 'tags': {'environment': 'staging'}}
        ]
        
        with patch('vasttams.common.tags.service.get_tag_manager') as mock_manager:
            mock_tag_manager = Mock()
            mock_tag_manager.get_tag_analytics.return_value = {
                'total_tags': 2,
                'unique_tags': ['environment']
            }
            mock_manager.return_value = mock_tag_manager
            
            analytics = await service.get_tag_analytics("sources")
            
            assert analytics['entity_type'] == 'sources'
            assert analytics['total_entities'] == 2
    
    @pytest.mark.asyncio
    async def test_get_standardized_tags(self, service):
        """Test get_standardized_tags"""
        with patch('vasttams.common.tags.service.get_tag_manager') as mock_manager:
            mock_tag_manager = Mock()
            mock_definition = Mock()
            mock_definition.name = "environment"
            mock_definition.description = "Environment tag"
            mock_definition.data_type = "string"
            mock_definition.required = False
            mock_definition.allowed_values = None
            mock_definition.pattern = None
            mock_definition.examples = ["production", "staging"]
            mock_definition.deprecated = False
            mock_definition.replacement = None
            
            mock_tag_manager.get_standardized_tags.return_value = {
                "environment": mock_definition
            }
            mock_manager.return_value = mock_tag_manager
            
            result = await service.get_standardized_tags()
            
            assert "environment" in result
            assert result["environment"]["name"] == "environment"
            assert result["environment"]["data_type"] == "string"
    
    @pytest.mark.asyncio
    async def test_create_tag_proposal(self, service):
        """Test create_tag_proposal"""
        with patch('vasttams.common.tags.service.get_tag_manager') as mock_manager:
            mock_tag_manager = Mock()
            mock_proposal = Mock()
            mock_proposal.name = "new_tag"
            mock_proposal.description = "A new tag"
            mock_proposal.data_type = "string"
            mock_proposal.justification = "Needed for X"
            mock_proposal.examples = ["example1"]
            mock_proposal.proposed_by = "user123"
            mock_proposal.proposed_at.isoformat.return_value = "2024-01-01T00:00:00"
            mock_proposal.status = "pending"
            
            mock_tag_manager.create_tag_proposal.return_value = mock_proposal
            mock_manager.return_value = mock_tag_manager
            
            result = await service.create_tag_proposal(
                name="new_tag",
                description="A new tag",
                data_type="string",
                justification="Needed for X",
                examples=["example1"],
                proposed_by="user123"
            )
            
            assert result["name"] == "new_tag"
            assert result["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_row_oriented_format(self):
        """Test get_entity_tags with row-oriented format (else branch)"""
        entity_id = tams_uuid()
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Row-oriented format
        mock_db.execute_sql.return_value = {
            'data': [
                {'tag_name': 'category', 'tag_value': 'test'},
                {'tag_name': 'priority', 'tag_value': 'high'}
            ]
        }
        
        service = TagStorageService(mock_db, Mock())
        tags = await service.get_entity_tags("source", entity_id)
        
        assert tags is not None
        assert tags.root['category'] == 'test'
        assert tags.root['priority'] == 'high'
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_row_oriented_json_array(self):
        """Test get_entity_tags with row-oriented format and JSON array value"""
        entity_id = tams_uuid()
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Row-oriented format with JSON array
        mock_db.execute_sql.return_value = {
            'data': [
                {'tag_name': 'categories', 'tag_value': '["test", "demo"]'}
            ]
        }
        
        service = TagStorageService(mock_db, Mock())
        tags = await service.get_entity_tags("source", entity_id)
        
        assert tags is not None
        assert tags.root['categories'] == ["test", "demo"]
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_row_oriented_list_value(self):
        """Test get_entity_tags with row-oriented format and list value"""
        entity_id = tams_uuid()
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Row-oriented format with list value
        mock_db.execute_sql.return_value = {
            'data': [
                {'tag_name': 'categories', 'tag_value': ['test', 'demo']}
            ]
        }
        
        service = TagStorageService(mock_db, Mock())
        tags = await service.get_entity_tags("source", entity_id)
        
        assert tags is not None
        assert tags.root['categories'] == ['test', 'demo']
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_row_oriented_unexpected_format(self):
        """Test get_entity_tags with row-oriented format and unexpected row format"""
        entity_id = tams_uuid()
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Unexpected row format (missing tag_name or tag_value)
        mock_db.execute_sql.return_value = {
            'data': [
                {'tag_name': 'category', 'tag_value': 'test'},
                {'unexpected': 'format'}  # Missing required fields
            ]
        }
        
        service = TagStorageService(mock_db, Mock())
        tags = await service.get_entity_tags("source", entity_id)
        
        # Should still return tags from valid rows
        assert tags is not None
        assert tags.root['category'] == 'test'
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_columnar_json_parse_error(self):
        """Test get_entity_tags handles JSON parse errors in columnar format"""
        entity_id = tams_uuid()
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Columnar format with invalid JSON
        mock_db.execute_sql.return_value = {
            'data': {
                'tag_name': ['category'],
                'tag_value': ['invalid-json-{']  # Invalid JSON
            }
        }
        
        service = TagStorageService(mock_db, Mock())
        tags = await service.get_entity_tags("source", entity_id)
        
        # Should handle error gracefully and use string value
        assert tags is not None
        assert tags.root['category'] == 'invalid-json-{'
    
    @pytest.mark.asyncio
    async def test_get_entity_tag_tags_none(self):
        """Test get_entity_tag when tags is None"""
        entity_id = tams_uuid()
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql.return_value = {'data': {}}  # No tags
        
        service = TagStorageService(mock_db, Mock())
        tag_value = await service.get_entity_tag("source", entity_id, "category")
        
        assert tag_value is None
    
    @pytest.mark.asyncio
    async def test_update_entity_tag_current_tags_none(self):
        """Test update_entity_tag when current_tags is None"""
        entity_id = tams_uuid()
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock()
        mock_db.insert_record = Mock()
        mock_db.execute_sql.return_value = {'data': {}}  # No tags
        
        service = TagStorageService(mock_db, Mock())
        result = await service.update_entity_tag("source", entity_id, "category", "test")
        
        assert result is True
        assert mock_db.insert_record.called
    
    @pytest.mark.asyncio
    async def test_update_entity_tag_current_tags_root_none(self):
        """Test update_entity_tag when current_tags.root is None"""
        entity_id = tams_uuid()
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock()
        mock_db.insert_record = Mock()
        
        from vasttamsserver.common.models import Tags
        mock_tags = Tags({})
        mock_tags.root = None
        
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        # Mock get_entity_tags to return Tags with None root
        service = TagStorageService(mock_db, Mock())
        with patch.object(service, 'get_entity_tags', return_value=mock_tags):
            result = await service.update_entity_tag("source", entity_id, "category", "test")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_entity_tag_not_found(self):
        """Test delete_entity_tag when tag doesn't exist"""
        entity_id = tams_uuid()
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql.return_value = {'data': {}}  # No tags
        
        service = TagStorageService(mock_db, Mock())
        result = await service.delete_entity_tag("source", entity_id, "nonexistent")
        
        assert result is False

