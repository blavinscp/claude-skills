#!/usr/bin/env python3
"""Prepare and submit ServiceNow CCB change requests for production deployments.

Constructs a structured ServiceNow change request payload from pipeline
context and optionally submits via the ServiceNow REST API.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


class CLIError(Exception):
    """Expected CLI failures."""
    pass


CHANGE_TYPES = {
    "standard": "Standard",
    "normal": "Normal",
    "emergency": "Emergency",
}

RISK_LEVELS = {
    "low": {"impact": "3", "priority": "4", "risk": "Low"},
    "medium": {"impact": "2", "priority": "3", "risk": "Moderate"},
    "high": {"impact": "2", "priority": "2", "risk": "High"},
    "critical": {"impact": "1", "priority": "1", "risk": "Very High"},
}


@dataclass
class ChangeRequest:
    type: str = ""
    category: str = "Salesforce"
    short_description: str = ""
    description: str = ""
    risk_level: str = ""
    impact: str = ""
    priority: str = ""
    deployment_window: str = ""
    rollback_plan: str = ""
    test_plan: str = ""
    implementation_plan: str = ""
    assignment_group: str = "Salesforce DevOps"
    requested_by: str = ""
    created_at: str = ""


@dataclass
class SubmitReport:
    change_request: ChangeRequest = field(default_factory=ChangeRequest)
    payload: Dict = field(default_factory=dict)
    submitted: bool = False
    response_code: int = 0
    change_number: str = ""
    error: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and submit ServiceNow CCB change requests.",
        epilog="Examples:\n"
               "  %(prog)s --change-type standard --description 'Deploy US-1234' "
               "--risk-level low --deployment-window '2026-04-01 06:00-08:00 UTC' "
               "--rollback-plan 'Quick-deploy validation ID 0AfXXX'\n"
               "\n"
               "  %(prog)s --change-type emergency --description 'Hotfix: auth bypass' "
               "--risk-level high --deployment-window immediate "
               "--rollback-plan 'Revert commit abc123' "
               "--api-url https://instance.service-now.com/api/now/table/change_request\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--change-type",
        required=True,
        choices=list(CHANGE_TYPES.keys()),
        help="Type of change request",
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Description of the change",
    )
    parser.add_argument(
        "--risk-level",
        required=True,
        choices=list(RISK_LEVELS.keys()),
        help="Risk level assessment",
    )
    parser.add_argument(
        "--deployment-window",
        required=True,
        help="Planned deployment window (e.g., '2026-04-01 06:00-08:00 UTC' or 'immediate')",
    )
    parser.add_argument(
        "--rollback-plan",
        required=True,
        help="Rollback plan if deployment fails",
    )
    parser.add_argument("--test-plan", default="", help="Test plan for the change")
    parser.add_argument("--implementation-plan", default="", help="Implementation steps")
    parser.add_argument("--stories", default="", help="Comma-separated Jira story keys")
    parser.add_argument("--validation-id", default="", help="SF validation job ID")
    parser.add_argument("--bundle", default="", help="Bundle branch name")
    parser.add_argument("--requested-by", default="", help="Name of requestor")
    parser.add_argument(
        "--assignment-group",
        default="Salesforce DevOps",
        help="ServiceNow assignment group",
    )
    parser.add_argument(
        "--api-url",
        help="ServiceNow REST API URL (submits if provided). "
             "Requires SERVICENOW_TOKEN env var.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    return parser.parse_args()


def build_change_request(args: argparse.Namespace) -> ChangeRequest:
    """Build a ChangeRequest from CLI arguments."""
    risk_info = RISK_LEVELS[args.risk_level]

    # Build detailed description
    description_parts = [args.description]
    if args.stories:
        description_parts.append(f"\nJira Stories: {args.stories}")
    if args.validation_id:
        description_parts.append(f"Validation ID: {args.validation_id}")
    if args.bundle:
        description_parts.append(f"Bundle: {args.bundle}")

    # Build implementation plan
    impl_plan = args.implementation_plan
    if not impl_plan:
        impl_plan = (
            "1. Verify CCB approval\n"
            "2. Confirm deployment window with stakeholders\n"
            "3. Run /deploy --target production\n"
            "4. Verify deployment success\n"
            "5. Run smoke tests\n"
            "6. Run /back-promote to sync lower environments\n"
            "7. Update Jira stories to Done\n"
            "8. Log deployment via /audit-log"
        )

    # Build test plan
    test_plan = args.test_plan
    if not test_plan:
        test_plan = (
            "1. Apex tests passed via /validate (RunLocalTests)\n"
            "2. UAT sign-off completed\n"
            "3. OmniStudio components verified in UAT\n"
            "4. Post-deploy smoke tests planned"
        )

    return ChangeRequest(
        type=CHANGE_TYPES[args.change_type],
        short_description=args.description[:160],
        description="\n".join(description_parts),
        risk_level=risk_info["risk"],
        impact=risk_info["impact"],
        priority=risk_info["priority"],
        deployment_window=args.deployment_window,
        rollback_plan=args.rollback_plan,
        test_plan=test_plan,
        implementation_plan=impl_plan,
        assignment_group=args.assignment_group,
        requested_by=args.requested_by,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def build_servicenow_payload(cr: ChangeRequest) -> Dict:
    """Convert a ChangeRequest to ServiceNow REST API payload."""
    return {
        "type": cr.type,
        "category": cr.category,
        "short_description": cr.short_description,
        "description": cr.description,
        "risk": cr.risk_level,
        "impact": cr.impact,
        "priority": cr.priority,
        "start_date": cr.deployment_window,
        "backout_plan": cr.rollback_plan,
        "test_plan": cr.test_plan,
        "implementation_plan": cr.implementation_plan,
        "assignment_group": cr.assignment_group,
        "requested_by": cr.requested_by,
    }


def submit_to_servicenow(api_url: str, payload: Dict) -> Dict:
    """Submit change request to ServiceNow REST API."""
    token = os.environ.get("SERVICENOW_TOKEN")
    if not token:
        raise CLIError("SERVICENOW_TOKEN environment variable is required for API submission")

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {
                "status_code": resp.status,
                "body": json.loads(resp.read().decode("utf-8")),
            }
    except urllib.error.HTTPError as e:
        return {
            "status_code": e.code,
            "body": {"error": e.read().decode("utf-8")},
        }
    except urllib.error.URLError as e:
        raise CLIError(f"Failed to connect to ServiceNow: {e.reason}")


def format_text(report: SubmitReport) -> str:
    """Format a SubmitReport as human-readable text."""
    cr = report.change_request
    lines = []
    lines.append(f"Change Request: {cr.type}")
    lines.append(f"  Description:  {cr.short_description}")
    lines.append(f"  Risk Level:   {cr.risk_level}")
    lines.append(f"  Impact:       {cr.impact}")
    lines.append(f"  Priority:     {cr.priority}")
    lines.append(f"  Window:       {cr.deployment_window}")
    lines.append(f"  Assignment:   {cr.assignment_group}")
    lines.append("")
    lines.append(f"Rollback Plan:")
    lines.append(f"  {cr.rollback_plan}")
    lines.append("")
    lines.append(f"Implementation Plan:")
    for line in cr.implementation_plan.split("\n"):
        lines.append(f"  {line}")
    lines.append("")
    lines.append(f"Test Plan:")
    for line in cr.test_plan.split("\n"):
        lines.append(f"  {line}")

    if report.submitted:
        lines.append("")
        if report.change_number:
            lines.append(f"Submitted: {report.change_number} (HTTP {report.response_code})")
        elif report.error:
            lines.append(f"Submission Failed: {report.error}")
    else:
        lines.append("")
        lines.append("Not submitted. Use --api-url to submit to ServiceNow.")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    cr = build_change_request(args)
    payload = build_servicenow_payload(cr)

    report = SubmitReport(
        change_request=cr,
        payload=payload,
    )

    # Submit if API URL provided
    if args.api_url:
        response = submit_to_servicenow(args.api_url, payload)
        report.submitted = True
        report.response_code = response["status_code"]
        if response["status_code"] in (200, 201):
            result = response["body"].get("result", {})
            report.change_number = result.get("number", "")
        else:
            report.error = str(response["body"].get("error", "Unknown error"))

    if args.format == "json":
        print(json.dumps(asdict(report), indent=2))
    else:
        print(format_text(report))

    if report.submitted and report.error:
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
