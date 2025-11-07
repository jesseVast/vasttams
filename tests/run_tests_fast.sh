#!/bin/bash
# Fast parallel test runner
# Runs all tests in parallel with optimal settings

cd "$(dirname "$0")/.." || exit 1

PYTHON_BIN="/Users/jesse.thaloor/Developer/python/vasttams/bin/python"

echo "Running tests in parallel mode..."
echo "Using pytest-xdist with auto-detected workers"
echo ""

# Run tests with parallel execution
$PYTHON_BIN -m pytest tests/ \
    -n auto \
    --dist=loadscope \
    -v \
    --tb=short \
    --maxfail=10 \
    "$@"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
else
    echo ""
    echo "❌ Some tests failed (exit code: $exit_code)"
fi

exit $exit_code

