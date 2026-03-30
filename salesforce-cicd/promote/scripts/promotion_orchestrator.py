#!/usr/bin/env python3
"""Orchestrate the full Salesforce promotion workflow.

Coordinates: bundle creation -> conflict resolution -> profile cleaning ->
validation -> GitLab MR creation -> Jira updates. Single entry point
replacing Copado promotions.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


class CLIError(Exception):
    """Expected CLI failures."""
    pass


ENV_BRANCHES = {
    "dev1": "dev1",
    "qa": "qa",
    "uat": "uat",
    "production": "main",
    "main": "main",
}

PROMOTION_PATH = ["dev1", "qa", "uat", "main"]


@dataclass
class StepResult:
    step: str
    status: str  # "success", "warning", "failed", "skipped"
    message: str = ""
    data: Dict = field(default_factory=dict)


@dataclass
class PromotionReport:
    stories: List[str] = field(default_factory=list)
    from_env: str = ""
    to_env: str = ""
    bundle_branch: str = ""
    hotfix: bool = False
    steps: List[StepResult] = field(default_factory=list)
    status: str = "pending"
    validation_id: str = ""
    mr_url: str = ""
    started_at: str = ""
    completed_at: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orchestrate a full Salesforce promotion workflow.",
        epilog="Examples:\n"
               "  %(prog)s --stories US-1234 --from-env dev1 --to-env qa\n"
               "  %(prog)s --stories US-9999 --from-env dev1 --to-env uat --hotfix\n"
               "  %(prog)s --stories US-1234,US-1235 --from-env dev1 --to-env qa\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--stories",
        required=True,
        help="Comma-separated Jira story keys",
    )
    parser.add_argument(
        "--from-env",
        required=True,
        choices=list(ENV_BRANCHES.keys()),
        help="Source environment",
    )
    parser.add_argument(
        "--to-env",
        required=True,
        choices=list(ENV_BRANCHES.keys()),
        help="Target environment",
    )
    parser.add_argument("--hotfix", action="store_true", help="Hotfix promotion (fast-track)")
    parser.add_argument("--skip-validate", action="store_true", help="Skip validation step (NOT recommended)")
    parser.add_argument("--bundle-id", help="Override bundle ID")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    return parser.parse_args()


def validate_promotion_path(from_env: str, to_env: str, hotfix: bool) -> None:
    """Validate that the promotion path is allowed."""
    if from_env == to_env:
        raise CLIError(f"Source and target environments cannot be the same: {from_env}")

    from_idx = PROMOTION_PATH.index(from_env) if from_env in PROMOTION_PATH else -1
    to_idx = PROMOTION_PATH.index(to_env) if to_env in PROMOTION_PATH else -1

    if from_idx < 0 or to_idx < 0:
        raise CLIError(f"Unknown environment in promotion path")

    if to_idx <= from_idx:
        raise CLIError(f"Cannot promote backwards: {from_env} -> {to_env}")

    if not hotfix and to_idx - from_idx > 1:
        raise CLIError(
            f"Standard promotions must follow the path: {' -> '.join(PROMOTION_PATH)}. "
            f"Use --hotfix to skip intermediate environments."
        )


def run_step(name: str, cmd: List[str], report: PromotionReport,
             dry_run: bool = False) -> StepResult:
    """Run a pipeline step and record the result."""
    if dry_run:
        result = StepResult(
            step=name,
            status="skipped",
            message=f"Dry run: would execute {' '.join(cmd)}",
        )
        report.steps.append(result)
        return result

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        output = proc.stdout.strip()

        # Try to parse JSON output
        data = {}
        if output:
            try:
                data = json.loads(output)
            except json.JSONDecodeError:
                data = {"raw_output": output}

        if proc.returncode == 0:
            result = StepResult(step=name, status="success", data=data)
        elif proc.returncode == 1:
            result = StepResult(step=name, status="warning",
                                message=proc.stderr.strip(), data=data)
        else:
            result = StepResult(step=name, status="failed",
                                message=proc.stderr.strip(), data=data)

    except subprocess.TimeoutExpired:
        result = StepResult(step=name, status="failed", message="Step timed out")
    except FileNotFoundError:
        result = StepResult(step=name, status="failed",
                            message=f"Command not found: {cmd[0]}")

    report.steps.append(result)
    return result


def orchestrate(args: argparse.Namespace) -> PromotionReport:
    """Run the full promotion orchestration."""
    stories = [s.strip() for s in args.stories.split(",")]
    stories_csv = ",".join(stories)

    report = PromotionReport(
        stories=stories,
        from_env=args.from_env,
        to_env=args.to_env,
        hotfix=args.hotfix,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    # Step 1: Create bundle
    bundle_args = [
        "python3", "salesforce-cicd/promote/scripts/create_bundle.py",
        "--stories", stories_csv,
        "--target-env", args.to_env,
        "--format", "json",
    ]
    if args.bundle_id:
        bundle_args.extend(["--bundle-id", args.bundle_id])
    if args.dry_run:
        bundle_args.append("--dry-run")

    step = run_step("create_bundle", bundle_args, report, dry_run=False)
    if step.status == "failed":
        report.status = "failed"
        return report

    bundle_data = step.data
    report.bundle_branch = bundle_data.get("bundle_branch", "")

    # Check for manual conflicts
    if bundle_data.get("status") == "conflicts_pending":
        report.status = "conflicts_pending"
        report.steps.append(StepResult(
            step="conflict_check",
            status="warning",
            message="Manual conflict resolution required before continuing",
            data={"manual_review": bundle_data.get("manual_review", [])},
        ))
        return report

    # Step 2: Profile cleaning
    profile_step = run_step(
        "profile_clean",
        ["python3", "salesforce-cicd/profile-clean/scripts/strip_profiles.py",
         "--source-dir", "force-app/main/default",
         "--format", "json"],
        report,
        dry_run=args.dry_run,
    )

    # Step 3: Validation
    if not args.skip_validate:
        test_level = "RunSpecifiedTests" if args.hotfix else "RunLocalTests"
        validate_cmd = [
            "python3", "salesforce-cicd/validate/scripts/validate_deployment.py",
            "--target-org", args.to_env,
            "--manifest", "force-app/main/default/package.xml",
            "--test-level", test_level,
            "--format", "json",
        ]
        validate_step = run_step("validate", validate_cmd, report, dry_run=args.dry_run)

        if validate_step.status == "failed":
            report.status = "validation_failed"
            return report

        report.validation_id = validate_step.data.get("validation_id", "")
    else:
        report.steps.append(StepResult(
            step="validate",
            status="skipped",
            message="Validation skipped (--skip-validate). NOT recommended.",
        ))

    # Step 4: Create GitLab MR (via MCP — documented as instruction, not executed)
    mr_title = f"Promote {stories_csv} to {args.to_env}"
    if args.hotfix:
        mr_title = f"[HOTFIX] {mr_title}"

    mr_description_lines = [
        f"## Promotion: {args.from_env} -> {args.to_env}",
        f"**Stories:** {stories_csv}",
        f"**Bundle:** {report.bundle_branch}",
        f"**Validation ID:** {report.validation_id}",
        f"**Hotfix:** {'Yes' if args.hotfix else 'No'}",
    ]

    report.steps.append(StepResult(
        step="create_mr",
        status="success" if args.dry_run else "pending",
        message="Create MR via GitLab MCP",
        data={
            "title": mr_title,
            "source_branch": report.bundle_branch,
            "target_branch": ENV_BRANCHES.get(args.to_env, args.to_env),
            "description": "\n".join(mr_description_lines),
            "labels": ["hotfix"] if args.hotfix else ["promotion"],
        },
    ))

    # Step 5: Audit log
    audit_step = run_step(
        "audit_log",
        ["python3", "salesforce-cicd/audit-log/scripts/audit_logger.py",
         "--action", "promote",
         "--environment", args.to_env,
         "--status", "initiated",
         "--details", json.dumps({"stories": stories, "bundle": report.bundle_branch}),
         "--format", "json"],
        report,
        dry_run=args.dry_run,
    )

    report.status = "ready_for_review"
    report.completed_at = datetime.now(timezone.utc).isoformat()
    return report


def format_text(report: PromotionReport) -> str:
    """Format a PromotionReport as human-readable text."""
    lines = []
    hotfix_tag = " [HOTFIX]" if report.hotfix else ""
    lines.append(f"Promotion{hotfix_tag}: {report.from_env} -> {report.to_env}")
    lines.append(f"  Stories: {', '.join(report.stories)}")
    lines.append(f"  Bundle:  {report.bundle_branch}")
    lines.append(f"  Status:  {report.status}")
    if report.validation_id:
        lines.append(f"  Validation ID: {report.validation_id}")
    lines.append("")

    lines.append("Steps:")
    for step in report.steps:
        icon = {"success": "OK", "warning": "WARN", "failed": "FAIL",
                "skipped": "SKIP", "pending": "PEND"}.get(step.status, step.status)
        lines.append(f"  [{icon}] {step.step}")
        if step.message:
            lines.append(f"         {step.message}")

    if report.mr_url:
        lines.append("")
        lines.append(f"MR: {report.mr_url}")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_promotion_path(args.from_env, args.to_env, args.hotfix)

    report = orchestrate(args)

    if args.format == "json":
        print(json.dumps(asdict(report), indent=2))
    else:
        print(format_text(report))

    status_codes = {
        "ready_for_review": 0,
        "conflicts_pending": 1,
        "validation_failed": 2,
        "failed": 2,
    }
    return status_codes.get(report.status, 1)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
