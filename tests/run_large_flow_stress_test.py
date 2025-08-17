#!/usr/bin/env python3
"""
Runner for TAMS Large Flow Stress Test

This script checks if the TAMS server is running and then executes
the large flow stress test that creates 1000 segments and tests
selective deletion.
"""

import subprocess
import sys
import time
import requests
from pathlib import Path


def check_server_running():
    """Check if TAMS server is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def main():
    """Main function to run the large flow stress test"""
    print("🚀 TAMS Large Flow Stress Test Runner")
    print("=" * 60)
    
    # Check if TAMS server is running
    print("🔍 Checking if TAMS server is running...")
    if not check_server_running():
        print("❌ TAMS server is not running!")
        print("   Please start the server first with: python run.py")
        return False
    
    print("✅ TAMS server is running")
    
    # Run the large flow stress test
    print("🧪 Starting large flow stress test...")
    test_script = Path(__file__).parent / "real_tests" / "test_large_flow_stress.py"
    
    if not test_script.exists():
        print(f"❌ Test script not found: {test_script}")
        return False
    
    print(f"Running: {test_script}")
    print("-" * 80)
    
    try:
        # Run the test
        result = subprocess.run([
            sys.executable, str(test_script)
        ], capture_output=False, text=True)
        
        if result.returncode == 0:
            print("-" * 80)
            print("✅ Large flow stress test completed successfully!")
            return True
        else:
            print("-" * 80)
            print(f"❌ Large flow stress test failed with exit code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to run large flow stress test: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
