# TAMS API 7.0 to 7.0 Migration Plan

## Overview
This document outlines the systematic approach to update the TAMS API from version 7.0 to 7.0, ensuring full compliance with the API specification.

## Current Status
- **Current Version**: 7.0 (hardcoded throughout codebase)
- **Target Version**: 7.0 (as specified in TimeAddressableMediaStore.yaml)
- **Implementation Status**: ~95% complete for core functionality
- **Main Gap**: Version references and some minor specification compliance

## Migration Strategy

### Phase 1: Version Update (HIGH PRIORITY)
**Goal**: Update all hardcoded version references from 7.0 to 7.0

#### Files to Update:
1. **app/main.py**
   - OpenAPI schema version
   - Service version
   - Telemetry version

2. **app/models/models.py**
   - Service model default version

3. **app/core/config.py**
   - API version configuration

4. **app/__init__.py**
   - Module version

5. **helm/tams/Chart.yaml**
   - App version

6. **app/core/telemetry.py**
   - Service version initialization

7. **config/production.json**
   - API version setting

#### Update Pattern:
```python
# Before
version="7.0"
api_version: str = "7.0"
__version__ = "7.0"

# After  
version="7.0"
api_version: str = "7.0"
__version__ = "7.0"
```

### Phase 2: Specification Compliance Verification (HIGH PRIORITY)
**Goal**: Ensure all endpoints exactly match the 7.0 API specification

#### Areas to Verify:
1. **Response Headers**
   - Verify all required headers are present
   - Check header format and values

2. **Query Parameters**
   - Validate parameter validation logic
   - Ensure parameter combinations work correctly

3. **Response Models**
   - Verify JSON schema matches specification
   - Check required vs optional fields

4. **Error Responses**
   - Ensure proper HTTP status codes
   - Validate error message format

### Phase 3: Enhanced Functionality (MEDIUM PRIORITY)
**Goal**: Implement any missing features from 7.0 specification

#### Potential Enhancements:
1. **Webhook Event Processing**
   - Background task processing
   - Event delivery guarantees
   - Retry mechanisms

2. **Advanced Filtering**
   - Complex query combinations
   - Performance optimizations
   - Caching strategies

3. **Security Improvements**
   - Enhanced OAuth2 flows
   - Better JWT validation
   - Rate limiting

### Phase 4: Testing and Validation (HIGH PRIORITY)
**Goal**: Comprehensive testing to ensure 7.0 compliance

#### Test Categories:
1. **Unit Tests**
   - Model validation
   - Business logic
   - Error handling

2. **Integration Tests**
   - End-to-end API calls
   - Database operations
   - Storage operations

3. **Compliance Tests**
   - OpenAPI schema validation
   - Response format verification
   - Header compliance

4. **Performance Tests**
   - Load testing
   - Memory usage
   - Response times

## Implementation Steps

### Step 1: Version Update Script
Create a script to systematically update all version references:

```bash
#!/bin/bash
# update_versions.sh
find . -name "*.py" -exec sed -i '' 's/6\.0/7.0/g' {} \;
find . -name "*.json" -exec sed -i '' 's/6\.0/7.0/g' {} \;
find . -name "*.yaml" -exec sed -i '' 's/6\.0/7.0/g' {} \;
find . -name "*.yml" -exec sed -i '' 's/6\.0/7.0/g' {} \;
```

### Step 2: Update Core Files
Manually update critical files to ensure proper version handling:

1. **app/main.py** - Update OpenAPI generation
2. **app/core/config.py** - Update default configuration
3. **app/models/models.py** - Update model defaults

### Step 3: Update Configuration Files
Update deployment and configuration files:

1. **helm/tams/Chart.yaml**
2. **config/production.json**
3. **docker-compose.yml** (if version specified)

### Step 4: Update Tests
Update test files to expect version 7.0:

1. **tests/test_basic.py** - Update version assertions
2. **tests/test_integration_*.py** - Update version checks
3. **tests/test_*.py** - Update any hardcoded version references

### Step 5: Update Documentation
Update all documentation references:

1. **README.md**
2. **API documentation**
3. **Deployment guides**

## Risk Assessment

### Low Risk
- Version number updates (simple string replacements)
- Configuration file updates
- Documentation updates

### Medium Risk
- OpenAPI schema generation changes
- Model validation updates
- Test suite updates

### High Risk
- Breaking changes in API behavior
- Database schema changes
- Storage format changes

## Rollback Plan

### Immediate Rollback
- Git revert to previous commit
- Restart services with previous version
- Update configuration files

### Data Migration
- No database schema changes expected
- No storage format changes expected
- Simple configuration rollback

## Success Criteria

### Version Update Complete
- [ ] All hardcoded "7.0" references updated to "7.0"
- [ ] OpenAPI schema shows version 7.0
- [ ] Service endpoints return version 7.0
- [ ] Configuration files updated

### Specification Compliance
- [ ] All endpoints match 7.0 specification exactly
- [ ] Response formats comply with schema
- [ ] Error handling follows specification
- [ ] Headers match requirements

### Testing Complete
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Compliance tests pass
- [ ] Performance tests meet requirements

## Timeline Estimate

- **Phase 1 (Version Update)**: 1-2 days
- **Phase 2 (Compliance Verification)**: 2-3 days  
- **Phase 3 (Enhanced Functionality)**: 3-5 days
- **Phase 4 (Testing and Validation)**: 2-3 days

**Total Estimated Time**: 8-13 days

## Next Actions

1. **Immediate**: Create version update script
2. **Day 1**: Execute version updates
3. **Day 2-3**: Verify specification compliance
4. **Day 4-5**: Run comprehensive tests
5. **Day 6**: Deploy and validate
6. **Day 7**: Documentation updates

## Notes

- This migration is primarily a version number update
- Core functionality is already implemented
- Risk of breaking changes is minimal
- Focus should be on testing and validation
- Consider staging environment deployment first
