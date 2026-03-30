#!/usr/bin/env python3
"""Create a deployment bundle branch and merge feature branches.

Assembles a promotion bundle by creating a branch from the target
environment branch and merging specified feature branches into it.
Validates completeness and outputs a manifest summary.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


class CLIError(Exception):
    """Expected CLI failures."""
    pass


def detect_tool(cmd_parts: list) -> bool:
    """Check if a CLI tool is available by running it."""
    try:
        subprocess.run(cmd_parts, capture_output=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


ENV_BRANCHES = {
    "dev1": "dev1",
    "qa": "qa",
    "uat": "uat",
    "production": "main",
    "main": "main",
}


@dataclass
class MergeResult:
    story: str
    branch: str
    status: str  # "merged", "conflict", "not_found"
    conflicts: List[str] = field(default_factory=list)


@dataclass
class BundleReport:
    bundle_id: str = ""
    bundle_branch: str = ""
    target_env: str = ""
    target_branch: str = ""
    stories: List[str] = field(default_factory=list)
    merge_results: List[MergeResult] = field(default_factory=list)
    auto_resolved: List[str] = field(default_factory=list)
    manual_review: List[str] = field(default_factory=list)
    status: str = "pending"
    delta_manifest: str = ""
    created_at: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a deployment bundle branch and merge feature branches.",
        epilog="Examples:\n"
               "  %(prog)s --stories US-1234,US-1235 --target-env qa\n"
               "  %(prog)s --stories US-9999 --target-env uat --bundle-id B0042\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--stories",
        required=True,
        help="Comma-separated Jira story keys (e.g., US-1234,US-1235)",
    )
    parser.add_argument(
        "--target-env",
        required=True,
        choices=list(ENV_BRANCHES.keys()),
        help="Target environment for the promotion",
    )
    parser.add_argument("--bundle-id", help="Override bundle ID (default: auto-generated)")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    return parser.parse_args()


def run_git(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Execute a git command."""
    cmd = ["git"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise CLIError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def get_next_bundle_id() -> str:
    """Generate the next bundle ID from existing branches."""
    result = run_git(["branch", "-r", "--list", "*/bundle/B*"], check=False)
    existing = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if "bundle/B" in line:
            try:
                num = int(line.split("bundle/B")[-1])
                existing.append(num)
            except ValueError:
                continue
    next_id = max(existing, default=0) + 1
    return f"B{next_id:04d}"


def branch_exists(branch: str) -> bool:
    """Check if a branch exists locally or remotely."""
    local = run_git(["branch", "--list", branch], check=False)
    if local.stdout.strip():
        return True
    remote = run_git(["branch", "-r", "--list", f"*/{branch}"], check=False)
    return bool(remote.stdout.strip())


def is_auto_resolvable(filepath: str) -> bool:
    """Check if a conflicting file is safe to auto-resolve."""
    auto_patterns = [
        ".profile-meta.xml",
        ".permissionset-meta.xml",
        ".layout-meta.xml",
    ]
    return any(filepath.endswith(p) for p in auto_patterns)


def create_bundle(args: argparse.Namespace) -> BundleReport:
    """Create the bundle branch and merge features."""
    stories = [s.strip() for s in args.stories.split(",")]
    target_branch = ENV_BRANCHES.get(args.target_env, args.target_env)
    bundle_id = args.bundle_id or get_next_bundle_id()
    bundle_branch = f"bundle/{bundle_id}"

    report = BundleReport(
        bundle_id=bundle_id,
        bundle_branch=bundle_branch,
        target_env=args.target_env,
        target_branch=target_branch,
        stories=stories,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    if args.dry_run:
        report.status = "dry_run"
        for story in stories:
            feature_branch = f"feature/{story}"
            exists = branch_exists(feature_branch)
            report.merge_results.append(MergeResult(
                story=story,
                branch=feature_branch,
                status="would_merge" if exists else "not_found",
            ))
        return report

    # Fetch latest
    run_git(["fetch", "origin"])

    # Create bundle branch from target
    run_git(["checkout", f"origin/{target_branch}"])
    run_git(["checkout", "-b", bundle_branch])

    # Merge each feature branch
    for story in stories:
        feature_branch = f"feature/{story}"
        if not branch_exists(feature_branch):
            report.merge_results.append(MergeResult(
                story=story,
                branch=feature_branch,
                status="not_found",
            ))
            continue

        merge_result = run_git(
            ["merge", f"origin/{feature_branch}", "--no-edit"],
            check=False,
        )

        if merge_result.returncode == 0:
            report.merge_results.append(MergeResult(
                story=story,
                branch=feature_branch,
                status="merged",
            ))
        else:
            # Check for conflicts
            status = run_git(["diff", "--name-only", "--diff-filter=U"], check=False)
            conflict_files = [f for f in status.stdout.strip().split("\n") if f]

            auto = [f for f in conflict_files if is_auto_resolvable(f)]
            manual = [f for f in conflict_files if not is_auto_resolvable(f)]

            # Auto-resolve safe files
            for f in auto:
                run_git(["checkout", "--theirs", f], check=False)
                run_git(["add", f], check=False)
                report.auto_resolved.append(f)

            if manual:
                report.manual_review.extend(manual)

            if not manual:
                run_git(["commit", "--no-edit"], check=False)

            report.merge_results.append(MergeResult(
                story=story,
                branch=feature_branch,
                status="conflict" if manual else "merged",
                conflicts=conflict_files,
            ))

    # Determine overall status
    has_manual = any(r.status == "conflict" for r in report.merge_results)
    has_missing = any(r.status == "not_found" for r in report.merge_results)
    if has_manual:
        report.status = "conflicts_pending"
    elif has_missing:
        report.status = "partial"
    else:
        report.status = "ready"

    # Generate delta manifest with SGD if available and bundle is ready
    if report.status == "ready" and detect_tool(["sf", "sgd", "--help"]):
        sgd_result = subprocess.run(
            [
                "sf", "sgd", "source", "delta",
                "--from", f"origin/{target_branch}",
                "--to", bundle_branch,
                "--output-dir", "delta/",
                "--generate-delta",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        if sgd_result.returncode == 0:
            report.delta_manifest = "delta/package/package.xml"

    return report


def format_text(report: BundleReport) -> str:
    """Format a BundleReport as human-readable text."""
    lines = []
    lines.append(f"Bundle: {report.bundle_branch}")
    lines.append(f"  Target:  {report.target_env} ({report.target_branch})")
    lines.append(f"  Status:  {report.status}")
    lines.append(f"  Stories: {', '.join(report.stories)}")
    lines.append(f"  Created: {report.created_at}")
    lines.append("")

    lines.append("Merge Results:")
    for r in report.merge_results:
        icon = {"merged": "OK", "conflict": "CONFLICT", "not_found": "MISSING",
                "would_merge": "PLAN"}.get(r.status, r.status)
        lines.append(f"  [{icon}] {r.story} ({r.branch})")
        if r.conflicts:
            for f in r.conflicts:
                lines.append(f"         - {f}")

    if report.auto_resolved:
        lines.append("")
        lines.append(f"Auto-Resolved ({len(report.auto_resolved)} files):")
        for f in report.auto_resolved:
            lines.append(f"  - {f}")

    if report.manual_review:
        lines.append("")
        lines.append(f"Manual Review Required ({len(report.manual_review)} files):")
        for f in report.manual_review:
            lines.append(f"  - {f}")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    report = create_bundle(args)

    if args.format == "json":
        print(json.dumps(asdict(report), indent=2))
    else:
        print(format_text(report))

    if report.status == "ready" or report.status == "dry_run":
        return 0
    elif report.status == "conflicts_pending":
        return 1
    else:
        return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
