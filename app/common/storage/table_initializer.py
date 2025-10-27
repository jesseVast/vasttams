"""
TAMS Table Initialization Service

This module handles the creation and initialization of all TAMS database tables
based on the Pydantic models. It provides business logic for table management
without being part of the vaststore infrastructure.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .schemas import get_tams_table_schemas, get_table_projections
from ...core.config import get_settings

logger = logging.getLogger(__name__)


class TAMSTableInitializer:
    """
    Handles initialization and management of TAMS database tables.
    
    This service provides business logic for table creation, schema validation,
    and projection management based on the TAMS data models.
    """
    
    def __init__(self, vast_db):
        """
        Initialize the table initializer.
        
        Args:
            vast_db: VastDBManager instance for database operations
        """
        self.vast_db = vast_db
        self.settings = get_settings()
        self.table_schemas = get_tams_table_schemas()
        self.table_projections = get_table_projections()
    
    async def initialize_all_tables(self, force_recreate: bool = False) -> Dict[str, bool]:
        """
        Initialize all TAMS tables with their schemas and projections.
        
        Args:
            force_recreate: If True, drop and recreate existing tables
            
        Returns:
            Dict[str, bool]: Results of table creation for each table
        """
        logger.info("Starting TAMS table initialization...")
        
        results = {}
        
        try:
            # Create tables in dependency order
            table_order = [
                "users", "api_tokens", "refresh_tokens", "auth_logs",  # Auth tables first
                "sources", "flows", "objects",  # Core entity tables
                "segments", "flow_object_references",  # Relationship tables
                "flow_collections", "source_collections",  # Collection tables
                "webhooks", "deletion_requests",  # Utility tables
                "tags"  # Tags table for metadata
            ]
            
            for table_name in table_order:
                if table_name in self.table_schemas:
                    try:
                        success = await self._create_table_with_projections(
                            table_name, 
                            force_recreate
                        )
                        results[table_name] = success
                        
                        if success:
                            logger.info(f"✅ Successfully initialized table: {table_name}")
                        else:
                            logger.error(f"❌ Failed to initialize table: {table_name}")
                            
                    except Exception as e:
                        logger.error(f"❌ Error initializing table {table_name}: {e}")
                        results[table_name] = False
                else:
                    logger.warning(f"⚠️ No schema found for table: {table_name}")
                    results[table_name] = False
            
            # Summary
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            
            logger.info(f"Table initialization complete: {successful}/{total} tables successful")
            
            if successful == total:
                logger.info("🎉 All TAMS tables initialized successfully!")
            else:
                failed_tables = [name for name, success in results.items() if not success]
                logger.warning(f"⚠️ Some tables failed to initialize: {failed_tables}")
            
            return results
            
        except Exception as e:
            logger.error(f"Critical error during table initialization: {e}")
            raise
    
    async def _create_table_with_projections(self, table_name: str, force_recreate: bool = False) -> bool:
        """
        Create a single table with its schema and projections.
        
        Args:
            table_name: Name of the table to create
            force_recreate: If True, drop existing table before creating
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if table_name not in self.table_schemas:
                logger.error(f"No schema found for table: {table_name}")
                return False
            
            schema = self.table_schemas[table_name]
            projections_list = self.table_projections.get(table_name, [])
            
            # Convert projections from List[List[str]] to Dict[str, List[str]]
            projections = {}
            for i, projection_columns in enumerate(projections_list):
                projection_name = f"projection_{i+1}"
                projections[projection_name] = projection_columns
            
            # Check if table already exists
            existing_tables = self.vast_db.list_tables()
            
            if table_name in existing_tables:
                if force_recreate:
                    logger.info(f"Dropping existing table: {table_name}")
                    await self._drop_table(table_name)
                else:
                    logger.info(f"Table {table_name} already exists, skipping creation")
                    return True
            
            # Create the table
            logger.info(f"Creating table: {table_name}")
            table = self.vast_db.create_table(table_name, schema, projections)
            
            if table is None:
                logger.error(f"Failed to create table: {table_name}")
                return False
            
            # Add projections if enabled
            if self.settings.enable_table_projections and projections:
                await self._add_table_projections(table_name, projections)
            
            logger.info(f"Successfully created table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            return False
    
    async def _drop_table(self, table_name: str) -> bool:
        """
        Drop a table from the database.
        
        Args:
            table_name: Name of the table to drop
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Note: VastDBManager doesn't have a drop_table method in the current interface
            # This would need to be implemented in the VastDBManager if needed
            logger.warning(f"Table dropping not implemented for: {table_name}")
            return False
        except Exception as e:
            logger.error(f"Error dropping table {table_name}: {e}")
            return False
    
    async def _add_table_projections(self, table_name: str, projections: List[List[str]]) -> bool:
        """
        Add projections to a table for performance optimization.
        
        Args:
            table_name: Name of the table
            projections: List of projection column combinations
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not projections:
                return True
            
            logger.info(f"Adding projections to table: {table_name}")
            
            for i, projection_columns in enumerate(projections):
                projection_name = f"{table_name}_{'_'.join(projection_columns)}_proj"
                
                try:
                    self.vast_db.add_projection(table_name, projection_name, projection_columns)
                    logger.debug(f"Added projection: {projection_name}")
                except Exception as e:
                    logger.warning(f"Failed to add projection {projection_name}: {e}")
                    # Continue with other projections
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding projections to table {table_name}: {e}")
            return False
    
    async def verify_tables_exist(self) -> Dict[str, bool]:
        """
        Verify that all required TAMS tables exist in the database.
        
        Returns:
            Dict[str, bool]: Status of each required table
        """
        logger.info("Verifying TAMS tables exist...")
        
        try:
            existing_tables = set(self.vast_db.list_tables())
            required_tables = set(self.table_schemas.keys())
            
            results = {}
            for table_name in required_tables:
                exists = table_name in existing_tables
                results[table_name] = exists
                
                if exists:
                    logger.debug(f"✅ Table exists: {table_name}")
                else:
                    logger.warning(f"❌ Table missing: {table_name}")
            
            missing_tables = [name for name, exists in results.items() if not exists]
            if missing_tables:
                logger.warning(f"Missing tables: {missing_tables}")
            else:
                logger.info("✅ All required TAMS tables exist")
            
            return results
            
        except Exception as e:
            logger.error(f"Error verifying tables: {e}")
            return {table_name: False for table_name in self.table_schemas.keys()}
    
    async def get_table_info(self) -> Dict[str, Dict]:
        """
        Get information about all TAMS tables.
        
        Returns:
            Dict[str, Dict]: Information about each table
        """
        logger.info("Getting TAMS table information...")
        
        try:
            table_info = {}
            
            for table_name in self.table_schemas.keys():
                try:
                    # Get table stats
                    stats = self.vast_db.get_table_stats(table_name)
                    
                    # Get projections
                    projections = self.vast_db.get_table_projections(table_name)
                    
                    table_info[table_name] = {
                        "exists": True,
                        "stats": stats,
                        "projections": projections,
                        "schema_fields": len(self.table_schemas[table_name])
                    }
                    
                except Exception as e:
                    logger.warning(f"Error getting info for table {table_name}: {e}")
                    table_info[table_name] = {
                        "exists": False,
                        "error": str(e)
                    }
            
            return table_info
            
        except Exception as e:
            logger.error(f"Error getting table information: {e}")
            return {}
    
    def get_required_tables(self) -> List[str]:
        """
        Get list of all required TAMS table names.
        
        Returns:
            List[str]: List of required table names
        """
        return list(self.table_schemas.keys())
    
    def get_table_schema(self, table_name: str) -> Optional[object]:
        """
        Get the PyArrow schema for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            PyArrow schema or None if not found
        """
        return self.table_schemas.get(table_name)
