#!/usr/bin/env python3
"""Deploy a Salesforce metadata package to a target org.

Wraps `sf project deploy start` and `sf project deploy quick` with
structured output including deployment status, component counts,
failure details, and duration. Supports standard deploy from a manifest
and quick-deploy from a prior validation ID.

This script is always user-initiated. It should never be called from
automated pipelines without explicit human approval.
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import List, Optional


class CLIError(Exception):
    """Expected CLI failures."""
    pass


@dataclass
class ComponentResult:
    total: int = 0
    deployed: int = 0
    failed: int = 0


@dataclass
class DeploymentReport:
    deployment_id: str = ""
    status: str = "Unknown"
    target_org: str = ""
    manifest: str = ""
    deploy_mode: str = "standard"
    components: ComponentResult = field(default_factory=ComponentResult)
    failures: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy a Salesforce metadata package to a target org.",
        epilog="Examples:\n"
               "  %(prog)s --target-org qa --manifest package.xml\n"
               "  %(prog)s --target-org production --validation-id 0Af3t00000XXXXXX\n"
               "  %(prog)s --target-org qa --manifest package.xml --dry-run\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target-org",
        required=True,
        help="Alias or username of the target org",
    )
    parser.add_argument(
        "--manifest",
        help="Path to package.xml manifest file (for standard deploy)",
    )
    parser.add_argument(
        "--source-dir",
        help="Path to source directory (alternative to manifest)",
    )
    parser.add_argument(
        "--validation-id",
        help="Job ID from a prior successful validation (triggers quick-deploy)",
    )
    parser.add_argument(
        "--test-level",
        choices=["NoTestRun", "RunSpecifiedTests", "RunLocalTests", "RunAllTestsInOrg"],
        help="Apex test execution level (default: no tests, since validation already ran them)",
    )
    parser.add_argument(
        "--tests",
        help="Comma-separated test class names (for RunSpecifiedTests)",
    )
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show command without executing",
    )
    return parser.parse_args()


def build_deploy_command(args: argparse.Namespace) -> List[str]:
    """Build the sf project deploy start command."""
    cmd = ["sf", "project", "deploy", "start"]

    cmd.extend(["--target-org", args.target_org])

    if args.manifest:
        cmd.extend(["--manifest", args.manifest])
    elif args.source_dir:
        cmd.extend(["--source-dir", args.source_dir])

    if args.test_level:
        cmd.extend(["--test-level", args.test_level])
        if args.test_level == "RunSpecifiedTests" and args.tests:
            cmd.extend(["--tests", args.tests])

    cmd.extend(["--json", "--wait", str(args.timeout // 60)])

    return cmd


def build_quick_deploy_command(args: argparse.Namespace) -> List[str]:
    """Build the sf project deploy quick command."""
    cmd = [
        "sf", "project", "deploy", "quick",
        "--job-id", args.validation_id,
        "--target-org", args.target_org,
        "--json",
        "--wait", str(args.timeout // 60),
    ]
    return cmd


def run_command(cmd: List[str], timeout: int = 600) -> dict:
    """Execute a CLI command and return parsed JSON output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        if result.returncode != 0:
            raise CLIError(
                f"Command failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return {}
    except subprocess.TimeoutExpired:
        raise CLIError(f"Command timed out after {timeout} seconds")
    except json.JSONDecodeError:
        raise CLIError("Failed to parse command output as JSON")


def parse_deploy_result(
    raw: dict,
    target_org: str,
    manifest: str,
    deploy_mode: str,
) -> DeploymentReport:
    """Parse sf CLI JSON output into a DeploymentReport."""
    report = DeploymentReport(
        target_org=target_org,
        manifest=manifest,
        deploy_mode=deploy_mode,
    )

    result = raw.get("result", {})
    report.deployment_id = result.get("id", "")
    report.status = result.get("status", "Unknown")

    # Component counts
    comp_total = result.get("numberComponentsTotal", 0)
    comp_deployed = result.get("numberComponentsDeployed", 0)
    comp_errors = result.get("numberComponentErrors", 0)
    report.components = ComponentResult(
        total=comp_total,
        deployed=comp_deployed,
        failed=comp_errors,
    )

    # Failure details
    details = result.get("details", {})
    component_failures = details.get("componentFailures", [])
    if isinstance(component_failures, dict):
        component_failures = [component_failures]
    for failure in component_failures:
        comp_type = failure.get("componentType", "")
        full_name = failure.get("fullName", "")
        problem = failure.get("problem", "")
        report.failures.append(f"{comp_type}/{full_name}: {problem}")

    return report


def format_text(report: DeploymentReport) -> str:
    """Format a DeploymentReport as human-readable text."""
    lines = []
    status_label = "PASS" if report.status == "Succeeded" else "FAIL"
    lines.append(f"Deployment: {status_label}")
    lines.append(f"  Deploy ID:  {report.deployment_id}")
    lines.append(f"  Target Org: {report.target_org}")
    lines.append(f"  Mode:       {report.deploy_mode}")
    lines.append(f"  Manifest:   {report.manifest}")
    lines.append(f"  Duration:   {report.duration_seconds:.0f}s")
    lines.append("")
    lines.append(
        f"Components: {report.components.deployed}/{report.components.total} "
        f"deployed, {report.components.failed} failed"
    )

    if report.failures:
        lines.append("")
        lines.append("Failures:")
        for err in report.failures:
            lines.append(f"  - {err}")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    if args.validation_id:
        # Quick-deploy mode
        deploy_mode = "quick-deploy"
        cmd = build_quick_deploy_command(args)
        manifest_label = f"validation:{args.validation_id}"
    else:
        # Standard deploy mode
        deploy_mode = "standard"
        if not args.manifest and not args.source_dir:
            raise CLIError(
                "Either --manifest, --source-dir, or --validation-id is required"
            )
        cmd = build_deploy_command(args)
        manifest_label = args.manifest or args.source_dir or ""

    if args.dry_run:
        print(f"Would execute: {' '.join(cmd)}")
        return 0

    start = time.time()
    raw = run_command(cmd, timeout=args.timeout)
    elapsed = time.time() - start

    report = parse_deploy_result(raw, args.target_org, manifest_label, deploy_mode)
    report.duration_seconds = round(elapsed, 1)

    # Output
    if args.format == "json":
        print(json.dumps(asdict(report), indent=2))
    else:
        print(format_text(report))

    # Exit code based on status
    if report.status == "Succeeded":
        return 0
    elif report.failures:
        return 2
    else:
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
