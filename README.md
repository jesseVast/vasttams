# TAMS (Time-addressable Media Store) API

A FastAPI implementation of the BBC TAMS API specification with VAST database integration for high-performance time-series analytics.

## Features

- **Full TAMS API Compliance**: Implements the complete BBC TAMS API specification v6.0
- **VAST Database Integration**: High-performance columnar storage using vastdbmanager
- **Time-Series Analytics**: Optimized for media flow segments with time ranges
- **RESTful API**: Complete CRUD operations for sources, flows, segments, and objects
- **Analytics Endpoints**: Built-in analytics for flow usage, storage patterns, and time analysis
- **Docker Support**: Containerized deployment with Docker and docker-compose
- **Comprehensive Testing**: Automated test suite for all endpoints

## Architecture

### VAST Database Store
The application uses the `vastdbmanager.py` module to provide a clean interface to VAST Database:

- **Columnar Storage**: Apache Arrow schemas with optimized table structures
- **Time-Series Optimization**: Automatic time range parsing and indexing
- **Transaction Support**: ACID-like operations with rollback capability
- **Schema Management**: Automatic table creation and schema discovery
- **Analytics Engine**: Built-in statistical analysis and aggregation
- **Connection Management**: Robust connection handling with retry logic

### Database Schema
The VAST store creates the following tables with optimized schemas:

- **sources**: Media sources with metadata and collections
- **flows**: Media flows with format-specific attributes (video, audio, data)
- **segments**: Time-series optimized flow segments with time ranges
- **objects**: Media objects with access tracking
- **webhooks**: Event notification configuration
- **deletion_requests**: Media deletion tracking

### API Endpoints

#### Core TAMS Endpoints
- `GET /` - Service information
- `GET /health` - Health check
- `GET /sources` - List sources with filtering
- `POST /sources` - Create new source
- `GET /sources/{id}` - Get source by ID
- `GET /flows` - List flows with filtering
- `POST /flows` - Create new flow
- `GET /flows/{id}` - Get flow by ID
- `GET /flows/{id}/segments` - Get flow segments
- `POST /flows/{id}/segments` - Create flow segment
- `GET /objects/{id}` - Get media object
- `POST /objects` - Create media object

#### Analytics Endpoints
- `GET /analytics/flow-usage` - Flow usage statistics
- `GET /analytics/storage-usage` - Storage usage analysis
- `GET /analytics/time-range-analysis` - Time range patterns

#### Management Endpoints
- `GET /webhooks` - List webhooks
- `POST /webhooks` - Create webhook
- `POST /flows/{id}/storage` - Allocate storage
- `GET /deletion-requests` - List deletion requests
- `POST /deletion-requests` - Create deletion request

## Quick Start

### Prerequisites
- Python 3.9+
- VAST Database server (optional, can use mock for development)
- Docker (optional)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bbctams
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment**
   ```bash
   cp env.example .env
   # Edit .env with your VAST database configuration
   ```

4. **Run the application**
   ```bash
   python run.py
   ```

5. **Access the API**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker Deployment

1. **Build and run with docker-compose**
   ```bash
   docker-compose up --build
   ```

2. **Or build manually**
   ```bash
   docker build -t tams-api .
   docker run -p 8000:8000 tams-api
   ```

## VAST Database Configuration

The application uses the following VAST database settings:

```env
# VAST Database settings
VAST_ENDPOINT=http://main.vast.acme.com/
VAST_ACCESS_KEY=test-access-key
VAST_SECRET_KEY=test-secret-key
VAST_BUCKET=tams-bucket
VAST_SCHEMA=tams-schema
```

### Testing VAST Store

Run the VAST store test script:
```bash
python test_vast_store.py
```

This will test:
- VAST store initialization
- Table and schema management
- Source creation and retrieval
- Analytics queries
- Table statistics

## API Usage Examples

### Create a Video Source
```bash
curl -X POST "http://localhost:8000/sources" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "urn:x-nmos:format:video",
    "label": "Main Camera Feed",
    "description": "Primary camera source for live broadcast"
  }'
```

### Create a Video Flow
```bash
curl -X POST "http://localhost:8000/flows" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "source_id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "urn:x-nmos:format:video",
    "codec": "video/mp4",
    "frame_width": 1920,
    "frame_height": 1080,
    "frame_rate": "25:1"
  }'
```

### Get Analytics
```bash
# Flow usage analytics
curl "http://localhost:8000/analytics/flow-usage"

# Storage usage analytics
curl "http://localhost:8000/analytics/storage-usage"

# Time range analysis
curl "http://localhost:8000/analytics/time-range-analysis"
```

## Testing

Run the test suite:
```bash
python test_basic.py
```

The tests cover:
- Health check endpoint
- Service information
- Source creation and retrieval
- Flow creation and retrieval
- Analytics endpoints
- List endpoints

## Configuration

Key configuration options in `.env`:

```env
# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=false

# VAST Database settings
VAST_ENDPOINT=http://localhost:8080
VAST_ACCESS_KEY=test-access-key
VAST_SECRET_KEY=test-secret-key
VAST_BUCKET=tams-bucket
VAST_SCHEMA=tams-schema

# Logging
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key-here-change-in-production
```

## VAST Database Features

### Columnar Storage
- Apache Arrow schemas for type safety
- Optimized table structures for TAMS data types
- Vectorized operations for analytics

### Transaction Support
The vastdbmanager provides transaction support:
```python
with vast_store.db_manager.session.transaction() as tx:
    bucket = tx.bucket("tams-bucket")
    schema = bucket.schema("tams-schema")
    table = schema.table("sources")
    # Perform operations within transaction
```

### Analytics Integration
Built-in analytics queries:
```python
# Flow usage analytics
analytics = await store.analytics_query("flow_usage")

# Storage usage analytics  
analytics = await store.analytics_query("storage_usage")

# Time range analysis
analytics = await store.analytics_query("time_range_analysis")

# Catalog summary
analytics = await store.analytics_query("catalog_summary")
```

### Schema Management
Automatic table creation and schema discovery:
```python
# List all tables
tables = store.list_tables()

# List all schemas
schemas = store.list_schemas()

# Get table statistics
stats = store.get_table_stats("sources")
```

## Development

### Project Structure
```
bbctams/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models
│   ├── config.py            # Configuration management
│   ├── vast_store.py        # VAST store implementation
│   └── vastdbmanager.py     # VAST database manager
├── api/
│   └── schemas/             # JSON schemas
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── run.py
└── test_basic.py
```

### Adding New Features

1. **New Data Types**: Add to `models.py` and update VAST store schemas
2. **New Endpoints**: Add to `main.py` with proper error handling
3. **New Analytics**: Extend `analytics_query` method in `vast_store.py`
4. **New Tests**: Add to `test_basic.py` or create new test files

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions:
- Check the documentation at `/docs`
- Review the test examples
- Open an issue on GitHub
