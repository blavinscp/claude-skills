#!/usr/bin/env python3
"""Validate a Salesforce deployment package against a target org.

Wraps `sf project deploy validate` with structured output including
pass/fail status, Apex test results, and code coverage metrics.
Stores validation job ID for subsequent quick-deploy.
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional


class CLIError(Exception):
    """Expected CLI failures."""
    pass


def detect_tool(cmd_parts: list) -> bool:
    """Check whether an external CLI tool is available."""
    try:
        subprocess.run(cmd_parts, capture_output=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@dataclass
class ComponentResult:
    total: int = 0
    deployed: int = 0
    errors: int = 0


@dataclass
class TestResult:
    total: int = 0
    passing: int = 0
    failing: int = 0
    skipped: int = 0


@dataclass
class CoverageResult:
    overall: float = 0.0
    classes_below_75: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    validation_id: str = ""
    status: str = "Unknown"
    target_org: str = ""
    test_level: str = ""
    manifest: str = ""
    components: ComponentResult = field(default_factory=ComponentResult)
    tests: TestResult = field(default_factory=TestResult)
    coverage: CoverageResult = field(default_factory=CoverageResult)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Salesforce deployment package against a target org.",
        epilog="Examples:\n"
               "  %(prog)s --target-org qa --manifest package.xml\n"
               "  %(prog)s --target-org qa --test-level RunSpecifiedTests --tests Test1,Test2\n"
               "  %(prog)s --job-id 0Af3t00000XXXXXX\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--target-org", help="Alias or username of the target org")
    parser.add_argument("--manifest", help="Path to package.xml manifest file")
    parser.add_argument("--source-dir", help="Path to source directory (alternative to manifest)")
    parser.add_argument(
        "--test-level",
        choices=["NoTestRun", "RunSpecifiedTests", "RunLocalTests", "RunAllTestsInOrg"],
        default="RunLocalTests",
        help="Apex test execution level (default: RunLocalTests)",
    )
    parser.add_argument("--tests", help="Comma-separated test class names (for RunSpecifiedTests)")
    parser.add_argument("--job-id", help="Check status of existing validation job")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds between status polls (default: 30)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Maximum wait time in seconds (default: 3600)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show command without executing")
    parser.add_argument(
        "--omnistudio-tool",
        choices=["native", "vlocity"],
        default="native",
        help="Tool for OmniStudio validation: native (sf CLI sequencing) or vlocity (vlocity_build)",
    )
    return parser.parse_args()


def build_validate_command(args: argparse.Namespace) -> List[str]:
    """Build the sf project deploy validate command."""
    cmd = ["sf", "project", "deploy", "validate"]

    if args.target_org:
        cmd.extend(["--target-org", args.target_org])

    if args.manifest:
        cmd.extend(["--manifest", args.manifest])
    elif args.source_dir:
        cmd.extend(["--source-dir", args.source_dir])

    cmd.extend(["--test-level", args.test_level])

    if args.test_level == "RunSpecifiedTests" and args.tests:
        cmd.extend(["--tests", args.tests])

    cmd.extend(["--json", "--wait", str(args.timeout // 60)])

    return cmd


def build_status_command(job_id: str, target_org: Optional[str] = None) -> List[str]:
    """Build command to check validation job status."""
    cmd = ["sf", "project", "deploy", "report", "--job-id", job_id, "--json"]
    if target_org:
        cmd.extend(["--target-org", target_org])
    return cmd


def run_command(cmd: List[str]) -> dict:
    """Execute a CLI command and return parsed JSON output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        if result.returncode != 0:
            raise CLIError(f"Command failed (exit {result.returncode}): {result.stderr.strip()}")
        return {}
    except subprocess.TimeoutExpired:
        raise CLIError("Command timed out after 600 seconds")
    except json.JSONDecodeError:
        raise CLIError(f"Failed to parse command output as JSON")


def parse_validation_result(raw: dict, target_org: str, test_level: str,
                            manifest: str) -> ValidationReport:
    """Parse sf CLI JSON output into a ValidationReport."""
    report = ValidationReport(
        target_org=target_org,
        test_level=test_level,
        manifest=manifest or "",
    )

    result = raw.get("result", {})
    report.validation_id = result.get("id", "")
    report.status = result.get("status", "Unknown")

    # Component results
    deploy_details = result.get("numberComponentsDeployed", 0)
    deploy_errors = result.get("numberComponentErrors", 0)
    deploy_total = result.get("numberComponentsTotal", 0)
    report.components = ComponentResult(
        total=deploy_total,
        deployed=deploy_details,
        errors=deploy_errors,
    )

    # Test results
    tests_total = result.get("numberTestsTotal", 0)
    tests_completed = result.get("numberTestsCompleted", 0)
    tests_errors = result.get("numberTestErrors", 0)
    report.tests = TestResult(
        total=tests_total,
        passing=tests_completed - tests_errors,
        failing=tests_errors,
        skipped=tests_total - tests_completed,
    )

    # Coverage
    coverage_data = result.get("runTestResult", {})
    if coverage_data:
        code_coverage = coverage_data.get("codeCoverage", [])
        if code_coverage:
            total_lines = sum(c.get("numLocations", 0) for c in code_coverage)
            covered_lines = sum(
                c.get("numLocations", 0) - c.get("numLocationsNotCovered", 0)
                for c in code_coverage
            )
            overall = (covered_lines / total_lines * 100) if total_lines > 0 else 0
            below_75 = [
                c.get("name", "Unknown")
                for c in code_coverage
                if c.get("numLocations", 0) > 0
                and ((c.get("numLocations", 0) - c.get("numLocationsNotCovered", 0))
                     / c.get("numLocations", 1) * 100) < 75
            ]
            report.coverage = CoverageResult(
                overall=round(overall, 1),
                classes_below_75=below_75,
            )

    # Errors
    details = result.get("details", {})
    component_failures = details.get("componentFailures", [])
    if isinstance(component_failures, dict):
        component_failures = [component_failures]
    for failure in component_failures:
        msg = f"{failure.get('componentType', '')}/{failure.get('fullName', '')}: {failure.get('problem', '')}"
        report.errors.append(msg)

    return report


def format_text(report: ValidationReport) -> str:
    """Format a ValidationReport as human-readable text."""
    lines = []
    status_icon = "PASS" if report.status == "Succeeded" else "FAIL"
    lines.append(f"Validation: {status_icon}")
    lines.append(f"  Job ID:     {report.validation_id}")
    lines.append(f"  Target Org: {report.target_org}")
    lines.append(f"  Test Level: {report.test_level}")
    lines.append(f"  Manifest:   {report.manifest}")
    lines.append(f"  Duration:   {report.duration_seconds:.0f}s")
    lines.append("")
    lines.append(f"Components: {report.components.deployed}/{report.components.total} deployed, {report.components.errors} errors")
    lines.append(f"Tests:      {report.tests.passing}/{report.tests.total} passing, {report.tests.failing} failing")
    lines.append(f"Coverage:   {report.coverage.overall}%")

    if report.coverage.classes_below_75:
        lines.append(f"  Below 75%: {', '.join(report.coverage.classes_below_75)}")

    if report.errors:
        lines.append("")
        lines.append("Errors:")
        for err in report.errors:
            lines.append(f"  - {err}")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    # Mode 1: Check existing job
    if args.job_id:
        cmd = build_status_command(args.job_id, args.target_org)
        if args.dry_run:
            print(f"Would execute: {' '.join(cmd)}")
            return 0
        raw = run_command(cmd)
        report = parse_validation_result(raw, args.target_org or "", "", "")
        report.validation_id = args.job_id
    else:
        # Mode 2: New validation
        if not args.target_org:
            raise CLIError("--target-org is required for new validations")
        if not args.manifest and not args.source_dir:
            raise CLIError("Either --manifest or --source-dir is required")
        if args.test_level == "RunSpecifiedTests" and not args.tests:
            raise CLIError("--tests is required when test-level is RunSpecifiedTests")

        cmd = build_validate_command(args)
        if args.dry_run:
            print(f"Would execute: {' '.join(cmd)}")
            return 0

        start = time.time()
        raw = run_command(cmd)
        elapsed = time.time() - start

        report = parse_validation_result(
            raw,
            args.target_org,
            args.test_level,
            args.manifest or args.source_dir or "",
        )
        report.duration_seconds = round(elapsed, 1)

    # Check vlocity_build availability if selected
    omnistudio_note = None
    if args.omnistudio_tool == "vlocity":
        if detect_tool(["vlocity", "--help"]):
            omnistudio_note = "vlocity_build selected and available for OmniStudio validation"
        else:
            omnistudio_note = "vlocity_build selected but not found on PATH; falling back to native sf CLI sequencing"

    # Output
    report_dict = asdict(report)
    if omnistudio_note:
        report_dict["omnistudio_tool"] = args.omnistudio_tool
        report_dict["omnistudio_note"] = omnistudio_note

    if args.format == "json":
        print(json.dumps(report_dict, indent=2))
    else:
        text_output = format_text(report)
        if omnistudio_note:
            text_output += f"\n\nOmniStudio: {omnistudio_note}"
        print(text_output)

    # Exit code based on status
    if report.status == "Succeeded":
        return 0
    elif report.errors:
        return 2
    else:
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
