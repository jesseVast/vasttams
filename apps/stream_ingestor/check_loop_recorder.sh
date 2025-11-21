#!/bin/bash
#
# Quick diagnostic script to check loop recorder for a specific flow
# Uses curl to check flow tags and segments
#
# Usage:
#   ./check_loop_recorder.sh <flow_id> [server_url] [username] [password]
#

set -e

FLOW_ID="${1:-}"
SERVER_URL="${2:-http://localhost:8000}"
USERNAME="${3:-admin}"
PASSWORD="${4:-admin}"

if [ -z "$FLOW_ID" ]; then
    echo "Usage: $0 <flow_id> [server_url] [username] [password]"
    echo ""
    echo "Example:"
    echo "  $0 d889c741-a895-42e1-8356-4ccc719b3ba2"
    exit 1
fi

API_URL="${SERVER_URL}/api/tams/latest"

echo "=" | tr -d '\n' | head -c 70 && echo ""
echo "LOOP RECORDER DIAGNOSTIC"
echo "=" | tr -d '\n' | head -c 70 && echo ""
echo ""
echo "Flow ID: $FLOW_ID"
echo "Server: $SERVER_URL"
echo ""

# Get auth token
echo "1️⃣  Authenticating..."
TOKEN_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"${USERNAME}\", \"password\": \"${PASSWORD}\"}" || echo "")

if [ -z "$TOKEN_RESPONSE" ] || echo "$TOKEN_RESPONSE" | grep -q "error\|Error\|401\|403"; then
    echo "   ❌ Authentication failed"
    echo "   Response: $TOKEN_RESPONSE"
    exit 1
fi

TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4 || echo "")
if [ -z "$TOKEN" ]; then
    echo "   ❌ Could not extract token from response"
    echo "   Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "   ✅ Authenticated"
echo ""

# Get flow
echo "2️⃣  Fetching flow..."
FLOW_RESPONSE=$(curl -s -X GET "${API_URL}/flows/${FLOW_ID}" \
    -H "Authorization: Bearer ${TOKEN}" || echo "")

if echo "$FLOW_RESPONSE" | grep -q "404\|not found"; then
    echo "   ❌ Flow not found"
    exit 1
fi

FLOW_LABEL=$(echo "$FLOW_RESPONSE" | grep -o '"label":"[^"]*' | cut -d'"' -f4 || echo "N/A")
echo "   ✅ Flow found: $FLOW_LABEL"
echo ""

# Get flow tags
echo "3️⃣  Checking flow tags..."
TAGS_RESPONSE=$(curl -s -X GET "${API_URL}/flows/${FLOW_ID}/tags" \
    -H "Authorization: Bearer ${TOKEN}" || echo "{}")

LOOP_DURATION=$(echo "$TAGS_RESPONSE" | grep -o '"loop_recorder_duration":"[^"]*' | cut -d'"' -f4 || echo "")

if [ -z "$LOOP_DURATION" ]; then
    echo "   ❌ No 'loop_recorder_duration' tag found!"
    echo "   Tags: $TAGS_RESPONSE"
    echo ""
    echo "   💡 Set it with:"
    echo "      curl -X PUT \"${API_URL}/flows/${FLOW_ID}/tags/loop_recorder_duration\" \\"
    echo "        -H \"Authorization: Bearer \${TOKEN}\" \\"
    echo "        -H \"Content-Type: text/plain\" \\"
    echo "        -d \"900\""
    exit 1
fi

echo "   ✅ loop_recorder_duration: ${LOOP_DURATION} seconds ($(echo "scale=1; ${LOOP_DURATION}/60" | bc) minutes)"
echo ""

# Get segments
echo "4️⃣  Checking segments..."
SEGMENTS_RESPONSE=$(curl -s -X GET "${API_URL}/flows/${FLOW_ID}/segments?limit=1000" \
    -H "Authorization: Bearer ${TOKEN}" || echo "[]")

SEGMENT_COUNT=$(echo "$SEGMENTS_RESPONSE" | grep -o '"object_id"' | wc -l | tr -d ' ' || echo "0")

if [ "$SEGMENT_COUNT" -eq "0" ]; then
    echo "   ⚠️  No segments found"
    echo "   💡 Loop recorder only runs when segments exist"
    exit 0
fi

echo "   ✅ Found $SEGMENT_COUNT segments"
echo ""

# Check for timeranges
TIMERANGE_COUNT=$(echo "$SEGMENTS_RESPONSE" | grep -o '"timerange"' | wc -l | tr -d ' ' || echo "0")
echo "   Segments with timerange: $TIMERANGE_COUNT/$SEGMENT_COUNT"

if [ "$TIMERANGE_COUNT" -eq "0" ]; then
    echo "   ❌ No segments have timeranges!"
    echo "   💡 Segments need timeranges for loop recorder to calculate duration"
    exit 1
fi

echo ""
echo "5️⃣  Summary:"
echo "   Flow ID: $FLOW_ID"
echo "   Loop recorder duration: ${LOOP_DURATION}s"
echo "   Segments: $SEGMENT_COUNT"
echo "   Segments with timerange: $TIMERANGE_COUNT"
echo ""
echo "✅ Flow appears to be configured correctly for loop recorder"
echo ""
echo "💡 If loop recorder still isn't working, check:"
echo "   1. Server logs for loop recorder messages:"
echo "      grep 'Loop recorder' server.log"
echo "   2. Verify events are being emitted:"
echo "      grep 'flow-segments/created' server.log"
echo "   3. Check if loop recorder module is enabled"
echo "   4. Verify segment creation triggers events"


