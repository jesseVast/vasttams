#!/usr/bin/env python3
"""
TAMS Table Query Tool - Query and export data from TAMS tables.

This tool allows you to query any TAMS table and export the results in JSON or CSV format.

Usage:
    python mgmt/query_tables_sync.py --list-tables
    python mgmt/query_tables_sync.py --table sources --format json
    python mgmt/query_tables_sync.py --table flows --format csv --limit 100
    python mgmt/query_tables_sync.py --table users --format json --output users.json
    python mgmt/query_tables_sync.py --table segments --stats
"""

import sys
import os
import json
import csv
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the src directory to the path
root_dir = os.path.abspath(str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(root_dir) / "src"))
sys.path.insert(0, root_dir)

# Change to root directory so config/config.json is found
os.chdir(root_dir)

from vastdbmanager import VastDBManager

from vasttamsserver.core.config import get_settings


class TAMSTableQuery:
    """TAMS table query tool"""
    
    # Valid TAMS tables
    VALID_TABLES = [
        'sources', 'flows', 'segments', 'objects', 'flow_object_references',
        'flow_collections', 'source_collections', 'webhooks', 'deletion_requests',
        'users', 'api_tokens', 'refresh_tokens', 'auth_logs'
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self.db_manager = None
    
    def initialize(self):
        """Initialize database connection"""
        try:
            self.db_manager = VastDBManager(
                endpoints=[self.settings.vast_endpoint],
                access_key=self.settings.vast_access_key,
                secret_key=self.settings.vast_secret_key,
                bucket=self.settings.vast_bucket,
                schema=self.settings.vast_schema,
                enable_trino=True,  # Always enable Trino for queries
                trino_host=self.settings.trino_host,
                trino_port=self.settings.trino_port,
                trino_user=self.settings.trino_user,
                trino_catalog=self.settings.trino_catalog,
                auto_connect=True
            )
            print("✅ Connected to VAST database")
        except Exception as e:
            print(f"❌ Failed to connect to VAST database: {e}", file=sys.stderr)
            self.db_manager = None
    
    def close(self):
        """Close database connection"""
        if self.db_manager:
            try:
                # VastDBManager doesn't require explicit closing
                pass
            except Exception as e:
                print(f"Error closing VastDBManager: {e}", file=sys.stderr)
    
    def list_tams_tables(self) -> List[str]:
        """List all tables in the configured TAMS schema"""
        if not self.db_manager:
            return []
        try:
            tables = self.db_manager.list_tables()
            return sorted(tables)
        except Exception as e:
            print(f"❌ Error listing tables: {e}", file=sys.stderr)
            return []
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get statistics for a given table"""
        if not self.db_manager:
            return {}
        try:
            stats = self.db_manager.get_table_stats(table_name)
            print(f"📊 Statistics for table '{table_name}':")
            for key, value in stats.items():
                print(f"   {key}: {value}")
            return stats
        except Exception as e:
            print(f"❌ Error getting table stats: {e}", file=sys.stderr)
            return {}
    
    def query_table(self, table_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query table data using query builder"""
        try:
            # Use query builder to select all columns
            query_builder = self.db_manager.query(table_name)
            
            # Apply limit if specified
            if limit and limit > 0:
                query_builder = query_builder.limit(limit)
            
            # Execute the query
            result = query_builder.execute()
            
            if not result:
                return []
            
            # Convert result to list of records
            records = []
            if isinstance(result, dict):
                # Handle Trino result format with 'data' key
                if 'data' in result and isinstance(result['data'], list):
                    # Direct list of records
                    records = result['data']
                elif 'data' in result and isinstance(result['data'], dict):
                    # Columnar format - convert to row format
                    data = result['data']
                    num_records = len(next(iter(data.values()))) if data else 0
                    
                    for i in range(num_records):
                        record = {}
                        for key, values in data.items():
                            if hasattr(values, '__len__') and i < len(values):
                                record[key] = values[i]
                            else:
                                record[key] = values
                        records.append(record)
            
            return records
            
        except Exception as e:
            print(f"❌ Error querying table {table_name}: {e}", file=sys.stderr)
            return []
    
    def output_json(self, data: List[Dict[str, Any]], output_file: Optional[str] = None):
        """Output data in JSON format"""
        output = json.dumps(data, indent=2, default=str)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            print(f"✅ Data written to {output_file}")
        else:
            print(output)
    
    def output_csv(self, data: List[Dict[str, Any]], output_file: Optional[str] = None):
        """Output data in CSV format"""
        if not data:
            print("No data to output.", file=sys.stderr)
            return
        
        fieldnames = list(data[0].keys())
        
        if output_file:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            print(f"✅ Data written to {output_file}")
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)


def main():
    parser = argparse.ArgumentParser(
        description="TAMS Table Query Tool - Query and export data from TAMS tables.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mgmt/query_tables_sync.py --list-tables
  python mgmt/query_tables_sync.py --table sources --format json
  python mgmt/query_tables_sync.py --table flows --format csv --limit 100
  python mgmt/query_tables_sync.py --table users --format json --output users.json
  python mgmt/query_tables_sync.py --table segments --stats
        """
    )
    parser.add_argument('--list-tables', action='store_true', help='List all available TAMS tables')
    parser.add_argument('--table', type=str, help='Specify the table to query (e.g., sources, flows)')
    parser.add_argument('--format', type=str, choices=['json', 'csv'], default='json', help='Output format (json or csv)')
    parser.add_argument('--output', type=str, help='Output file path (if not specified, output to stdout)')
    parser.add_argument('--limit', type=int, help='Limit the number of records returned')
    parser.add_argument('--stats', action='store_true', help='Show table statistics instead of data')
    
    args = parser.parse_args()
    
    query_tool = TAMSTableQuery()
    query_tool.initialize()
    
    if not query_tool.db_manager:
        return 1  # Exit with error
    
    try:
        if args.list_tables:
            tables = query_tool.list_tams_tables()
            print("📋 Available TAMS tables:")
            for table in tables:
                print(f"   • {table}")
            print(f"\nTotal: {len(tables)} tables")
        elif args.table:
            if args.stats:
                query_tool.get_table_stats(args.table)
            else:
                print(f"🔍 Querying table '{args.table}'...")
                data = query_tool.query_table(args.table, args.limit)
                print(f"✅ Found {len(data)} records")
                if data:
                    if args.format == 'json':
                        query_tool.output_json(data, args.output)
                    elif args.format == 'csv':
                        query_tool.output_csv(data, args.output)
                else:
                    print("No records found.")
        else:
            parser.print_help()
    finally:
        query_tool.close()


if __name__ == "__main__":
    main()
