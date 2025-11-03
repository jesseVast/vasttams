#!/usr/bin/env python3
"""
Webhook Test Server

A simple HTTP server for testing TAMS webhook events.
Receives webhook POST requests and logs them for inspection.

Usage:
    python tests/webhook_test_server.py [--port PORT] [--host HOST]
"""

import argparse
import json
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any
from urllib.parse import urlparse, parse_qs
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhook events"""
    
    def log_message(self, format, *args):
        """Override to use our logger instead of stderr"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests (health check, status)"""
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "service": "webhook-test-server",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_POST(self):
        """Handle POST requests (webhook events)"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            # Parse JSON payload
            try:
                payload = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                payload = {"raw_body": body.decode('utf-8', errors='replace')}
            
            # Get headers
            headers = dict(self.headers)
            
            # Log the webhook event
            self._log_webhook_event(payload, headers)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "status": "received",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            self.wfile.write(json.dumps(error_response, indent=2).encode('utf-8'))
    
    def _log_webhook_event(self, payload: Dict[str, Any], headers: Dict[str, str]):
        """Log webhook event in a readable format"""
        print("\n" + "=" * 80)
        print(f"WEBHOOK EVENT RECEIVED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Extract API key if present
        api_key_name = None
        api_key_value = None
        for header_name, header_value in headers.items():
            if header_name.lower().startswith('x-api-key') or header_name.lower() == 'authorization':
                api_key_name = header_name
                api_key_value = header_value[:20] + "..." if len(header_value) > 20 else header_value
                break
        
        print(f"\n📡 Request Info:")
        print(f"  Method: {self.command}")
        print(f"  Path: {self.path}")
        print(f"  Remote Address: {self.client_address[0]}:{self.client_address[1]}")
        if api_key_name:
            print(f"  {api_key_name}: {api_key_value}")
        
        print(f"\n📋 Headers:")
        for name, value in sorted(headers.items()):
            if name.lower().startswith('x-api-key') or name.lower() == 'authorization':
                masked_value = value[:20] + "..." if len(value) > 20 else value
                print(f"  {name}: {masked_value}")
            else:
                print(f"  {name}: {value}")
        
        print(f"\n📦 Payload:")
        print(json.dumps(payload, indent=2))
        
        # Extract event type and details
        event_type = payload.get('event_type') or payload.get('event') or payload.get('type') or "unknown"
        event_timestamp = payload.get('event_timestamp') or payload.get('timestamp') or "unknown"
        event_data = payload.get('event') or payload.get('data') or payload
        
        print(f"\n🎯 Event Info:")
        print(f"   Type: {event_type}")
        print(f"   Timestamp: {event_timestamp}")
        
        # Extract resource info from event_data
        if isinstance(event_data, dict):
            # TAMS webhook format: event_data contains the resource
            resource_id = event_data.get('id') or event_data.get('@id') or "unknown"
            resource_type = "unknown"
            
            # Determine resource type from structure
            if 'source_id' in event_data or 'format' in event_data:
                if 'codec' in event_data or 'essence_parameters' in event_data:
                    resource_type = "Flow"
                else:
                    resource_type = "Source"
            elif 'object_id' in event_data or 'flow_id' in event_data:
                resource_type = "Segment"
            elif 'referenced_by_flows' in event_data:
                resource_type = "Object"
            
            print(f"   Resource Type: {resource_type}")
            print(f"   Resource ID: {resource_id}")
            
            # Show key fields
            if resource_type == "Flow":
                print(f"   Flow Label: {event_data.get('label', 'N/A')}")
                print(f"   Source ID: {event_data.get('source_id', 'N/A')}")
            elif resource_type == "Source":
                print(f"   Source Label: {event_data.get('label', 'N/A')}")
                print(f"   Format: {event_data.get('format', 'N/A')}")
            elif resource_type == "Segment":
                print(f"   Flow ID: {event_data.get('flow_id', 'N/A')}")
                print(f"   Object ID: {event_data.get('object_id', 'N/A')}")
                timerange = event_data.get('timerange')
                if timerange:
                    timerange_str = timerange.get('value') if isinstance(timerange, dict) else str(timerange)
                    print(f"   Timerange: {timerange_str}")
        
        print("=" * 80 + "\n")
        
        # Also log to logger for file logging
        logger.info(f"Webhook event received: {event_type}, payload size: {len(json.dumps(payload))} bytes")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-API-Key')
        self.end_headers()


def run_server(host: str = '0.0.0.0', port: int = 8080):
    """Run the webhook test server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, WebhookHandler)
    
    print(f"\n{'=' * 80}")
    print(f"🚀 Webhook Test Server Starting")
    print(f"{'=' * 80}")
    print(f"Listening on: http://{host}:{port}")
    print(f"Health check: http://{host}:{port}/health")
    print(f"Webhook endpoint: http://{host}:{port}/")
    print(f"\nReady to receive webhook events...")
    print(f"Press Ctrl+C to stop\n")
    print(f"{'=' * 80}\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down webhook test server...")
        httpd.shutdown()
        print("✅ Server stopped\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='TAMS Webhook Test Server - Receives and logs webhook events'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8080,
        help='Port to listen on (default: 8080)'
    )
    parser.add_argument(
        '--host', '-H',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0 for all interfaces)'
    )
    
    args = parser.parse_args()
    
    run_server(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
