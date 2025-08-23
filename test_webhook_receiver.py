#!/usr/bin/env python3
"""
Simple webhook receiver for testing TAMS webhooks
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle POST requests (webhook calls)"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            # Parse JSON payload
            payload = json.loads(body.decode('utf-8'))
            
            # Log webhook details
            logger.info("=" * 60)
            logger.info("🔥 WEBHOOK RECEIVED!")
            logger.info("=" * 60)
            logger.info(f"Path: {self.path}")
            logger.info(f"Event Type: {payload.get('event_type')}")
            logger.info(f"Timestamp: {payload.get('timestamp')}")
            logger.info(f"Headers: {dict(self.headers)}")
            
            # Log segment data if present
            if 'segment' in payload:
                segment = payload['segment']
                logger.info("📹 Segment Data:")
                logger.info(f"  Object ID: {segment.get('object_id')}")
                logger.info(f"  Timerange: {segment.get('timerange')}")
                logger.info(f"  Flow ID: {segment.get('flow_id')}")
                logger.info(f"  Sample Count: {segment.get('sample_count')}")
            
            # Log flow data if present
            if 'flow' in payload:
                flow = payload['flow']
                logger.info("🌊 Flow Data:")
                logger.info(f"  ID: {flow.get('id')}")
                logger.info(f"  Source ID: {flow.get('source_id')}")
                logger.info(f"  Format: {flow.get('format')}")
            
            # Log source data if present
            if 'source' in payload:
                source = payload['source']
                logger.info("📡 Source Data:")
                logger.info(f"  ID: {source.get('id')}")
                logger.info(f"  Format: {source.get('format')}")
            
            logger.info("=" * 60)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response = {"status": "received", "message": "Webhook processed successfully"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_GET(self):
        """Handle GET requests for testing"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Webhook receiver is running!\n")
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"HTTP: {format % args}")

def run_server(port=9000):
    """Run the webhook receiver server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, WebhookHandler)
    logger.info(f"🚀 Webhook receiver starting on port {port}")
    logger.info(f"📡 Listening for webhooks at http://localhost:{port}")
    logger.info("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down webhook receiver...")
        httpd.shutdown()

if __name__ == "__main__":
    run_server()
