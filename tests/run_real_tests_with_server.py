#!/usr/bin/env python3
"""
Real Tests Runner with Server Management

This script:
1. Cleans the database
2. Starts the TAMS API server
3. Waits for server to be healthy
4. Runs all real integration tests
5. Cleans up the server
"""

import os
import sys
import time
import signal
import subprocess
import requests
import logging
import argparse
from pathlib import Path
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServerManager:
    """Manages the TAMS API server lifecycle"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.server_url = f"http://{host}:{port}"
        self.server_process: Optional[subprocess.Popen] = None
        
    def start_server(self) -> bool:
        """Start the TAMS API server"""
        logger.info(f"🚀 Starting TAMS API server on {self.host}:{self.port}")
        
        try:
            # Start the server in the background using the correct Python path
            python_path = "/Users/jesse.thaloor/Developer/python/bbctams/bin/python"
            self.server_process = subprocess.Popen(
                [python_path, "run.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).parent.parent
            )
            
            logger.info(f"✅ Server process started with PID: {self.server_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start server: {e}")
            return False
    
    def wait_for_server(self, max_wait: int = 60) -> bool:
        """Wait for server to become healthy"""
        logger.info(f"🔍 Waiting for server to become healthy at {self.server_url}")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{self.server_url}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "healthy":
                        elapsed = time.time() - start_time
                        logger.info(f"✅ Server is healthy after {elapsed:.1f} seconds")
                        return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
        
        logger.error(f"❌ Server failed to become healthy after {max_wait} seconds")
        return False
    
    def stop_server(self):
        """Stop the TAMS API server"""
        if self.server_process:
            logger.info(f"🛑 Stopping server process (PID: {self.server_process.pid})")
            
            try:
                # Send SIGTERM first
                self.server_process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.server_process.wait(timeout=10)
                    logger.info("✅ Server stopped gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning("⚠️ Server didn't stop gracefully, forcing kill")
                    self.server_process.kill()
                    self.server_process.wait()
                
            except Exception as e:
                logger.error(f"❌ Error stopping server: {e}")
                # Force kill if needed
                try:
                    self.server_process.kill()
                except:
                    pass
            finally:
                self.server_process = None

class DatabaseManager:
    """Manages database cleanup operations"""
    
    @staticmethod
    def cleanup_database() -> bool:
        """Clean the database using the cleanup script"""
        logger.info("🧹 Starting database cleanup...")
        
        try:
            cleanup_script = Path(__file__).parent.parent / "mgmt" / "cleanup_database.py"
            
            if not cleanup_script.exists():
                logger.error(f"❌ Cleanup script not found: {cleanup_script}")
                return False
            
            # Run the cleanup script using the correct Python path
            python_path = "/Users/jesse.thaloor/Developer/python/bbctams/bin/python"
            result = subprocess.run(
                [python_path, str(cleanup_script)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            if result.returncode == 0:
                logger.info("✅ Database cleanup completed successfully")
                return True
            else:
                logger.error(f"❌ Database cleanup failed with return code {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Database cleanup failed: {e}")
            return False

class TestRunner:
    """Manages test execution"""
    
    def __init__(self, test_dir: str = "real_tests"):
        self.test_dir = Path(__file__).parent / test_dir
        
    def run_tests(self, verbose: bool = False, coverage: bool = False) -> int:
        """Run the real tests"""
        logger.info(f"🧪 Running tests from {self.test_dir}")
        
        if not self.test_dir.exists():
            logger.error(f"❌ Test directory not found: {self.test_dir}")
            return 1
        
        # Build pytest command using the correct Python path
        python_path = "/Users/jesse.thaloor/Developer/python/bbctams/bin/python"
        cmd = [python_path, "-m", "pytest", str(self.test_dir)]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
        
        # Add pytest options
        cmd.extend([
            "--tb=short",
            "--strict-markers",
            "--disable-warnings"
        ])
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, cwd=Path(__file__).parent)
            return result.returncode
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
            return 1

def setup_test_environment():
    """Set up environment variables for 172.x.x.x services"""
    import os
    
    # Set VAST Database settings (from docker-compose.yml)
    # Note: Test harness expects TAMS_ prefix
    os.environ["TAMS_VAST_ENDPOINT"] = "http://172.200.204.90"
    os.environ["TAMS_VAST_ACCESS_KEY"] = "SRSPW0DQT9T70Y787U68"
    os.environ["TAMS_VAST_SECRET_KEY"] = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
    os.environ["TAMS_VAST_BUCKET"] = "jthaloor-db"
    os.environ["TAMS_VAST_SCHEMA"] = "tams7"
    
    # Set S3 settings (from docker-compose.yml)
    # Note: Test harness expects TAMS_ prefix
    os.environ["TAMS_S3_ENDPOINT_URL"] = "http://172.200.204.91"
    os.environ["TAMS_S3_ACCESS_KEY_ID"] = "SRSPW0DQT9T70Y787U68"
    os.environ["TAMS_S3_SECRET_ACCESS_KEY"] = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
    os.environ["TAMS_S3_BUCKET_NAME"] = "jthaloor-s3"
    os.environ["TAMS_S3_USE_SSL"] = "false"
    
    # Set server settings
    os.environ["HOST"] = "0.0.0.0"
    os.environ["PORT"] = "8000"
    os.environ["LOG_LEVEL"] = "INFO"
    
    logger.info("🔧 Test environment configured with 172.x.x.x services:")
    logger.info(f"   VAST: {os.environ['TAMS_VAST_ENDPOINT']}")
    logger.info(f"   S3: {os.environ['TAMS_S3_ENDPOINT_URL']}")
    logger.info(f"   Server: {os.environ['HOST']}:{os.environ['PORT']}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run real tests with server management")
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip database cleanup")
    parser.add_argument("--no-server", action="store_true", help="Don't start server (assume it's running)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage reporting")
    parser.add_argument("--wait-time", type=int, default=60, help="Max wait time for server (default: 60s)")
    
    args = parser.parse_args()
    
    logger.info("🚀 TAMS Real Tests Runner with Server Management")
    logger.info("=" * 80)
    
    # Set up test environment first
    setup_test_environment()
    
    # Initialize managers
    server_manager = ServerManager(args.host, args.port)
    db_manager = DatabaseManager()
    test_runner = TestRunner()
    
    server_started = False
    
    try:
        # Step 1: Clean database (unless skipped)
        if not args.no_cleanup:
            if not db_manager.cleanup_database():
                logger.error("❌ Database cleanup failed, aborting")
                return 1
        else:
            logger.info("⏭️ Skipping database cleanup")
        
        # Step 2: Start server (unless skipped)
        if not args.no_server:
            if not server_manager.start_server():
                logger.error("❌ Failed to start server, aborting")
                return 1
            
            server_started = True
            
            # Step 3: Wait for server to be healthy
            if not server_manager.wait_for_server(args.wait_time):
                logger.error("❌ Server failed to become healthy, aborting")
                return 1
        else:
            logger.info("⏭️ Assuming server is already running")
            
            # Still check if server is healthy
            if not server_manager.wait_for_server(args.wait_time):
                logger.error("❌ Server is not healthy, aborting")
                return 1
        
        # Step 4: Run tests
        logger.info("🧪 Starting test execution...")
        test_result = test_runner.run_tests(args.verbose, args.coverage)
        
        if test_result == 0:
            logger.info("✅ All tests completed successfully!")
        else:
            logger.error(f"❌ Tests failed with return code {test_result}")
        
        return test_result
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Process interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        # Cleanup: Stop server if we started it
        if server_started:
            server_manager.stop_server()

if __name__ == "__main__":
    try:
        # Use the correct Python path for this script
        if not sys.executable.endswith("bbctams/bin/python"):
            logger.warning(f"⚠️ Running with Python: {sys.executable}")
            logger.info("ℹ️ Consider using: /Users/jesse.thaloor/Developer/python/bbctams/bin/python")
        
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Process interrupted by user")
        sys.exit(1)
