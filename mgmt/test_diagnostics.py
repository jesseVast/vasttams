#!/usr/bin/env python3
"""
Test script for Storage Diagnostics System

This script tests all the new diagnostic components to ensure they work correctly
and provides a comprehensive system health check.
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.diagnostics import (
    StorageHealthMonitor,
    TAMSModelValidator, 
    ConnectionTester,
    PerformanceAnalyzer,
    StorageTroubleshooter,
    get_diagnostics_logger
)


async def test_health_monitor():
    """Test the health monitor component"""
    print("\n🔍 Testing Health Monitor...")
    diag_logger = get_diagnostics_logger()
    
    start_time = time.time()
    diag_logger.log_test_start("health_monitor", "System health monitoring test")
    
    monitor = StorageHealthMonitor()
    
    try:
        result = await monitor.check_system_health()
        duration_ms = (time.time() - start_time) * 1000
        
        # Log individual health checks
        for check in result.checks:
            diag_logger.log_health_check(
                component=check.name,
                status=check.status.value,
                response_time_ms=check.response_time_ms,
                message=check.message
            )
        
        # Log overall test result
        success = result.overall_status.value == "healthy"
        diag_logger.log_test_result(
            test_name="health_monitor",
            success=success,
            duration_ms=duration_ms,
            details={
                "overall_status": result.overall_status.value,
                "checks_performed": len(result.checks),
                "healthy_checks": len([c for c in result.checks if c.status.value == "healthy"])
            }
        )
        
        print(f"✅ Health Monitor - Status: {result.overall_status.value}")
        print(f"   Checks performed: {len(result.checks)}")
        print(f"   Summary: {result.summary}")
        
        for check in result.checks[:3]:  # Show first 3 checks
            print(f"   - {check.name}: {check.status.value} ({check.response_time_ms:.2f}ms)")
        
        return True
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        diag_logger.log_test_result("health_monitor", False, duration_ms, {"error": str(e)})
        print(f"❌ Health Monitor failed: {e}")
        return False


def test_model_validator():
    """Test the model validator component"""
    print("\n🔍 Testing Model Validator...")
    diag_logger = get_diagnostics_logger()
    
    start_time = time.time()
    diag_logger.log_test_start("model_validator", "TAMS compliance validation test")
    
    validator = TAMSModelValidator()
    
    try:
        report = validator.generate_compliance_report()
        duration_ms = (time.time() - start_time) * 1000
        
        # Log individual model compliance results
        models = report.get('models', {})
        for model_name, model_data in models.items():
            diag_logger.log_compliance_result(
                model_name=model_name,
                compliance_percentage=model_data.get('compliance_percentage', 0),
                compliance_level=model_data.get('compliance_level', 'unknown'),
                issues_count=model_data.get('issues_count', 0),
                critical_issues=model_data.get('critical_issues', 0)
            )
        
        # Log critical issues
        critical_issues = report.get('critical_issues', [])
        for issue in critical_issues:
            diag_logger.log_issue_detected(
                category="compliance",
                severity="critical",
                title=f"{issue['model']}.{issue['field']}",
                description=issue['issue']
            )
        
        # Log overall test result
        overall_compliance = report.get('overall_compliance', 0)
        success = overall_compliance == 100.0
        diag_logger.log_test_result(
            test_name="model_validator",
            success=success,
            duration_ms=duration_ms,
            details={
                "overall_compliance": overall_compliance,
                "status": report.get('status', 'unknown'),
                "models_tested": len(models),
                "critical_issues": len(critical_issues)
            }
        )
        
        print(f"✅ Model Validator - Overall Compliance: {overall_compliance}%")
        print(f"   Status: {report.get('status', 'unknown')}")
        print(f"   Models tested: {len(models)}")
        
        summary = report.get('summary', {})
        print(f"   Compliant: {summary.get('compliant', 0)}, Issues: {summary.get('minor_issues', 0) + summary.get('major_issues', 0) + summary.get('non_compliant', 0)}")
        
        # Show critical issues if any
        if critical_issues:
            print(f"   ⚠️  Critical issues: {len(critical_issues)}")
            for issue in critical_issues[:2]:  # Show first 2
                print(f"      - {issue['model']}: {issue['issue']}")
        
        return True
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        diag_logger.log_test_result("model_validator", False, duration_ms, {"error": str(e)})
        print(f"❌ Model Validator failed: {e}")
        return False


async def test_connection_tester():
    """Test the connection tester component"""
    print("\n🔍 Testing Connection Tester...")
    tester = ConnectionTester()
    
    try:
        result = await tester.run_connectivity_suite(include_performance=False)
        print(f"✅ Connection Tester - Status: {result.overall_status.value}")
        print(f"   Tests: {result.passed_tests}/{result.total_tests} passed")
        print(f"   Average response time: {result.average_response_time:.2f}ms")
        
        # Show test results
        for test in result.tests[:3]:  # Show first 3 tests
            status_emoji = "✅" if test.status.value == "connected" else "❌"
            print(f"   {status_emoji} {test.test_name}: {test.status.value} ({test.response_time_ms:.2f}ms)")
        
        return True
    except Exception as e:
        print(f"❌ Connection Tester failed: {e}")
        return False


async def test_performance_analyzer():
    """Test the performance analyzer component"""
    print("\n🔍 Testing Performance Analyzer...")
    analyzer = PerformanceAnalyzer()
    
    try:
        result = await analyzer.analyze_performance(include_benchmarks=False)
        print(f"✅ Performance Analyzer - Score: {result.performance_score:.1f}/100")
        print(f"   Status: {result.overall_status.value}")
        print(f"   Benchmarks: {len(result.benchmarks)}")
        print(f"   Query metrics: {len(result.query_metrics)}")
        
        # Show performance issues if any
        if result.bottlenecks:
            print(f"   ⚠️  Bottlenecks detected: {len(result.bottlenecks)}")
            for bottleneck in result.bottlenecks[:2]:  # Show first 2
                print(f"      - {bottleneck}")
        
        return True
    except Exception as e:
        print(f"❌ Performance Analyzer failed: {e}")
        return False


async def test_troubleshooter():
    """Test the troubleshooter component"""
    print("\n🔍 Testing Troubleshooter...")
    troubleshooter = StorageTroubleshooter()
    
    try:
        result = await troubleshooter.run_comprehensive_diagnosis()
        print(f"✅ Troubleshooter - Health: {result.overall_health}")
        print(f"   Issues detected: {len(result.issues_detected)}")
        print(f"   Session duration: {result.duration_ms:.2f}ms")
        print(f"   Summary: {result.summary}")
        
        # Count issues by severity
        if result.issues_detected:
            severities = {}
            for issue in result.issues_detected:
                sev = issue.severity.value
                severities[sev] = severities.get(sev, 0) + 1
            
            severity_str = ", ".join([f"{count} {sev}" for sev, count in severities.items()])
            print(f"   Issue breakdown: {severity_str}")
        
        # Show immediate actions if any
        if result.immediate_actions:
            print(f"   Immediate actions: {len(result.immediate_actions)}")
            for action in result.immediate_actions[:2]:
                print(f"      - {action}")
        
        return True
    except Exception as e:
        print(f"❌ Troubleshooter failed: {e}")
        return False


async def test_quick_health_check():
    """Test quick health check functionality"""
    print("\n🔍 Testing Quick Health Check...")
    troubleshooter = StorageTroubleshooter()
    
    try:
        result = await troubleshooter.get_quick_health_check()
        print(f"✅ Quick Health Check - Status: {result.get('status', 'unknown')}")
        print(f"   Connectivity: {result.get('connectivity_status', 'unknown')}")
        print(f"   Health: {result.get('health_status', 'unknown')}")
        
        issues = result.get('issues', [])
        if issues:
            print(f"   Issues: {len(issues)}")
            for issue in issues:
                print(f"      - {issue}")
        
        return True
    except Exception as e:
        print(f"❌ Quick Health Check failed: {e}")
        return False


def save_test_results(results):
    """Save test results to a file"""
    output_file = Path("logs") / f"diagnostics_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Test results saved to: {output_file}")


async def main():
    """Run all diagnostic tests"""
    print("🧪 TAMS Storage Diagnostics System Test")
    print("=" * 50)
    
    # Initialize diagnostics logger
    diag_logger = get_diagnostics_logger()
    diag_logger.log_separator("TAMS Storage Diagnostics Test Session")
    diag_logger.log_session_start("comprehensive_diagnostics")
    
    start_time = datetime.utcnow()
    
    # Run all tests
    test_results = {
        "timestamp": start_time.isoformat(),
        "tests": {}
    }
    
    tests = [
        ("health_monitor", test_health_monitor),
        ("model_validator", test_model_validator),
        ("connection_tester", test_connection_tester),
        ("performance_analyzer", test_performance_analyzer),
        ("troubleshooter", test_troubleshooter),
        ("quick_health_check", test_quick_health_check),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name.upper()} {'='*20}")
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            
            test_results["tests"][test_name] = {
                "status": "passed" if success else "failed",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if success:
                passed_tests += 1
                
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            test_results["tests"][test_name] = {
                "status": "crashed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Final results
    duration = (datetime.utcnow() - start_time).total_seconds()
    test_results["summary"] = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": total_tests - passed_tests,
        "success_rate": (passed_tests / total_tests) * 100,
        "duration_seconds": duration
    }
    
    print(f"\n{'='*50}")
    print(f"🎯 TEST SUMMARY")
    print(f"   Tests passed: {passed_tests}/{total_tests} ({(passed_tests/total_tests)*100:.1f}%)")
    print(f"   Duration: {duration:.2f} seconds")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Diagnostics system is working correctly.")
        status = "success"
    elif passed_tests > total_tests / 2:
        print("⚠️  MOST TESTS PASSED. Some components may need attention.")
        status = "partial_success"
    else:
        print("❌ MULTIPLE FAILURES. Diagnostics system needs debugging.")
        status = "failure"
    
    test_results["overall_status"] = status
    
    # Log session end
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    diag_logger.log_session_end("comprehensive_diagnostics", success_rate, duration)
    diag_logger.log_separator("Test Session Complete")
    
    # Save results
    save_test_results(test_results)
    
    print(f"\n✅ Diagnostics system test completed with status: {status}")
    
    return status == "success"


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
