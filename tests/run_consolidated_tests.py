#!/usr/bin/env python3
"""
Consolidated Test Runner

This script runs all tests organized by module, providing clear output
and summary information. It replaces the previous scattered test runners.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any
import time


class TestRunner:
    """Main test runner class"""
    
    def __init__(self):
        """Initialize test runner"""
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        self.python_path = "/Users/jesse.thaloor/Developer/python/bbctams/bin/python"
        
        # Test module configuration
        self.test_modules = {
            "core": {
                "path": "test_core",
                "description": "Core functionality tests",
                "priority": 1
            },
            "storage": {
                "path": "test_storage", 
                "description": "Storage functionality tests",
                "priority": 2
            },
            "api": {
                "path": "test_api",
                "description": "API functionality tests", 
                "priority": 3
            },
            "integration": {
                "path": "test_integration",
                "description": "Integration and workflow tests",
                "priority": 4
            }
        }
        
        # Test results storage
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
    
    def run_command(self, command: List[str], cwd: Path = None) -> Dict[str, Any]:
        """Run a command and return results"""
        if cwd is None:
            cwd = self.project_root
        
        # Set environment to suppress warnings
        env = os.environ.copy()
        env['PYTHONWARNINGS'] = 'ignore'
        
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                env=env
            )
            
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out after 5 minutes",
                "success": False
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command failed with exception: {str(e)}",
                "success": False
            }
    
    def run_module_tests(self, module_name: str, module_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run tests for a specific module"""
        print(f"\n{'='*60}")
        print(f"Running {module_name.upper()} Tests")
        print(f"{'='*60}")
        print(f"Description: {module_config['description']}")
        print(f"Path: {module_config['path']}")
        print(f"{'='*60}")
        
        module_path = self.tests_dir / module_config["path"]
        
        if not module_path.exists():
            print(f"❌ Module path does not exist: {module_path}")
            return {
                "success": False,
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
                "error": "Module path does not exist"
            }
        
        # Run pytest for the module
        command = [
            self.python_path, "-m", "pytest",
            str(module_path),
            "-v",
            "--tb=short",
            "--strict-markers",
            "--disable-warnings"
        ]
        
        print(f"Running command: {' '.join(command)}")
        start_time = time.time()
        
        result = self.run_command(command)
        
        execution_time = time.time() - start_time
        
        # Parse test results from output
        test_stats = self.parse_test_output(result["stdout"])
        
        print(f"\nExecution time: {execution_time:.2f} seconds")
        
        if result["success"]:
            print(f"✅ {module_name.upper()} tests completed successfully")
        else:
            print(f"❌ {module_name.upper()} tests failed")
            if result["stderr"]:
                print(f"Error output: {result['stderr']}")
        
        return {
            "success": result["success"],
            "execution_time": execution_time,
            "tests_run": test_stats.get("total", 0),
            "tests_passed": test_stats.get("passed", 0),
            "tests_failed": test_stats.get("failed", 0),
            "tests_skipped": test_stats.get("skipped", 0),
            "error": result["stderr"] if not result["success"] else None
        }
    
    def parse_test_output(self, output: str) -> Dict[str, int]:
        """Parse pytest output to extract test statistics"""
        stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0
        }
        
        # Look for pytest summary line
        lines = output.split('\n')
        for line in lines:
            if "passed" in line and ("failed" in line or "error" in line):
                # Parse line like "5 passed, 1 failed, 2 skipped in 2.34s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        if "passed" in parts[i+1]:
                            stats["passed"] = int(part)
                        elif "failed" in parts[i+1]:
                            stats["failed"] = int(part)
                        elif "skipped" in parts[i+1]:
                            stats["skipped"] = int(part)
                
                stats["total"] = stats["passed"] + stats["failed"] + stats["skipped"]
                break
        
        return stats
    
    def run_all_tests(self, modules: List[str] = None) -> bool:
        """Run all tests or specified modules"""
        if modules is None:
            modules = list(self.test_modules.keys())
        
        # Sort modules by priority
        sorted_modules = sorted(
            [(name, config) for name, config in self.test_modules.items() if name in modules],
            key=lambda x: x[1]["priority"]
        )
        
        print(f"🚀 Starting consolidated test run for {len(sorted_modules)} modules")
        print(f"Project root: {self.project_root}")
        print(f"Python path: {self.python_path}")
        
        overall_success = True
        
        for module_name, module_config in sorted_modules:
            try:
                result = self.run_module_tests(module_name, module_config)
                self.test_results[module_name] = result
                
                # Update totals
                self.total_tests += result["tests_run"]
                self.passed_tests += result["tests_passed"]
                self.failed_tests += result["tests_failed"]
                self.skipped_tests += result["tests_skipped"]
                
                if not result["success"]:
                    overall_success = False
                    
            except Exception as e:
                print(f"❌ Error running {module_name} tests: {str(e)}")
                self.test_results[module_name] = {
                    "success": False,
                    "error": str(e)
                }
                overall_success = False
        
        return overall_success
    
    def print_summary(self):
        """Print test run summary"""
        print(f"\n{'='*80}")
        print("TEST RUN SUMMARY")
        print(f"{'='*80}")
        
        # Module results
        for module_name, result in self.test_results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            print(f"{module_name.upper():<15} {status}")
            
            if "tests_run" in result:
                print(f"  Tests: {result['tests_run']} total, "
                      f"{result['tests_passed']} passed, "
                      f"{result['tests_failed']} failed, "
                      f"{result['tests_skipped']} skipped")
            
            if "execution_time" in result:
                print(f"  Time: {result['execution_time']:.2f}s")
            
            if result.get("error"):
                print(f"  Error: {result['error']}")
        
        # Overall summary
        print(f"\n{'='*80}")
        print("OVERALL SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        print(f"Skipped: {self.skipped_tests} ⏭️")
        
        if self.failed_tests == 0:
            print(f"\n🎉 All tests passed! ({self.passed_tests} tests)")
        else:
            print(f"\n⚠️  {self.failed_tests} tests failed")
        
        print(f"{'='*80}")
    
    def cleanup(self):
        """Cleanup after test run"""
        # Remove any test artifacts
        test_artifacts = [
            ".pytest_cache",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            "*.pyd"
        ]
        
        for artifact in test_artifacts:
            if artifact.startswith("."):
                artifact_path = self.tests_dir / artifact
                if artifact_path.exists():
                    import shutil
                    shutil.rmtree(artifact_path)
            else:
                # Handle wildcard patterns
                for file_path in self.tests_dir.rglob(artifact):
                    try:
                        file_path.unlink()
                    except Exception:
                        pass


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run consolidated tests for BBC TAMS")
    parser.add_argument(
        "--modules", "-m",
        nargs="+",
        choices=["core", "storage", "api", "integration"],
        help="Specific modules to test (default: all)"
    )
    parser.add_argument(
        "--python-path", "-p",
        default="/Users/jesse.thaloor/Developer/python/bbctams/bin/python",
        help="Python interpreter path"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip cleanup after test run"
    )
    
    args = parser.parse_args()
    
    # Create test runner
    runner = TestRunner()
    runner.python_path = args.python_path
    
    try:
        # Run tests
        success = runner.run_all_tests(args.modules)
        
        # Print summary
        runner.print_summary()
        
        # Cleanup
        if not args.no_cleanup:
            runner.cleanup()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test run failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
