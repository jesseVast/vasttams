#!/bin/bash

# TAMS API Full Workflow Test Script
# This script tests the complete TAMS API workflow including sources, flows, segments, and URL access

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE="http://localhost:8000"
TEST_SOURCE_ID="550e8400-e29b-41d4-a716-446655440001"
TEST_FLOW_ID="550e8400-e29b-41d4-a716-446655440002"
TEST_OBJECT_ID="550e8400-e29b-41d4-a716-446655440003"
TEST_FILE="test_media.txt"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_warning "jq is not installed. JSON responses will not be formatted."
        JQ_AVAILABLE=false
    else
        JQ_AVAILABLE=true
    fi
    
    log_success "Dependencies check passed"
}

check_api_health() {
    log_info "Checking API health..."
    
    HEALTH_RESPONSE=$(curl -s -f "$API_BASE/health" || echo "FAILED")
    
    if [[ "$HEALTH_RESPONSE" == "FAILED" ]]; then
        log_error "API is not accessible at $API_BASE"
        log_error "Please ensure the TAMS API is running"
        exit 1
    fi
    
    log_success "API is healthy and accessible"
}

setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Create test media file
    echo "This is test media content for TAMS API testing" > "$TEST_FILE"
    echo "Additional content line" >> "$TEST_FILE"
    echo "Final content line" >> "$TEST_FILE"
    
    log_success "Test media file created: $TEST_FILE"
    log_info "File contents:"
    cat "$TEST_FILE"
    echo
}

cleanup_test_environment() {
    log_info "Cleaning up test environment..."
    
    if [[ -f "$TEST_FILE" ]]; then
        rm "$TEST_FILE"
        log_success "Test media file removed"
    fi
    
    if [[ -f "$TEST_OBJECT_ID" ]]; then
        rm "$TEST_OBJECT_ID"
        log_success "Downloaded object file removed"
    fi
}

create_source() {
    log_info "Step 1: Creating video source..."
    
    SOURCE_RESPONSE=$(curl -s -X POST "$API_BASE/sources" \
        -H "Content-Type: application/json" \
        -d "{
            \"id\": \"$TEST_SOURCE_ID\",
            \"format\": \"urn:x-nmos:format:video\",
            \"label\": \"Test Camera Feed\",
            \"description\": \"Test source for workflow validation\",
            \"tags\": {
                \"location\": \"test-studio\",
                \"quality\": \"test\",
                \"purpose\": \"workflow-testing\"
            },
            \"source_collection\": [],
            \"collected_by\": []
        }")
    
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        echo "$SOURCE_RESPONSE" | jq '.'
    else
        echo "$SOURCE_RESPONSE"
    fi
    
    SOURCE_ID=$(echo "$SOURCE_RESPONSE" | jq -r '.id' 2>/dev/null || echo "unknown")
    log_success "Source created: $SOURCE_ID"
}

create_flow() {
    log_info "Step 2: Creating video flow..."
    
    FLOW_RESPONSE=$(curl -s -X POST "$API_BASE/flows" \
        -H "Content-Type: application/json" \
        -d "{
            \"id\": \"$TEST_FLOW_ID\",
            \"source_id\": \"$TEST_SOURCE_ID\",
            \"format\": \"urn:x-nmos:format:video\",
            \"codec\": \"video/mp4\",
            \"label\": \"Test HD Video Stream\",
            \"description\": \"Test flow for workflow validation\",
            \"essence_parameters\": {
                \"frame_width\": 1920,
                \"frame_height\": 1080,
                \"frame_rate\": {
                    \"numerator\": 25,
                    \"denominator\": 1
                }
            }
        }")
    
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        echo "$FLOW_RESPONSE" | jq '.'
    else
        echo "$FLOW_RESPONSE"
    fi
    
    FLOW_ID=$(echo "$FLOW_RESPONSE" | jq -r '.id' 2>/dev/null || echo "unknown")
    log_success "Flow created: $FLOW_ID"
}

create_segments() {
    log_info "Step 3: Creating flow segments..."
    
    # Create first segment with media file
    log_info "Creating first segment (with media file)..."
    SEGMENT1_RESPONSE=$(curl -s -X POST "$API_BASE/flows/$TEST_FLOW_ID/segments" \
        -F "segment_data={\"object_id\":\"$TEST_OBJECT_ID\",\"timerange\":\"2025-08-27T20:00:00Z/2025-08-27T20:05:00Z\",\"ts_offset\":\"PT0S\",\"last_duration\":\"PT5M\",\"sample_offset\":0,\"sample_count\":7500,\"key_frame_count\":125}" \
        -F "file=@$TEST_FILE")
    
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        echo "$SEGMENT1_RESPONSE" | jq '.'
    else
        echo "$SEGMENT1_RESPONSE"
    fi
    
    OBJECT_ID=$(echo "$SEGMENT1_RESPONSE" | jq -r '.object_id' 2>/dev/null || echo "unknown")
    log_success "Segment 1 created with object: $OBJECT_ID"
    
    # Create second segment (same object, different time)
    log_info "Creating second segment (same object, different time)..."
    SEGMENT2_RESPONSE=$(curl -s -X POST "$API_BASE/flows/$TEST_FLOW_ID/segments" \
        -F "segment_data={\"object_id\":\"$TEST_OBJECT_ID\",\"timerange\":\"2025-08-27T21:00:00Z/2025-08-27T21:05:00Z\",\"ts_offset\":\"PT0S\",\"last_duration\":\"PT5M\",\"sample_offset\":0,\"sample_count\":7500,\"key_frame_count\":125}" \
        -F "file=@$TEST_FILE")
    
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        echo "$SEGMENT2_RESPONSE" | jq '.'
    else
        echo "$SEGMENT2_RESPONSE"
    fi
    
    log_success "Segment 2 created"
    
    # Create third segment (metadata only, same object)
    log_info "Creating third segment (metadata only, same object)..."
    SEGMENT3_RESPONSE=$(curl -s -X POST "$API_BASE/flows/$TEST_FLOW_ID/segments" \
        -F "segment_data={\"object_id\":\"$TEST_OBJECT_ID\",\"timerange\":\"2025-08-27T22:00:00Z/2025-08-27T22:10:00Z\"}")
    
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        echo "$SEGMENT3_RESPONSE" | jq '.'
    else
        echo "$SEGMENT3_RESPONSE"
    fi
    
    log_success "Segment 3 created"
}

fetch_segments() {
    log_info "Step 4: Fetching flow segments..."
    
    SEGMENTS_RESPONSE=$(curl -s "$API_BASE/flows/$TEST_FLOW_ID/segments")
    
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        echo "$SEGMENTS_RESPONSE" | jq '.'
    else
        echo "$SEGMENTS_RESPONSE"
    fi
    
    SEGMENT_COUNT=$(echo "$SEGMENTS_RESPONSE" | jq '. | length' 2>/dev/null || echo "unknown")
    log_success "Found $SEGMENT_COUNT segments"
}

test_url_access() {
    log_info "Step 5: Testing URL access..."
    
    # Get the first segment's URLs
    SEGMENTS_RESPONSE=$(curl -s "$API_BASE/flows/$TEST_FLOW_ID/segments")
    GET_URL=$(echo "$SEGMENTS_RESPONSE" | jq -r '.[0].get_urls[] | select(.label | contains("GET")) | .url' 2>/dev/null || echo "")
    HEAD_URL=$(echo "$SEGMENTS_RESPONSE" | jq -r '.[0].get_urls[] | select(.label | contains("HEAD")) | .url' 2>/dev/null || echo "")
    
    if [[ -z "$GET_URL" || -z "$HEAD_URL" ]]; then
        log_error "Failed to extract URLs from segment response"
        return 1
    fi
    
    log_info "GET URL: ${GET_URL:0:80}..."
    log_info "HEAD URL: ${HEAD_URL:0:80}..."
    
    # Test HEAD request (metadata)
    log_info "Testing HEAD request..."
    HEAD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -I "$HEAD_URL" || echo "FAILED")
    
    if [[ "$HEAD_STATUS" == "200" ]]; then
        log_success "HEAD request successful (status: $HEAD_STATUS)"
    else
        log_warning "HEAD request returned status: $HEAD_STATUS"
    fi
    
    # Test GET request (content)
    log_info "Testing GET request..."
    GET_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$GET_URL" || echo "FAILED")
    
    if [[ "$GET_STATUS" == "200" ]]; then
        log_success "GET request successful (status: $GET_STATUS)"
    else
        log_warning "GET request returned status: $GET_STATUS"
    fi
    
    # Download content
    log_info "Downloading content..."
    curl -s -o "$TEST_OBJECT_ID" "$GET_URL"
    
    if [[ -f "$TEST_OBJECT_ID" ]]; then
        FILE_SIZE=$(wc -c < "$TEST_OBJECT_ID")
        log_success "Content downloaded: $TEST_OBJECT_ID (size: $FILE_SIZE bytes)"
        log_info "Downloaded content:"
        cat "$TEST_OBJECT_ID"
        echo
    else
        log_error "Failed to download content"
    fi
}

check_object_details() {
    log_info "Step 6: Checking object details..."
    
    OBJECT_RESPONSE=$(curl -s "$API_BASE/objects/$TEST_OBJECT_ID")
    
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        echo "$OBJECT_RESPONSE" | jq '.'
    else
        echo "$OBJECT_RESPONSE"
    fi
    
    FLOW_REF_COUNT=$(echo "$OBJECT_RESPONSE" | jq '.flow_references | length' 2>/dev/null || echo "unknown")
    log_success "Object has $FLOW_REF_COUNT flow references"
}

test_analytics() {
    log_info "Step 7: Testing analytics..."
    
    # Flow usage analytics
    log_info "Testing flow usage analytics..."
    ANALYTICS_RESPONSE=$(curl -s "$API_BASE/analytics/flow-usage")
    
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        echo "$ANALYTICS_RESPONSE" | jq '.'
    else
        echo "$ANALYTICS_RESPONSE"
    fi
    
    TOTAL_FLOWS=$(echo "$ANALYTICS_RESPONSE" | jq -r '.total_flows' 2>/dev/null || echo "unknown")
    log_success "Total flows in analytics: $TOTAL_FLOWS"
    
    # Storage usage analytics
    log_info "Testing storage usage analytics..."
    STORAGE_RESPONSE=$(curl -s "$API_BASE/analytics/storage-usage")
    
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        echo "$STORAGE_RESPONSE" | jq '.'
    else
        echo "$STORAGE_RESPONSE"
    fi
    
    TOTAL_OBJECTS=$(echo "$STORAGE_RESPONSE" | jq -r '.total_objects' 2>/dev/null || echo "unknown")
    log_success "Total objects in storage: $TOTAL_OBJECTS"
}

test_object_reuse() {
    log_info "Step 8: Testing object reuse..."
    
    # Create another segment with different object
    log_info "Creating segment with different object..."
    SEGMENT4_RESPONSE=$(curl -s -X POST "$API_BASE/flows/$TEST_FLOW_ID/segments" \
        -F "segment_data={\"object_id\":\"550e8400-e29b-41d4-a716-446655440004\",\"timerange\":\"2025-08-27T23:00:00Z/2025-08-27T23:05:00Z\"}" \
        -F "file=@$TEST_FILE")
    
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        echo "$SEGMENT4_RESPONSE" | jq '.'
    else
        echo "$SEGMENT4_RESPONSE"
    fi
    
    log_success "Segment 4 created with new object"
    
    # Verify object references
    log_info "Verifying object references..."
    OBJECT1_REFS=$(curl -s "$API_BASE/objects/$TEST_OBJECT_ID" | jq '.flow_references | length' 2>/dev/null || echo "unknown")
    OBJECT2_REFS=$(curl -s "$API_BASE/objects/550e8400-e29b-41d4-a716-446655440004" | jq '.flow_references | length' 2>/dev/null || echo "unknown")
    
    log_success "Object $TEST_OBJECT_ID has $OBJECT1_REFS flow references"
    log_success "Object 550e8400-e29b-41d4-a716-446655440004 has $OBJECT2_REFS flow references"
}

cleanup_test_data() {
    log_info "Step 9: Cleaning up test data..."
    
    # Delete segments
    log_info "Deleting segments..."
    SEGMENTS_DELETE_RESPONSE=$(curl -s -X DELETE "$API_BASE/flows/$TEST_FLOW_ID/segments?timerange=2025-08-27T20:00:00Z/2025-08-27T23:59:59Z&deleted_by=test-user")
    log_success "Segments deleted"
    
    # Delete flow
    log_info "Deleting flow..."
    FLOW_DELETE_RESPONSE=$(curl -s -X DELETE "$API_BASE/flows/$TEST_FLOW_ID?deleted_by=test-user")
    log_success "Flow deleted"
    
    # Delete source
    log_info "Deleting source..."
    SOURCE_DELETE_RESPONSE=$(curl -s -X DELETE "$API_BASE/sources/$TEST_SOURCE_ID?deleted_by=test-user")
    log_success "Source deleted"
}

main() {
    echo "🧪 Starting Full TAMS Workflow Test..."
    echo "================================================"
    echo "API Base URL: $API_BASE"
    echo "Test Source ID: $TEST_SOURCE_ID"
    echo "Test Flow ID: $TEST_FLOW_ID"
    echo "Test Object ID: $TEST_OBJECT_ID"
    echo "================================================"
    echo
    
    # Run all test steps
    check_dependencies
    check_api_health
    setup_test_environment
    
    create_source
    create_flow
    create_segments
    fetch_segments
    test_url_access
    check_object_details
    test_analytics
    test_object_reuse
    
    echo
    echo "================================================"
    log_success "Full workflow test completed successfully!"
    echo "================================================"
    echo
    
    # Ask user if they want to cleanup
    read -p "Do you want to cleanup test data? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup_test_data
        log_success "Test data cleaned up"
    else
        log_info "Test data preserved for manual inspection"
    fi
    
    cleanup_test_environment
}

# Handle script interruption
trap 'log_error "Script interrupted. Cleaning up..."; cleanup_test_environment; exit 1' INT TERM

# Run main function
main "$@"
