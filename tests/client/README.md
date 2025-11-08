# TAMS Client Test Suite

Tests for the `vasttamsclient` Python client library.

## Test Structure

```
tests/client/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── test_exceptions.py       # Exception class tests
├── test_auth.py             # TokenManager authentication tests
├── test_client.py           # TAMSClient core tests
├── test_domain_source.py   # TAMSSource domain object tests
├── test_domain_flow.py     # TAMSFlow domain object tests
└── test_api_sources.py     # Source API method tests
```

## Running Tests

### Run all client tests
```bash
pytest tests/client/ -v
```

### Run specific test file
```bash
pytest tests/client/test_client.py -v
```

### Run with coverage
```bash
pytest tests/client/ --cov=src/client/vasttamsclient --cov-report=html
```

## Test Coverage

### Current Test Files

1. **test_exceptions.py** - Tests for all exception classes
   - TAMSClientError (base exception)
   - TAMSAuthenticationError
   - TAMSAPIError (with status code and response body)
   - TAMSConnectionError

2. **test_auth.py** - TokenManager tests
   - Initialization
   - Successful login
   - Authentication errors (401)
   - Token caching
   - Token refresh
   - Connection errors

3. **test_client.py** - TAMSClient core tests
   - Initialization and configuration
   - Context manager (async with)
   - Session management
   - HTTP request handling
   - Token refresh on 401
   - Factory methods (TAMSSource, TAMSFlow)
   - Query methods (get_source, get_flow, list_sources, list_flows)
   - Synchronous wrappers

4. **test_domain_source.py** - TAMSSource domain object tests
   - Initialization (new vs existing)
   - Properties (format, label, description)
   - Creation (_ensure_created)
   - Flow operations (TAMSFlow factory, add_flow, get_flow, list_flows)
   - CRUD operations (refresh, update, delete)
   - Tag operations (get_tags, get_tag, set_tag, delete_tag)

5. **test_domain_flow.py** - TAMSFlow domain object tests
   - Initialization (with source_id, source object, existing flow)
   - Properties (source_id, format, codec, label, essence_parameters)
   - Creation (_ensure_created)
   - Segment operations (add_segment, get_segment, list_segments, delete_segments)
   - CRUD operations (refresh, update, delete)
   - Tag operations

6. **test_api_sources.py** - Source API method tests
   - create_source
   - get_source
   - update_source
   - delete_source
   - list_sources
   - Error handling

## Fixtures

The `conftest.py` provides the following fixtures:

- `mock_token` - Mock authentication token
- `mock_token_manager` - Mock TokenManager instance
- `mock_session` - Mock aiohttp ClientSession
- `mock_response` - Mock aiohttp ClientResponse
- `client` - TAMSClient instance with mocked dependencies
- `server_url` - Test server URL

## Mocking Strategy

Tests use `unittest.mock` to mock:
- HTTP requests (aiohttp ClientSession)
- Authentication (TokenManager)
- API responses
- File system operations (for segment uploads)

This allows tests to run without requiring:
- A running TAMS server
- Network connectivity
- Actual S3 storage
- FFmpeg/ffprobe

## Future Test Files

Additional test files to be created:

- `test_domain_segment.py` - TAMSSegment domain object tests
- `test_api_flows.py` - Flow API method tests
- `test_api_segments.py` - Segment API method tests
- `test_api_objects.py` - Object API method tests
- `test_api_tags.py` - Tag API method tests
- `test_api_storage_backends.py` - Storage backend API tests
- `test_utils_ffmpeg.py` - FFmpeg probe utility tests
- `test_integration.py` - Integration tests (requires running server)

## Notes

- All tests use `pytest.mark.asyncio` for async test functions
- Tests are isolated and don't depend on external services
- Tests verify both success and error paths
- Mock responses match TAMS API response formats

