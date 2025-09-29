#!/usr/bin/env python3
"""
TAMS Table Query Tool

A comprehensive script to query any TAMS table and output results in JSON or CSV format.
Supports all TAMS tables: sources, flows, segments, objects, users, etc.

Usage:
    python query_tables.py --table sources --format json
    python query_tables.py --table flows --format csv --output flows.csv
    python query_tables.py --table segments --format json --limit 100
    python query_tables.py --list-tables
    python query_tables.py --table users --format json --stats

Options:
    --table TABLE       Table name to query (sources, flows, segments, objects, users, etc.)
    --format FORMAT     Output format: json, csv (default: json)
    --output FILE       Output file path (default: stdout)
    --limit N           Limit number of records returned (default: no limit)
    --stats             Show table statistics
    --list-tables       List all available tables
    --help              Show this help message
"""

import asyncio
import sys
import json
import csv
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.vaststore.vastdbmanager import VastDBManager
from app.core.config import get_settings


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
    
    async def initialize(self):
        """Initialize database connection"""
        try:
            self.db_manager = VastDBManager(
                endpoints=[self.settings.vast_endpoint],
                access_key=self.settings.vast_access_key,
                secret_key=self.settings.vast_secret_key,
                bucket=self.settings.vast_bucket,
                schema=self.settings.vast_schema,
                auto_connect=True
            )
            print("✅ Connected to VAST database", file=sys.stderr)
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}", file=sys.stderr)
            sys.exit(1)
    
    async def list_tables(self):
        """List all available tables"""
        try:
            tables = self.db_manager.list_tables()
            print("📋 Available TAMS tables:")
            for table in sorted(tables):
                print(f"   • {table}")
            print(f"\nTotal: {len(tables)} tables")
        except Exception as e:
            print(f"❌ Error listing tables: {e}", file=sys.stderr)
            sys.exit(1)
    
    async def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get table statistics"""
        try:
            stats = self.db_manager.get_table_stats(table_name)
            return stats
        except Exception as e:
            print(f"❌ Error getting table stats: {e}", file=sys.stderr)
            return {}
    
    async def query_table(self, table_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
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
                # Get the length of the first column to determine number of records
                first_key = next(iter(result.keys()))
                if first_key != '$row_id' and hasattr(result[first_key], '__len__'):
                    num_records = len(result[first_key])
                    
                    for i in range(num_records):
                        record = {}
                        for key, values in result.items():
                            if key != '$row_id':  # Skip internal row IDs
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
            print(f"✅ JSON output written to {output_file}", file=sys.stderr)
        else:
            print(output)
    
    def output_csv(self, data: List[Dict[str, Any]], output_file: Optional[str] = None):
        """Output data in CSV format"""
        if not data:
            if output_file:
                with open(output_file, 'w') as f:
                    f.write("")
                print(f"✅ Empty CSV written to {output_file}", file=sys.stderr)
            return
        
        # Get all unique keys from all records
        all_keys = set()
        for record in data:
            all_keys.update(record.keys())
        fieldnames = sorted(all_keys)
        
        if output_file:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            print(f"✅ CSV output written to {output_file}", file=sys.stderr)
        else:
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            print(output.getvalue())
    
    async def close(self):
        """Close database connection"""
        if self.db_manager:
            try:
                if hasattr(self.db_manager, 'close'):
                    self.db_manager.close()
            except Exception as e:
                print(f"Warning: Error closing database connection: {e}", file=sys.stderr)


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="TAMS Table Query Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--table', '-t',
        choices=TAMSTableQuery.VALID_TABLES,
        help='Table name to query'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['json', 'csv'],
        default='json',
        help='Output format (default: json)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file path (default: stdout)'
    )
    
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Limit number of records returned'
    )
    
    parser.add_argument(
        '--stats', '-s',
        action='store_true',
        help='Show table statistics'
    )
    
    parser.add_argument(
        '--list-tables',
        action='store_true',
        help='List all available tables'
    )
    
    args = parser.parse_args()
    
    # Initialize query tool
    query_tool = TAMSTableQuery()
    await query_tool.initialize()
    
    try:
        if args.list_tables:
            await query_tool.list_tables()
            return
        
        if not args.table:
            print("❌ Error: --table is required (use --list-tables to see available tables)", file=sys.stderr)
            sys.exit(1)
        
        # Show table statistics if requested
        if args.stats:
            print(f"📊 Statistics for table '{args.table}':", file=sys.stderr)
            stats = await query_tool.get_table_stats(args.table)
            if stats:
                for key, value in stats.items():
                    print(f"   {key}: {value}", file=sys.stderr)
            print(file=sys.stderr)
        
        # Query table data
        print(f"🔍 Querying table '{args.table}'...", file=sys.stderr)
        records = await query_tool.query_table(args.table, args.limit)
        
        print(f"✅ Found {len(records)} records", file=sys.stderr)
        
        # Output data
        if args.format == 'json':
            query_tool.output_json(records, args.output)
        elif args.format == 'csv':
            query_tool.output_csv(records, args.output)
    
    finally:
        await query_tool.close()


if __name__ == "__main__":
    asyncio.run(main())
