#!/bin/bash
# Build wheel files for private dependencies (vastdbmanager and vasts3)
# This script builds wheels from local GitLab packages and places them in wheels/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VASTSTORE_DIR="$HOME/Developer/gitlab/vaststore"
WHEELS_DIR="$PROJECT_ROOT/wheels"

echo "🔨 Building wheel files for private dependencies..."
echo "   Source: $VASTSTORE_DIR"
echo "   Output: $WHEELS_DIR"

# Create wheels directory if it doesn't exist
mkdir -p "$WHEELS_DIR"

# Check if vaststore directory exists
if [ ! -d "$VASTSTORE_DIR" ]; then
    echo "❌ Error: VastStore directory not found at $VASTSTORE_DIR"
    echo "   Please ensure the packages are available at that location"
    exit 1
fi

# Build vastdbmanager wheel
if [ -d "$VASTSTORE_DIR/vastdbmanager" ]; then
    echo ""
    echo "📦 Building vastdbmanager wheel..."
    cd "$VASTSTORE_DIR/vastdbmanager"
    python3 -m pip install --upgrade build wheel
    python3 -m build --wheel
    # Remove old vastdbmanager wheels before copying new one
    rm -f "$WHEELS_DIR"/vastdbmanager-*.whl
    # Copy wheel to wheels directory
    cp dist/*.whl "$WHEELS_DIR/"
    echo "✅ vastdbmanager wheel built and copied to $WHEELS_DIR"
else
    echo "❌ Error: vastdbmanager directory not found at $VASTSTORE_DIR/vastdbmanager"
    exit 1
fi

# Build vasts3 wheel
if [ -d "$VASTSTORE_DIR/vasts3" ]; then
    echo ""
    echo "📦 Building vasts3 wheel..."
    cd "$VASTSTORE_DIR/vasts3"
    python3 -m pip install --upgrade build wheel
    python3 -m build --wheel
    # Remove old vasts3 wheels before copying new one
    rm -f "$WHEELS_DIR"/vasts3-*.whl
    # Copy wheel to wheels directory
    cp dist/*.whl "$WHEELS_DIR/"
    echo "✅ vasts3 wheel built and copied to $WHEELS_DIR"
else
    echo "❌ Error: vasts3 directory not found at $VASTSTORE_DIR/vasts3"
    exit 1
fi

echo ""
echo "✅ All wheels built successfully!"
echo "   Location: $WHEELS_DIR"
echo ""
echo "📋 Built wheels:"
ls -lh "$WHEELS_DIR"/*.whl 2>/dev/null || echo "   (no wheels found)"

