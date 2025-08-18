"""Table operations for VastDBManager"""

import logging
from typing import Dict, List, Optional
from pyarrow import Schema

logger = logging.getLogger(__name__)


class TableOperations:
    """Handles table creation, schema evolution, and projections"""
    
    def __init__(self, connection_manager):
        """Initialize table operations with connection manager"""
        self.connection_manager = connection_manager
    
    def create_table(self, table_name: str, schema: Schema, projections: Optional[Dict[str, List[str]]] = None):
        """Create a new table with VAST projections for optimal performance, or evolve existing table schema"""
        try:
            if not self.connection_manager.is_connected():
                raise RuntimeError("Not connected to VAST database")
            
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                
                # Check if table already exists
                existing_table = schema_obj.table(table_name, fail_if_missing=False)
                
                if existing_table is not None:
                    # Get current table schema for comparison
                    current_schema = existing_table.columns()
                    
                    # Check if we need to evolve the schema
                    if self._schemas_match(current_schema, schema):
                        logger.info(f"Table {table_name} already exists with matching schema, skipping creation")
                        return existing_table
                    else:
                        # Schema has changed - evolve the table instead of dropping it
                        logger.info(f"Table {table_name} schema changed, evolving table structure")
                        evolved_table = self._evolve_table_schema(existing_table, current_schema, schema)
                        return evolved_table
                
                # Create new table
                table = schema_obj.create_table(table_name, schema)
                
                # Add VAST projections if specified
                if projections:
                    self._add_vast_projections(table, projections)
                
                logger.info(f"Created table {table_name} with projections: {list(projections.keys()) if projections else 'none'}")
                return table
                
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            raise
    
    def _evolve_table_schema(self, existing_table, current_schema: Schema, new_schema: Schema):
        """Evolve an existing table's schema by adding new columns"""
        try:
            logger.info(f"Evolving table schema for {existing_table.name}")
            
            # Get current and new field names
            current_fields = {field.name for field in current_schema}
            new_fields = {field.name for field in new_schema}
            
            # Find fields that need to be added
            fields_to_add = new_fields - current_fields
            
            if not fields_to_add:
                logger.info("No new fields to add")
                return existing_table
            
            logger.info(f"Adding {len(fields_to_add)} new fields: {fields_to_add}")
            
            # Add new columns to the existing table
            for field_name in fields_to_add:
                # Find the field definition in the new schema
                new_field = next(field for field in new_schema if field.name == field_name)
                
                try:
                    # Add the new column with a default value
                    existing_table.add_column(field_name, new_field.type)
                    logger.info(f"Added column {field_name} with type {new_field.type}")
                except Exception as e:
                    logger.warning(f"Failed to add column {field_name}: {e}")
                    # Continue with other columns
            
            logger.info(f"Successfully evolved table {existing_table.name}")
            return existing_table
            
        except Exception as e:
            logger.error(f"Error evolving table schema: {e}")
            # Return the existing table if evolution fails
            return existing_table
    
    def _schemas_match(self, current_schema: Schema, new_schema: Schema) -> bool:
        """Compare two schemas to determine if they're compatible"""
        try:
            # Convert schemas to comparable format
            current_fields = {field.name: field.type for field in current_schema}
            new_fields = {field.name: field.type for field in new_schema}
            
            # Check if all new fields exist in current schema with same type
            for field_name, field_type in new_fields.items():
                if field_name not in current_fields:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("New field %s not in current schema", field_name)
                    return False
                
                # Compare field types (allowing for some type compatibility)
                if not self._types_compatible(current_fields[field_name], field_type):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Field %s type changed: %s -> %s", field_name, current_fields[field_name], field_type)
                    return False
            
            logger.debug("Schemas are compatible")
            return True
            
        except Exception as e:
            logger.warning(f"Error comparing schemas: {e}")
            return False
    
    def _types_compatible(self, current_type, new_type) -> bool:
        """Check if two PyArrow types are compatible"""
        try:
            # For now, use simple string comparison
            # In the future, this could be enhanced with type compatibility rules
            return str(current_type) == str(new_type)
        except Exception:
            return False
    
    def _add_vast_projections(self, table, projections: Dict[str, List[str]]):
        """Add VAST projections using the actual SDK methods for optimal performance"""
        try:
            for projection_name, columns in projections.items():
                # Determine which columns should be sorted vs unsorted
                # Time-series columns (timestamp) should be sorted for optimal performance
                sorted_columns = []
                unsorted_columns = []
                
                for col in columns:
                    if 'time' in col.lower() or 'timestamp' in col.lower():
                        sorted_columns.append(col)
                    else:
                        unsorted_columns.append(col)
                
                # Create the projection using VAST's actual API
                table.create_projection(
                    projection_name=projection_name,
                    sorted_columns=sorted_columns,
                    unsorted_columns=unsorted_columns
                )
                
                logger.info(f"Created VAST projection '{projection_name}' with {len(sorted_columns)} sorted, {len(unsorted_columns)} unsorted columns")
            
            logger.info(f"Successfully added {len(projections)} projections to table")
            
        except Exception as e:
            logger.warning(f"Failed to add VAST projections: {e}")
            # Continue without projections if they fail
    
    def get_table_projections(self, table_name: str) -> List[str]:
        """Get list of projection names for a table"""
        try:
            if not self.connection_manager.is_connected():
                return []
            
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                table = schema_obj.table(table_name)
                
                # Get projection information using VAST's actual API
                projections = list(table.projections())
                return [p.name for p in projections] if projections else []
                
        except Exception as e:
            logger.error(f"Failed to get projections for table {table_name}: {e}")
            return []
    
    def add_projection(self, table_name: str, projection_name: str, columns: List[str]):
        """Add a new projection to an existing table"""
        try:
            if not self.connection_manager.is_connected():
                raise RuntimeError("Not connected to VAST database")
            
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                table = schema_obj.table(table_name)
                
                # Determine sorted vs unsorted columns
                sorted_columns = []
                unsorted_columns = []
                
                for col in columns:
                    if 'time' in col.lower() or 'timestamp' in col.lower():
                        sorted_columns.append(col)
                    else:
                        unsorted_columns.append(col)
                
                # Create projection using VAST's actual API
                table.create_projection(
                    projection_name=projection_name,
                    sorted_columns=sorted_columns,
                    unsorted_columns=unsorted_columns
                )
                
                logger.info(f"Added projection '{projection_name}' to table {table_name}")
                
        except Exception as e:
            logger.error(f"Failed to add projection {projection_name} to table {table_name}: {e}")
            raise

    def drop_projection(self, table_name: str, projection_name: str):
        """Drop (delete) a projection from an existing table"""
        try:
            if not self.connection_manager.is_connected():
                raise RuntimeError("Not connected to VAST database")
            
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                table = schema_obj.table(table_name)
                
                # Get the projection object and drop it using VAST's actual API
                projection = table.projection(projection_name)
                projection.drop()
                
                logger.info(f"Dropped projection '{projection_name}' from table {table_name}")
                
        except Exception as e:
            logger.error(f"Failed to drop projection {projection_name} from table {table_name}: {e}")
            raise
