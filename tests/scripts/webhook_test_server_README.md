# Webhook Test Server

A simple HTTP server for testing TAMS webhook events. Receives webhook POST requests and logs them in a human-readable format for inspection.

## Usage

### Start the Server

```bash
# Default (port 8080, all interfaces)
python3 tests/webhook_test_server.py

# Custom port
python3 tests/webhook_test_server.py --port 9000

# Custom host and port
python3 tests/webhook_test_server.py --host 127.0.0.1 --port 9000
```

### Register a Webhook in TAMS

Once the server is running, register a webhook to point to it:

```bash
curl -X POST http://localhost:8000/service/webhooks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://localhost:8080",
    "api_key_name": "x-api-key",
    "api_key_value": "test-key-123",
    "events": ["sources/created", "flows/created", "flows/segments_added"]
  }'
```

### Test with curl

You can also test the server directly:

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-key-123" \
  -d '{
    "event_type": "sources/created",
    "event_timestamp": "2025-11-03T13:00:00Z",
    "event": {
      "id": "test-source-id",
      "label": "Test Source",
      "format": "urn:x-nmos:format:video"
    }
  }'
```

## Features

- **Event Logging**: Displays webhook events in a readable format with:
  - Request information (method, path, remote address)
  - Headers (with API key masking)
  - Full JSON payload
  - Extracted event type, timestamp, and resource details
  
- **Health Check**: GET `/health` or `/` returns server status

- **CORS Support**: Handles OPTIONS requests for CORS preflight

- **Error Handling**: Gracefully handles malformed requests and logs errors

## Example Output

```
================================================================================
WEBHOOK EVENT RECEIVED - 2025-11-03 13:30:45
================================================================================

📡 Request Info:
  Method: POST
  Path: /
  Remote Address: 127.0.0.1:54321
  x-api-key: test-key-123...

📋 Headers:
  Content-Length: 234
  Content-Type: application/json
  Host: localhost:8080
  x-api-key: test-key-123...

📦 Payload:
{
  "event_type": "sources/created",
  "event_timestamp": "2025-11-03T13:30:45.123456Z",
  "event": {
    "id": "abc123...",
    "label": "Test Source",
    "format": "urn:x-nmos:format:video"
  }
}

🎯 Event Info:
   Type: sources/created
   Timestamp: 2025-11-03T13:30:45.123456Z
   Resource Type: Source
   Resource ID: abc123...
   Source Label: Test Source
   Format: urn:x-nmos:format:video
================================================================================
```
