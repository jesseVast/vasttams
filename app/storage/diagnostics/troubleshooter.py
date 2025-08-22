"""
Storage Troubleshooter for TAMS

Provides automated issue detection, diagnosis, and resolution suggestions
for storage-related problems with detailed troubleshooting workflows.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .health_monitor import StorageHealthMonitor, HealthStatus
from .model_validator import TAMSModelValidator, ComplianceLevel
from .connection_tester import ConnectionTester, ConnectionStatus
from .performance_analyzer import PerformanceAnalyzer, PerformanceStatus

logger = logging.getLogger(__name__)


class IssueSeverity(Enum):
    """Issue severity levels"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """Issue categories"""
    CONNECTIVITY = "connectivity"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"
    DATA_INTEGRITY = "data_integrity"
    COMPLIANCE = "compliance"
    SYSTEM_HEALTH = "system_health"


@dataclass
class Issue:
    """Detected issue"""
    issue_id: str
    title: str
    category: IssueCategory
    severity: IssueSeverity
    description: str
    symptoms: List[str]
    root_cause: Optional[str] = None
    impact: Optional[str] = None
    resolution_steps: List[str] = None
    estimated_fix_time: Optional[str] = None
    requires_restart: bool = False
    detected_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()
        if self.resolution_steps is None:
            self.resolution_steps = []


@dataclass
class TroubleshootingSession:
    """Complete troubleshooting session result"""
    session_id: str
    issues_detected: List[Issue]
    overall_health: str
    recommendations: List[str]
    quick_fixes: List[str]
    immediate_actions: List[str]
    follow_up_actions: List[str]
    timestamp: datetime
    duration_ms: float
    summary: str


class StorageTroubleshooter:
    """Automated troubleshooting for storage systems"""
    
    def __init__(self):
        """Initialize troubleshooter"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize diagnostic components
        self.health_monitor = StorageHealthMonitor()
        self.model_validator = TAMSModelValidator()
        self.connection_tester = ConnectionTester()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Issue tracking
        self.known_issues: List[Issue] = []
        self.resolution_history: List[Dict[str, Any]] = []
    
    async def run_comprehensive_diagnosis(self) -> TroubleshootingSession:
        """
        Run comprehensive diagnosis of storage systems
        
        Returns:
            TroubleshootingSession with detected issues and recommendations
        """
        start_time = datetime.utcnow()
        session_id = f"troubleshoot_{int(start_time.timestamp())}"
        
        try:
            self.logger.info(f"Starting comprehensive diagnosis session: {session_id}")
            
            # Run all diagnostic components in parallel
            diagnostic_tasks = [
                self._diagnose_health_issues(),
                self._diagnose_connectivity_issues(),
                self._diagnose_performance_issues(),
                self._diagnose_compliance_issues(),
            ]
            
            results = await asyncio.gather(*diagnostic_tasks, return_exceptions=True)
            
            # Collect all issues
            all_issues = []
            for result in results:
                if isinstance(result, Exception):
                    # Create issue for diagnostic failure
                    all_issues.append(Issue(
                        issue_id=f"diagnostic_failure_{len(all_issues)}",
                        title="Diagnostic Component Failure",
                        category=IssueCategory.SYSTEM_HEALTH,
                        severity=IssueSeverity.HIGH,
                        description=f"Diagnostic component failed: {str(result)}",
                        symptoms=["Diagnostic analysis incomplete"],
                        resolution_steps=["Check system logs", "Restart diagnostic services"]
                    ))
                elif isinstance(result, list):
                    all_issues.extend(result)
            
            # Analyze issues and generate session
            session = self._generate_troubleshooting_session(
                session_id, all_issues, start_time
            )
            
            # Store results
            self.known_issues.extend(all_issues)
            
            self.logger.info(f"Diagnosis completed: {len(all_issues)} issues detected")
            return session
            
        except Exception as e:
            self.logger.error(f"Comprehensive diagnosis failed: {e}")
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return TroubleshootingSession(
                session_id=session_id,
                issues_detected=[Issue(
                    issue_id="diagnosis_error",
                    title="Troubleshooting System Error",
                    category=IssueCategory.SYSTEM_HEALTH,
                    severity=IssueSeverity.CRITICAL,
                    description=f"Troubleshooting system encountered an error: {str(e)}",
                    symptoms=["Diagnostic analysis failed"],
                    resolution_steps=["Check troubleshooter logs", "Restart troubleshooting system"]
                )],
                overall_health="critical",
                recommendations=["System diagnosis failed - manual intervention required"],
                quick_fixes=[],
                immediate_actions=["Check system logs", "Verify system health"],
                follow_up_actions=["Contact system administrator"],
                timestamp=start_time,
                duration_ms=duration,
                summary="Troubleshooting system failed - manual diagnosis required"
            )
    
    async def _diagnose_health_issues(self) -> List[Issue]:
        """Diagnose system health issues"""
        issues = []
        
        try:
            health_result = await self.health_monitor.check_system_health()
            
            # Check for unhealthy components
            for check in health_result.checks:
                if check.status != HealthStatus.HEALTHY:
                    severity = self._map_health_to_severity(check.status)
                    
                    issues.append(Issue(
                        issue_id=f"health_{check.name}",
                        title=f"Health Issue: {check.name}",
                        category=IssueCategory.SYSTEM_HEALTH,
                        severity=severity,
                        description=check.message,
                        symptoms=[f"{check.name} status: {check.status.value}"],
                        root_cause=check.details.get("error") if check.details else None,
                        impact=f"{check.name} not functioning properly",
                        resolution_steps=self._get_health_resolution_steps(check.name, check.status),
                        estimated_fix_time="5-15 minutes"
                    ))
            
            # Check overall system health
            if health_result.overall_status != HealthStatus.HEALTHY:
                issues.append(Issue(
                    issue_id="overall_health",
                    title="Overall System Health Issue",
                    category=IssueCategory.SYSTEM_HEALTH,
                    severity=self._map_health_to_severity(health_result.overall_status),
                    description=health_result.summary,
                    symptoms=[f"Overall status: {health_result.overall_status.value}"],
                    impact="System may not function properly",
                    resolution_steps=["Address individual component issues", "Restart services if necessary"],
                    estimated_fix_time="15-30 minutes"
                ))
            
        except Exception as e:
            issues.append(Issue(
                issue_id="health_diagnosis_error",
                title="Health Diagnosis Failed",
                category=IssueCategory.SYSTEM_HEALTH,
                severity=IssueSeverity.HIGH,
                description=f"Health monitoring failed: {str(e)}",
                symptoms=["Health checks unavailable"],
                resolution_steps=["Check health monitor configuration", "Restart health monitoring"],
                estimated_fix_time="10-20 minutes"
            ))
        
        return issues
    
    async def _diagnose_connectivity_issues(self) -> List[Issue]:
        """Diagnose connectivity issues"""
        issues = []
        
        try:
            connectivity_result = await self.connection_tester.run_connectivity_suite(include_performance=False)
            
            # Check failed connection tests
            for test in connectivity_result.tests:
                if test.status != ConnectionStatus.CONNECTED:
                    severity = self._map_connection_to_severity(test.status)
                    
                    issues.append(Issue(
                        issue_id=f"connectivity_{test.test_name}",
                        title=f"Connectivity Issue: {test.test_name}",
                        category=IssueCategory.CONNECTIVITY,
                        severity=severity,
                        description=test.message,
                        symptoms=[f"{test.test_name} status: {test.status.value}"],
                        root_cause=test.error,
                        impact=f"Service {test.test_name} unavailable",
                        resolution_steps=self._get_connectivity_resolution_steps(test.test_name, test.status),
                        estimated_fix_time="10-30 minutes"
                    ))
            
            # Check overall connectivity
            if connectivity_result.overall_status != ConnectionStatus.CONNECTED:
                issues.append(Issue(
                    issue_id="overall_connectivity",
                    title="Overall Connectivity Issue",
                    category=IssueCategory.CONNECTIVITY,
                    severity=self._map_connection_to_severity(connectivity_result.overall_status),
                    description=connectivity_result.summary,
                    symptoms=[f"Overall connectivity: {connectivity_result.overall_status.value}"],
                    impact="Multiple services unavailable",
                    resolution_steps=["Check network connectivity", "Verify service configurations", "Restart services"],
                    estimated_fix_time="20-45 minutes"
                ))
        
        except Exception as e:
            issues.append(Issue(
                issue_id="connectivity_diagnosis_error",
                title="Connectivity Diagnosis Failed",
                category=IssueCategory.CONNECTIVITY,
                severity=IssueSeverity.HIGH,
                description=f"Connectivity testing failed: {str(e)}",
                symptoms=["Connectivity tests unavailable"],
                resolution_steps=["Check connection tester configuration", "Verify network access"],
                estimated_fix_time="15-25 minutes"
            ))
        
        return issues
    
    async def _diagnose_performance_issues(self) -> List[Issue]:
        """Diagnose performance issues"""
        issues = []
        
        try:
            performance_result = await self.performance_analyzer.analyze_performance(include_benchmarks=False)
            
            # Check poor performance benchmarks
            for benchmark in performance_result.benchmarks:
                if benchmark.status in [PerformanceStatus.POOR, PerformanceStatus.CRITICAL]:
                    severity = self._map_performance_to_severity(benchmark.status)
                    
                    issues.append(Issue(
                        issue_id=f"performance_{benchmark.benchmark_name}",
                        title=f"Performance Issue: {benchmark.benchmark_name}",
                        category=IssueCategory.PERFORMANCE,
                        severity=severity,
                        description=benchmark.message,
                        symptoms=[f"{benchmark.benchmark_name}: {benchmark.execution_time_ms:.2f}ms"],
                        impact="Slow system response times",
                        resolution_steps=self._get_performance_resolution_steps(benchmark.benchmark_name, benchmark.status),
                        estimated_fix_time="30-60 minutes"
                    ))
            
            # Check overall performance
            if performance_result.overall_status in [PerformanceStatus.POOR, PerformanceStatus.CRITICAL]:
                issues.append(Issue(
                    issue_id="overall_performance",
                    title="Overall Performance Issue",
                    category=IssueCategory.PERFORMANCE,
                    severity=self._map_performance_to_severity(performance_result.overall_status),
                    description=performance_result.summary,
                    symptoms=[f"Performance score: {performance_result.performance_score:.1f}/100"],
                    impact="System performance degraded",
                    resolution_steps=performance_result.recommendations[:3],  # Top 3 recommendations
                    estimated_fix_time="45-90 minutes"
                ))
        
        except Exception as e:
            issues.append(Issue(
                issue_id="performance_diagnosis_error",
                title="Performance Diagnosis Failed",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.MEDIUM,
                description=f"Performance analysis failed: {str(e)}",
                symptoms=["Performance tests unavailable"],
                resolution_steps=["Check performance analyzer configuration", "Verify system resources"],
                estimated_fix_time="20-30 minutes"
            ))
        
        return issues
    
    async def _diagnose_compliance_issues(self) -> List[Issue]:
        """Diagnose TAMS compliance issues"""
        issues = []
        
        try:
            compliance_report = self.model_validator.generate_compliance_report()
            
            # Check for compliance failures
            for model_name, model_result in compliance_report.get("models", {}).items():
                compliance_level = model_result.get("compliance_level")
                
                if compliance_level in ["major_issues", "non_compliant"]:
                    severity = IssueSeverity.HIGH if compliance_level == "non_compliant" else IssueSeverity.MEDIUM
                    
                    issues.append(Issue(
                        issue_id=f"compliance_{model_name}",
                        title=f"TAMS Compliance Issue: {model_name}",
                        category=IssueCategory.COMPLIANCE,
                        severity=severity,
                        description=model_result.get("summary", "Model not TAMS compliant"),
                        symptoms=[f"{model_name} compliance: {compliance_level}"],
                        impact="API may not meet TAMS specification",
                        resolution_steps=self._get_compliance_resolution_steps(model_name, compliance_level),
                        estimated_fix_time="60-120 minutes"
                    ))
            
            # Check critical compliance issues
            critical_issues = compliance_report.get("critical_issues", [])
            if critical_issues:
                issues.append(Issue(
                    issue_id="critical_compliance",
                    title="Critical TAMS Compliance Issues",
                    category=IssueCategory.COMPLIANCE,
                    severity=IssueSeverity.CRITICAL,
                    description=f"{len(critical_issues)} critical compliance violations detected",
                    symptoms=[issue["issue"] for issue in critical_issues[:3]],  # First 3 issues
                    impact="API does not meet TAMS specification",
                    resolution_steps=[issue["suggestion"] for issue in critical_issues[:3]],
                    estimated_fix_time="120-240 minutes"
                ))
        
        except Exception as e:
            issues.append(Issue(
                issue_id="compliance_diagnosis_error",
                title="Compliance Diagnosis Failed",
                category=IssueCategory.COMPLIANCE,
                severity=IssueSeverity.MEDIUM,
                description=f"TAMS compliance check failed: {str(e)}",
                symptoms=["Compliance validation unavailable"],
                resolution_steps=["Check model validator configuration", "Verify model definitions"],
                estimated_fix_time="30-45 minutes"
            ))
        
        return issues
    
    def _generate_troubleshooting_session(self, session_id: str, issues: List[Issue], 
                                        start_time: datetime) -> TroubleshootingSession:
        """Generate comprehensive troubleshooting session"""
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Categorize issues by severity
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        high_issues = [i for i in issues if i.severity == IssueSeverity.HIGH]
        medium_issues = [i for i in issues if i.severity == IssueSeverity.MEDIUM]
        low_issues = [i for i in issues if i.severity == IssueSeverity.LOW]
        
        # Determine overall health
        if critical_issues:
            overall_health = "critical"
        elif high_issues:
            overall_health = "degraded"
        elif medium_issues:
            overall_health = "warning"
        elif low_issues:
            overall_health = "minor_issues"
        else:
            overall_health = "healthy"
        
        # Generate recommendations
        recommendations = self._generate_comprehensive_recommendations(issues)
        
        # Generate action items
        immediate_actions = []
        quick_fixes = []
        follow_up_actions = []
        
        # Immediate actions for critical issues
        for issue in critical_issues:
            immediate_actions.extend(issue.resolution_steps[:2])  # First 2 steps
        
        # Quick fixes for high priority issues
        for issue in high_issues:
            if issue.estimated_fix_time and "5" in issue.estimated_fix_time or "10" in issue.estimated_fix_time:
                quick_fixes.extend(issue.resolution_steps[:1])  # First step only
        
        # Follow-up actions for medium/low issues
        for issue in medium_issues + low_issues:
            follow_up_actions.extend(issue.resolution_steps[:1])
        
        # Remove duplicates and limit counts
        immediate_actions = list(dict.fromkeys(immediate_actions))[:5]
        quick_fixes = list(dict.fromkeys(quick_fixes))[:5]
        follow_up_actions = list(dict.fromkeys(follow_up_actions))[:10]
        
        # Generate summary
        issue_count = len(issues)
        if issue_count == 0:
            summary = "No issues detected - system is healthy"
        else:
            summary = f"{issue_count} issues detected: {len(critical_issues)} critical, {len(high_issues)} high, {len(medium_issues)} medium, {len(low_issues)} low priority"
        
        return TroubleshootingSession(
            session_id=session_id,
            issues_detected=issues,
            overall_health=overall_health,
            recommendations=recommendations,
            quick_fixes=quick_fixes,
            immediate_actions=immediate_actions,
            follow_up_actions=follow_up_actions,
            timestamp=start_time,
            duration_ms=duration,
            summary=summary
        )
    
    def _generate_comprehensive_recommendations(self, issues: List[Issue]) -> List[str]:
        """Generate comprehensive recommendations based on issues"""
        recommendations = []
        
        # Category-based recommendations
        categories = {}
        for issue in issues:
            if issue.category not in categories:
                categories[issue.category] = []
            categories[issue.category].append(issue)
        
        # Connectivity recommendations
        if IssueCategory.CONNECTIVITY in categories:
            recommendations.append("Address connectivity issues first - they may be causing other problems")
            recommendations.append("Check network connectivity and service configurations")
        
        # Performance recommendations
        if IssueCategory.PERFORMANCE in categories:
            recommendations.append("Investigate performance bottlenecks affecting system responsiveness")
            recommendations.append("Monitor system resources and optimize slow operations")
        
        # Compliance recommendations
        if IssueCategory.COMPLIANCE in categories:
            recommendations.append("Review TAMS compliance issues to ensure API specification adherence")
            recommendations.append("Update model definitions to match TAMS requirements")
        
        # Health recommendations
        if IssueCategory.SYSTEM_HEALTH in categories:
            recommendations.append("Address system health issues to prevent service disruptions")
            recommendations.append("Verify all system components are functioning properly")
        
        # Priority-based recommendations
        critical_count = len([i for i in issues if i.severity == IssueSeverity.CRITICAL])
        high_count = len([i for i in issues if i.severity == IssueSeverity.HIGH])
        
        if critical_count > 0:
            recommendations.insert(0, f"URGENT: Address {critical_count} critical issues immediately")
        
        if high_count > 0:
            recommendations.append(f"Prioritize {high_count} high-priority issues")
        
        # General recommendations
        if len(issues) > 5:
            recommendations.append("Consider systematic approach to issue resolution")
            recommendations.append("Document resolution steps for future reference")
        
        return recommendations[:10]  # Limit to top 10
    
    # Helper methods for severity mapping
    def _map_health_to_severity(self, health_status: HealthStatus) -> IssueSeverity:
        """Map health status to issue severity"""
        mapping = {
            HealthStatus.HEALTHY: IssueSeverity.LOW,
            HealthStatus.WARNING: IssueSeverity.MEDIUM,
            HealthStatus.CRITICAL: IssueSeverity.HIGH,
            HealthStatus.UNKNOWN: IssueSeverity.MEDIUM
        }
        return mapping.get(health_status, IssueSeverity.MEDIUM)
    
    def _map_connection_to_severity(self, connection_status: ConnectionStatus) -> IssueSeverity:
        """Map connection status to issue severity"""
        mapping = {
            ConnectionStatus.CONNECTED: IssueSeverity.LOW,
            ConnectionStatus.DISCONNECTED: IssueSeverity.HIGH,
            ConnectionStatus.TIMEOUT: IssueSeverity.MEDIUM,
            ConnectionStatus.ERROR: IssueSeverity.HIGH,
            ConnectionStatus.UNKNOWN: IssueSeverity.MEDIUM
        }
        return mapping.get(connection_status, IssueSeverity.MEDIUM)
    
    def _map_performance_to_severity(self, performance_status: PerformanceStatus) -> IssueSeverity:
        """Map performance status to issue severity"""
        mapping = {
            PerformanceStatus.EXCELLENT: IssueSeverity.LOW,
            PerformanceStatus.GOOD: IssueSeverity.LOW,
            PerformanceStatus.ACCEPTABLE: IssueSeverity.MEDIUM,
            PerformanceStatus.POOR: IssueSeverity.HIGH,
            PerformanceStatus.CRITICAL: IssueSeverity.CRITICAL
        }
        return mapping.get(performance_status, IssueSeverity.MEDIUM)
    
    # Helper methods for resolution steps
    def _get_health_resolution_steps(self, component: str, status: HealthStatus) -> List[str]:
        """Get resolution steps for health issues"""
        steps = [
            f"Check {component} service status and logs",
            f"Restart {component} service if necessary",
            f"Verify {component} configuration",
            f"Check {component} dependencies and resources"
        ]
        
        if "database" in component.lower():
            steps.extend([
                "Check database connectivity and credentials",
                "Verify database server is running",
                "Review database performance metrics"
            ])
        elif "storage" in component.lower():
            steps.extend([
                "Check storage connectivity and credentials", 
                "Verify storage service is accessible",
                "Review storage performance and capacity"
            ])
        
        return steps
    
    def _get_connectivity_resolution_steps(self, test_name: str, status: ConnectionStatus) -> List[str]:
        """Get resolution steps for connectivity issues"""
        steps = [
            f"Check network connectivity for {test_name}",
            f"Verify {test_name} service configuration",
            f"Test {test_name} credentials and permissions",
            f"Restart {test_name} service if necessary"
        ]
        
        if "vast" in test_name.lower():
            steps.extend([
                "Check VAST database server status",
                "Verify VAST endpoint URL and credentials",
                "Test VAST database connectivity manually"
            ])
        elif "s3" in test_name.lower():
            steps.extend([
                "Check S3 service availability",
                "Verify S3 endpoint and bucket configuration",
                "Test S3 credentials and permissions"
            ])
        
        return steps
    
    def _get_performance_resolution_steps(self, benchmark_name: str, status: PerformanceStatus) -> List[str]:
        """Get resolution steps for performance issues"""
        steps = [
            f"Investigate {benchmark_name} performance bottlenecks",
            f"Monitor system resources during {benchmark_name} operations",
            f"Optimize {benchmark_name} configuration",
            f"Consider scaling resources for {benchmark_name}"
        ]
        
        if "query" in benchmark_name.lower():
            steps.extend([
                "Review database query optimization",
                "Check database indexes and statistics",
                "Monitor database server performance"
            ])
        elif "connection" in benchmark_name.lower():
            steps.extend([
                "Check network latency and bandwidth",
                "Verify connection pooling configuration",
                "Monitor connection usage patterns"
            ])
        
        return steps
    
    def _get_compliance_resolution_steps(self, model_name: str, compliance_level: str) -> List[str]:
        """Get resolution steps for compliance issues"""
        steps = [
            f"Review {model_name} model definition against TAMS specification",
            f"Update {model_name} field names and types to match TAMS requirements",
            f"Test {model_name} API responses for TAMS compliance",
            f"Validate {model_name} model with TAMS specification tools"
        ]
        
        if compliance_level == "non_compliant":
            steps.insert(0, f"URGENT: {model_name} completely fails TAMS compliance")
            steps.extend([
                f"Completely rewrite {model_name} model to match TAMS specification",
                f"Review all {model_name} API endpoints for compliance"
            ])
        
        return steps
    
    async def get_quick_health_check(self) -> Dict[str, Any]:
        """Get quick health check for immediate status"""
        try:
            # Run minimal checks for quick feedback
            tasks = [
                self.connection_tester.run_connectivity_suite(include_performance=False),
                self.health_monitor.check_system_health()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            connectivity_result = results[0] if not isinstance(results[0], Exception) else None
            health_result = results[1] if not isinstance(results[1], Exception) else None
            
            # Quick assessment
            status = "healthy"
            issues = []
            
            if connectivity_result and connectivity_result.overall_status != ConnectionStatus.CONNECTED:
                status = "connectivity_issues"
                issues.append("Connectivity problems detected")
            
            if health_result and health_result.overall_status != HealthStatus.HEALTHY:
                status = "health_issues" if status == "healthy" else "multiple_issues"
                issues.append("System health problems detected")
            
            return {
                "status": status,
                "issues": issues,
                "connectivity_status": connectivity_result.overall_status.value if connectivity_result else "unknown",
                "health_status": health_result.overall_status.value if health_result else "unknown",
                "timestamp": datetime.utcnow().isoformat(),
                "quick_check": True
            }
            
        except Exception as e:
            return {
                "status": "error",
                "issues": [f"Quick health check failed: {str(e)}"],
                "timestamp": datetime.utcnow().isoformat(),
                "quick_check": True
            }
