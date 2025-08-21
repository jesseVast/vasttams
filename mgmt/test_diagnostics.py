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
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.diagnostics import (
    StorageHealthMonitor,
    TAMSModelValidator, 
    ConnectionTester,
    PerformanceAnalyzer,
    StorageTroubleshooter
)


async def test_health_monitor():
    """Test the health monitor component"""
    print("\n🔍 Testing Health Monitor...")
    monitor = StorageHealthMonitor()
    
    try:
        result = await monitor.check_system_health()
        print(f"✅ Health Monitor - Status: {result.overall_status.value}")
        print(f"   Checks performed: {len(result.checks)}")
        print(f"   Summary: {result.summary}")
        
        for check in result.checks[:3]:  # Show first 3 checks
            print(f"   - {check.component}: {check.status.value} ({check.response_time_ms:.2f}ms)")
        
        return True
    except Exception as e:
        print(f"❌ Health Monitor failed: {e}")
        return False


def test_model_validator():
    """Test the model validator component"""
    print("\n🔍 Testing Model Validator...")
    validator = TAMSModelValidator()
    
    try:
        report = validator.generate_compliance_report()
        print(f"✅ Model Validator - Overall Compliance: {report.get('overall_compliance', 0)}%")
        print(f"   Status: {report.get('status', 'unknown')}")
        print(f"   Models tested: {len(report.get('models', {}))}")
        
        summary = report.get('summary', {})
        print(f"   Compliant: {summary.get('compliant', 0)}, Issues: {summary.get('minor_issues', 0) + summary.get('major_issues', 0) + summary.get('non_compliant', 0)}")
        
        # Show critical issues if any
        critical_issues = report.get('critical_issues', [])
        if critical_issues:
            print(f"   ⚠️  Critical issues: {len(critical_issues)}")
            for issue in critical_issues[:2]:  # Show first 2
                print(f"      - {issue['model']}: {issue['issue']}")
        
        return True
    except Exception as e:
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
