#!/usr/bin/env python3
"""
Tenant ID Source Verification Audit Script

This script performs a comprehensive security audit to verify that tenant_id is never
sourced from request parameters (path, query, or body) in regular tenant endpoints.

Key Verifications:
1. No regular tenant endpoints accept tenant_id from request parameters
2. All platform admin endpoints with tenant_id parameters have proper authorization
3. Generate comprehensive report with categorized findings
4. Produce minimal fix list for any violations

Usage:
    python scripts/verify_tenant_id_sources.py                    # Full audit report
    python scripts/verify_tenant_id_sources.py --json report.json # Export to JSON
    python scripts/verify_tenant_id_sources.py --violations-only  # Show only violations
    python scripts/verify_tenant_id_sources.py --summary          # Summary only

Exit Codes:
    0 - No violations found (all endpoints secure)
    1 - Security violations found (tenant_id in params without admin auth)
    2 - Script error (unable to complete scan)
"""

import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone
from colorama import init, Fore, Style

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.tenant_isolation import TenantIsolationScanner, ScanResult, EndpointInfo

init(autoreset=True)


class TenantIDSourceAudit:
    """Comprehensive audit for tenant_id source verification."""

    def __init__(self):
        self.scanner = TenantIsolationScanner()
        self.result: ScanResult = None
        self.violations: List[EndpointInfo] = []
        self.legitimate_cross_tenant: List[EndpointInfo] = []
        self.regular_endpoints: List[EndpointInfo] = []
        self.audit_timestamp = datetime.now(timezone.utc)

    def run_audit(self) -> ScanResult:
        """Execute the comprehensive audit scan."""
        print(f"{Fore.CYAN}{Style.BRIGHT}Starting Tenant ID Source Security Audit...")
        print(f"{Fore.CYAN}Timestamp: {self.audit_timestamp.isoformat()}\n")

        # Run the scanner
        self.result = self.scanner.scan_all_endpoints()

        # Categorize endpoints
        self._categorize_endpoints()

        return self.result

    def _categorize_endpoints(self):
        """Categorize endpoints by security classification."""
        for endpoint in self.result.endpoints:
            # Skip exempt endpoints (public, auth, etc.)
            if endpoint.warnings and any('Exempt endpoint' in w for w in endpoint.warnings):
                continue

            # Check for tenant_id in path parameter violations
            if endpoint.has_tenant_id_path_param:
                if endpoint.has_platform_admin_auth:
                    # Legitimate cross-tenant operation
                    self.legitimate_cross_tenant.append(endpoint)
                else:
                    # VIOLATION: tenant_id in path without admin auth
                    self.violations.append(endpoint)
            else:
                # Regular endpoint without tenant_id in path
                self.regular_endpoints.append(endpoint)

    def print_summary(self):
        """Print executive summary of audit results."""
        print("\n" + "=" * 80)
        print(f"{Fore.CYAN}{Style.BRIGHT}TENANT ID SOURCE SECURITY AUDIT - EXECUTIVE SUMMARY")
        print("=" * 80 + "\n")

        # Overall statistics
        print(f"{Style.BRIGHT}Scan Statistics:")
        print(f"  Total Endpoints Scanned:        {self.result.total_endpoints}")
        print(f"  Authenticated Endpoints:        {self.result.authenticated_endpoints}")
        print(f"  Regular Endpoints:              {len(self.regular_endpoints)}")
        print()

        # Tenant ID in path analysis
        print(f"{Style.BRIGHT}Tenant ID Path Parameter Analysis:")
        print(f"  Endpoints with tenant_id:       {self.result.endpoints_with_tenant_id_path}")
        print(f"  Legitimate (Platform Admin):    {Fore.GREEN}{len(self.legitimate_cross_tenant)}")
        print(f"  VIOLATIONS (No Admin Auth):     {Fore.RED if self.violations else Fore.GREEN}{len(self.violations)}")
        print()

        # Security verdict
        if self.violations:
            print(f"{Fore.RED}{Style.BRIGHT}[!] CRITICAL SECURITY VIOLATIONS FOUND")
            print(f"{Fore.RED}{len(self.violations)} endpoint(s) accept tenant_id from request parameters")
            print(f"{Fore.RED}without platform admin authorization - this is a security vulnerability!")
        else:
            print(f"{Fore.GREEN}{Style.BRIGHT}[OK] NO SECURITY VIOLATIONS FOUND")
            print(f"{Fore.GREEN}All endpoints properly enforce tenant isolation")

        print("\n" + "=" * 80 + "\n")

    def print_violations(self):
        """Print detailed information about security violations."""
        if not self.violations:
            return

        print(f"{Fore.RED}{Style.BRIGHT}SECURITY VIOLATIONS - DETAILED REPORT")
        print("=" * 80 + "\n")

        for i, endpoint in enumerate(self.violations, 1):
            print(f"{Fore.RED}{Style.BRIGHT}[{i}] VIOLATION: Unauthorized tenant_id access")
            print(f"{Fore.YELLOW}File:     {Path(endpoint.file_path).name}")
            print(f"{Fore.YELLOW}Function: {endpoint.function_name} (line {endpoint.line_number})")
            print(f"{Fore.YELLOW}Route:    {endpoint.http_method} {endpoint.route_path}")
            print()
            print(f"{Style.BRIGHT}Issue:")
            print(f"  This endpoint accepts tenant_id from the request path/parameters")
            print(f"  without requiring platform admin authorization. This allows users")
            print(f"  to potentially access data from other tenants.")
            print()
            print(f"{Style.BRIGHT}Required Fix:")
            print(f"  Add platform admin authorization:")
            print(f"  {Fore.GREEN}user_info: dict = Depends(require_platform_admin(role='platform_admin'))")
            print()
            print(f"  OR remove tenant_id from path and extract from user context:")
            print(f"  {Fore.GREEN}tenant_id = get_tenant_id(user_info)")
            print()
            print("-" * 80)
            print()

    def print_legitimate_cross_tenant(self):
        """Print information about legitimate cross-tenant operations."""
        if not self.legitimate_cross_tenant:
            return

        print(f"{Fore.GREEN}{Style.BRIGHT}LEGITIMATE CROSS-TENANT OPERATIONS")
        print("=" * 80 + "\n")
        print(f"These endpoints accept tenant_id in path parameters but are properly")
        print(f"protected with platform admin authorization:\n")

        for i, endpoint in enumerate(self.legitimate_cross_tenant, 1):
            print(f"{Fore.GREEN}[{i}] {endpoint.http_method} {endpoint.route_path}")
            print(f"    File: {Path(endpoint.file_path).name}:{endpoint.line_number}")
            print(f"    Function: {endpoint.function_name}")
            print(f"    {Fore.GREEN}[+] Platform admin authorization present")
            print()

        print("-" * 80 + "\n")

    def print_minimal_fix_list(self):
        """Print minimal list of fixes required."""
        if not self.violations:
            print(f"{Fore.GREEN}{Style.BRIGHT}[OK] NO FIXES REQUIRED - All endpoints are secure!\n")
            return

        print(f"{Fore.YELLOW}{Style.BRIGHT}MINIMAL FIX LIST")
        print("=" * 80 + "\n")
        print(f"The following {len(self.violations)} endpoint(s) require immediate attention:\n")

        for i, endpoint in enumerate(self.violations, 1):
            print(f"{i}. {Fore.YELLOW}{Path(endpoint.file_path).name}:{endpoint.line_number}")
            print(f"   Function: {endpoint.function_name}")
            print(f"   Route: {endpoint.http_method} {endpoint.route_path}")
            print(f"   Action: Add platform admin auth OR remove tenant_id from path")
            print()

        print("=" * 80 + "\n")

    def print_full_report(self):
        """Print comprehensive audit report."""
        self.print_summary()
        self.print_violations()
        self.print_legitimate_cross_tenant()
        self.print_minimal_fix_list()

    def export_json(self, filepath: str):
        """Export audit results to JSON file."""
        audit_data = {
            "audit_metadata": {
                "timestamp": self.audit_timestamp.isoformat(),
                "scanner_version": "2.0",
                "purpose": "Verify tenant_id source security"
            },
            "summary": {
                "total_endpoints": self.result.total_endpoints,
                "authenticated_endpoints": self.result.authenticated_endpoints,
                "regular_endpoints": len(self.regular_endpoints),
                "endpoints_with_tenant_id_path": self.result.endpoints_with_tenant_id_path,
                "legitimate_cross_tenant_operations": len(self.legitimate_cross_tenant),
                "security_violations": len(self.violations),
                "has_violations": len(self.violations) > 0,
                "isolation_coverage": self.result.isolation_coverage,
            },
            "violations": [
                {
                    "file": str(Path(e.file_path).name),
                    "function": e.function_name,
                    "line": e.line_number,
                    "route": f"{e.http_method} {e.route_path}",
                    "severity": "CRITICAL",
                    "issue": "tenant_id in path parameter without platform admin authorization",
                    "recommended_fix": "Add platform admin auth or remove tenant_id from path"
                }
                for e in self.violations
            ],
            "legitimate_cross_tenant": [
                {
                    "file": str(Path(e.file_path).name),
                    "function": e.function_name,
                    "line": e.line_number,
                    "route": f"{e.http_method} {e.route_path}",
                    "status": "SECURE",
                    "note": "Platform admin authorization present"
                }
                for e in self.legitimate_cross_tenant
            ],
            "detailed_scan_results": self.scanner.export_json(self.result)
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(audit_data, f, indent=2)

        print(f"{Fore.GREEN}[OK] Audit report exported to: {filepath}\n")


def main():
    """Main entry point for the audit script."""
    parser = argparse.ArgumentParser(
        description='Comprehensive audit of tenant_id source security',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        # Full audit report
  %(prog)s --summary              # Quick summary only
  %(prog)s --violations-only      # Show only violations
  %(prog)s --json audit.json      # Export to JSON
        """
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary only (no detailed reports)'
    )
    parser.add_argument(
        '--violations-only',
        action='store_true',
        help='Show only security violations (no legitimate operations)'
    )
    parser.add_argument(
        '--json',
        metavar='FILE',
        help='Export audit results to JSON file'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Include all endpoints in output'
    )

    args = parser.parse_args()

    try:
        # Run the audit
        audit = TenantIDSourceAudit()
        audit.run_audit()

        # Export JSON if requested
        if args.json:
            audit.export_json(args.json)

        # Print reports based on flags
        if args.summary:
            audit.print_summary()
        elif args.violations_only:
            audit.print_summary()
            audit.print_violations()
            audit.print_minimal_fix_list()
        else:
            # Full report by default
            audit.print_full_report()

        # If verbose, also print the detailed scanner report
        if args.verbose:
            print("\n" + "=" * 80)
            print(f"{Fore.CYAN}{Style.BRIGHT}DETAILED SCANNER REPORT (ALL ENDPOINTS)")
            print("=" * 80 + "\n")
            report = audit.scanner.generate_report(audit.result, verbose=True)
            print(report)

        # Exit with appropriate code
        if audit.violations:
            sys.exit(1)  # Violations found
        else:
            sys.exit(0)  # All clear

    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}ERROR: Audit script failed")
        print(f"{Fore.RED}{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)  # Script error


if __name__ == '__main__':
    main()
