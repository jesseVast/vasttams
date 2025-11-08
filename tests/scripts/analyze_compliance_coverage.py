#!/usr/bin/env python3
"""
Analyze TAMS 8.0 Compliance Test Coverage

This script compares the TAMS 8.0 OpenAPI specification with the existing
compliance tests to identify gaps in test coverage.
"""

import re
import json
from pathlib import Path
from collections import defaultdict

# Paths
SPEC_FILE = Path(__file__).parent.parent / "tams-8.0" / "api" / "TimeAddressableMediaStore.yaml"
COMPLIANCE_TESTS_DIR = Path(__file__).parent

def extract_endpoints_from_spec():
    """Extract all endpoints from the OpenAPI spec"""
    endpoints = defaultdict(list)
    
    if not SPEC_FILE.exists():
        print(f"ERROR: Spec file not found: {SPEC_FILE}")
        return endpoints
    
    with open(SPEC_FILE, 'r') as f:
        content = f.read()
    
    # Extract path patterns
    path_pattern = r'^\s+/([^:]+):'
    paths = re.findall(path_pattern, content, re.MULTILINE)
    
    # Extract operations for each path
    current_path = None
    for line in content.split('\n'):
        # Match path definition
        path_match = re.match(r'^\s+/([^:]+):', line)
        if path_match:
            current_path = '/' + path_match.group(1)
            continue
        
        # Match HTTP methods
        method_match = re.match(r'^\s+(get|post|put|delete|head|options|patch):', line, re.IGNORECASE)
        if method_match and current_path:
            method = method_match.group(1).upper()
            endpoints[current_path].append(method)
    
    return endpoints

def extract_tested_endpoints():
    """Extract endpoints tested in compliance test files"""
    tested = defaultdict(set)
    
    compliance_files = list(COMPLIANCE_TESTS_DIR.glob("**/test_compliance.py"))
    
    for test_file in compliance_files:
        with open(test_file, 'r') as f:
            lines = f.readlines()
        
        # Find all API calls - look for patterns like:
        # requests.get(f"{BASE_URL}/sources", ...)
        # requests.post(f"{BASE_URL}/flows/{flow_id}", ...)
        for i, line in enumerate(lines):
            # Match requests.METHOD(f"{BASE_URL}/path", ...)
            pattern = r'requests\.(get|post|put|delete|head)\s*\(\s*f?"[^"]*\{[^}]*BASE_URL[^}]*\}([^"]+)"'
            matches = re.findall(pattern, line, re.IGNORECASE)
            for method, path_part in matches:
                # Extract path from f-string
                # Handle patterns like f"{BASE_URL}/sources" or f"{BASE_URL}/flows/{flow_id}"
                path_match = re.search(r'/([^"]+)', path_part)
                if path_match:
                    # Normalize path - replace variables with placeholders
                    path = '/' + path_match.group(1)
                    # Replace common variable patterns
                    path = re.sub(r'\{[^}]+\}', '{id}', path)
                    path = re.sub(r'\{[^}]+\}', '{name}', path)
                    tested[path].add(method.upper())
            
            # Also match direct URL strings
            url_pattern = r'f?"[^"]*\{[^}]*BASE_URL[^}]*\}(/[^"]+)"'
            url_matches = re.findall(url_pattern, line, re.IGNORECASE)
            for path_part in url_matches:
                path_match = re.search(r'/([^"]+)', path_part)
                if path_match:
                    path = '/' + path_match.group(1)
                    path = re.sub(r'\{[^}]+\}', '{id}', path)
                    path = re.sub(r'\{[^}]+\}', '{name}', path)
                    # Try to infer method from context (look at previous lines)
                    if i > 0:
                        prev_line = lines[i-1].lower()
                        if 'requests.get' in prev_line or 'get' in prev_line:
                            tested[path].add('GET')
                        elif 'requests.post' in prev_line or 'post' in prev_line:
                            tested[path].add('POST')
                        elif 'requests.put' in prev_line or 'put' in prev_line:
                            tested[path].add('PUT')
                        elif 'requests.delete' in prev_line or 'delete' in prev_line:
                            tested[path].add('DELETE')
                        elif 'requests.head' in prev_line or 'head' in prev_line:
                            tested[path].add('HEAD')
    
    return tested

def categorize_endpoints(endpoints):
    """Categorize endpoints by resource type"""
    categories = {
        'Service': [],
        'Sources': [],
        'Flows': [],
        'Segments': [],
        'Objects': [],
        'Storage Backends': [],
        'Webhooks': [],
        'Deletion Requests': [],
        'Other': []
    }
    
    for path, methods in endpoints.items():
        if path == '/' or path.startswith('/service'):
            if 'webhook' in path:
                categories['Webhooks'].append((path, methods))
            elif 'storage-backend' in path:
                categories['Storage Backends'].append((path, methods))
            else:
                categories['Service'].append((path, methods))
        elif path.startswith('/sources'):
            categories['Sources'].append((path, methods))
        elif path.startswith('/flows'):
            if '/segments' in path:
                categories['Segments'].append((path, methods))
            else:
                categories['Flows'].append((path, methods))
        elif path.startswith('/objects'):
            categories['Objects'].append((path, methods))
        elif path.startswith('/flow-delete-requests'):
            categories['Deletion Requests'].append((path, methods))
        else:
            categories['Other'].append((path, methods))
    
    return categories

def main():
    print("=" * 80)
    print("TAMS 8.0 Compliance Test Coverage Analysis")
    print("=" * 80)
    print()
    
    # Extract endpoints from spec
    print("📋 Extracting endpoints from TAMS 8.0 OpenAPI specification...")
    spec_endpoints = extract_endpoints_from_spec()
    print(f"   Found {len(spec_endpoints)} unique paths in spec")
    
    # Extract tested endpoints
    print("🧪 Analyzing compliance test files...")
    tested_endpoints = extract_tested_endpoints()
    print(f"   Found {len(tested_endpoints)} unique paths in tests")
    
    # Categorize
    spec_categories = categorize_endpoints(spec_endpoints)
    tested_categories = categorize_endpoints(tested_endpoints)
    
    # Generate report
    print()
    print("=" * 80)
    print("COVERAGE ANALYSIS BY CATEGORY")
    print("=" * 80)
    print()
    
    total_spec = 0
    total_tested = 0
    
    for category in ['Service', 'Sources', 'Flows', 'Segments', 'Objects', 
                     'Storage Backends', 'Webhooks', 'Deletion Requests', 'Other']:
        spec_paths = spec_categories[category]
        tested_paths = tested_categories[category]
        
        spec_count = sum(len(methods) for _, methods in spec_paths)
        tested_count = sum(len(methods) for _, methods in tested_paths)
        
        total_spec += spec_count
        total_tested += tested_count
        
        coverage = (tested_count / spec_count * 100) if spec_count > 0 else 0
        
        print(f"\n{category}:")
        print(f"  Spec endpoints: {spec_count}")
        print(f"  Tested endpoints: {tested_count}")
        print(f"  Coverage: {coverage:.1f}%")
        
        # Show missing endpoints
        spec_paths_set = {path for path, _ in spec_paths}
        tested_paths_set = {path for path, _ in tested_paths}
        missing = spec_paths_set - tested_paths_set
        
        if missing:
            print(f"  ⚠️  Missing paths ({len(missing)}):")
            for path in sorted(missing)[:10]:  # Show first 10
                methods = [m for p, m in spec_paths if p == path][0]
                print(f"     {path} [{', '.join(methods)}]")
            if len(missing) > 10:
                print(f"     ... and {len(missing) - 10} more")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    overall_coverage = (total_tested / total_spec * 100) if total_spec > 0 else 0
    print(f"Total spec endpoints: {total_spec}")
    print(f"Total tested endpoints: {total_tested}")
    print(f"Overall coverage: {overall_coverage:.1f}%")
    print()
    
    # Detailed gap analysis
    print("=" * 80)
    print("DETAILED GAP ANALYSIS")
    print("=" * 80)
    print()
    
    all_spec_paths = set(spec_endpoints.keys())
    all_tested_paths = set(tested_endpoints.keys())
    missing_paths = all_spec_paths - all_tested_paths
    
    if missing_paths:
        print(f"⚠️  {len(missing_paths)} paths from spec are not tested:")
        for path in sorted(missing_paths):
            methods = spec_endpoints[path]
            print(f"   {path} [{', '.join(methods)}]")
    else:
        print("✅ All paths from spec are covered by tests!")
    
    print()
    print("=" * 80)
    print("NOTE: This analysis is based on URL patterns found in test files.")
    print("Some endpoints may be tested indirectly or through integration tests.")
    print("=" * 80)

if __name__ == "__main__":
    main()

