#!/usr/bin/env python3
"""HIPAA-compliant structured audit logger for Salesforce CI/CD pipeline.

Appends structured audit entries to a JSON-lines file or queries existing
entries with filters.

Modes:
    Log mode:   Provide --action, --environment, --status to create an entry.
    Query mode: Provide --query key=value pairs to search existing entries.

Usage:
    # Log an action
    python3 audit_logger.py --action promote --environment qa --status success \\
        --user jane@co.com --details '{"stories":["US-1234"]}' --format json

    # Query entries
    python3 audit_logger.py --query action=promote --query environment=qa --format json
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_OUTPUT_DIR = "pipeline-audit"
AUDIT_FILENAME = "audit.jsonl"

VALID_ACTIONS = [
    "promote",
    "validate",
    "deploy",
    "back-promote",
    "profile-clean",
    "ccb-submit",
    "rollback",
    "hotfix",
]

VALID_STATUSES = ["initiated", "success", "failed"]

VALID_ENVIRONMENTS = ["dev1", "qa", "uat", "main"]


def get_git_user() -> str | None:
    """Attempt to get user email from git config."""
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def ensure_output_dir(output_dir: str) -> Path:
    """Create the output directory if it doesn't exist."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_entry(
    action: str,
    user: str,
    environment: str,
    status: str,
    details: dict | None = None,
) -> dict:
    """Create a structured audit entry."""
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user": user,
        "action": action,
        "environment": environment,
        "status": status,
    }
    if details:
        entry["details"] = details
    return entry


def append_entry(entry: dict, output_dir: str) -> Path:
    """Append an audit entry to the JSON-lines file."""
    dir_path = ensure_output_dir(output_dir)
    file_path = dir_path / AUDIT_FILENAME
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")
    return file_path


def read_entries(output_dir: str) -> list[dict]:
    """Read all audit entries from the JSON-lines file."""
    file_path = Path(output_dir) / AUDIT_FILENAME
    if not file_path.exists():
        return []

    entries = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                print(
                    f"Warning: skipping malformed entry on line {line_num}",
                    file=sys.stderr,
                )
    return entries


def filter_entries(entries: list[dict], filters: dict[str, str]) -> list[dict]:
    """Filter entries by key=value pairs."""
    result = []
    for entry in entries:
        match = True
        for key, value in filters.items():
            entry_value = entry.get(key)
            if entry_value is None:
                match = False
                break
            if str(entry_value) != value:
                match = False
                break
        if match:
            result.append(entry)
    return result


def parse_query_filters(query_args: list[str]) -> dict[str, str]:
    """Parse --query key=value arguments into a dict."""
    filters = {}
    for q in query_args:
        if "=" not in q:
            print(
                f"Error: query filter must be key=value format, got: {q}",
                file=sys.stderr,
            )
            sys.exit(2)
        key, value = q.split("=", 1)
        filters[key.strip()] = value.strip()
    return filters


def format_entry_text(entry: dict) -> str:
    """Format a single entry as human-readable text."""
    ts = entry.get("timestamp", "?")
    user = entry.get("user", "?")
    action = entry.get("action", "?")
    env = entry.get("environment", "?")
    status = entry.get("status", "?")
    details = entry.get("details", {})
    details_str = json.dumps(details) if details else "-"
    return f"[{ts}] {user} | {action} | {env} | {status} | {details_str}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HIPAA-compliant audit logger for Salesforce CI/CD pipeline.",
        epilog=(
            "Examples:\n"
            "  Log:   python3 audit_logger.py --action promote --environment qa "
            "--status success --format json\n"
            "  Query: python3 audit_logger.py --query action=promote "
            "--query environment=qa --format json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Log mode arguments
    parser.add_argument(
        "--action",
        choices=VALID_ACTIONS,
        help="Action type to log.",
    )
    parser.add_argument(
        "--user",
        help="User who triggered the action (default: git config user.email).",
    )
    parser.add_argument(
        "--environment",
        choices=VALID_ENVIRONMENTS,
        help="Target environment.",
    )
    parser.add_argument(
        "--status",
        choices=VALID_STATUSES,
        help="Action outcome.",
    )
    parser.add_argument(
        "--details",
        help="JSON string with action-specific details (e.g., '{\"stories\":[\"US-1234\"]}').",
    )

    # Query mode arguments
    parser.add_argument(
        "--query",
        action="append",
        help="Filter entries by key=value (repeatable). E.g., --query action=promote --query status=failed.",
    )

    # Common arguments
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for audit files (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text).",
    )

    args = parser.parse_args()

    # Determine mode
    is_log_mode = args.action is not None
    is_query_mode = args.query is not None

    if is_log_mode and is_query_mode:
        print("Error: cannot use --action and --query together.", file=sys.stderr)
        return 2

    if not is_log_mode and not is_query_mode:
        print(
            "Error: provide --action (to log) or --query (to search). "
            "Use --help for usage.",
            file=sys.stderr,
        )
        return 2

    # --- Log Mode ---
    if is_log_mode:
        if not args.environment:
            print("Error: --environment is required when logging.", file=sys.stderr)
            return 2
        if not args.status:
            print("Error: --status is required when logging.", file=sys.stderr)
            return 2

        # Resolve user
        user = args.user or get_git_user()
        if not user:
            print(
                "Error: --user is required (could not detect from git config).",
                file=sys.stderr,
            )
            return 2

        # Parse details
        details = None
        if args.details:
            try:
                details = json.loads(args.details)
                if not isinstance(details, dict):
                    print(
                        "Error: --details must be a JSON object.",
                        file=sys.stderr,
                    )
                    return 2
            except json.JSONDecodeError as e:
                print(f"Error: invalid JSON in --details: {e}", file=sys.stderr)
                return 2

        entry = create_entry(args.action, user, args.environment, args.status, details)
        file_path = append_entry(entry, args.output_dir)

        if args.format == "json":
            output = {
                "logged": True,
                "file": str(file_path),
                "entry": entry,
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"Logged: {format_entry_text(entry)}")
            print(f"  File: {file_path}")

        return 0

    # --- Query Mode ---
    if is_query_mode:
        filters = parse_query_filters(args.query)
        entries = read_entries(args.output_dir)

        if not entries:
            if args.format == "json":
                print(json.dumps({"count": 0, "entries": []}, indent=2))
            else:
                print("No audit entries found.")
            return 1

        matched = filter_entries(entries, filters)

        if args.format == "json":
            output = {
                "count": len(matched),
                "filters": filters,
                "entries": matched,
            }
            print(json.dumps(output, indent=2))
        else:
            if not matched:
                print(f"No entries match filters: {filters}")
            else:
                print(f"Audit Entries ({len(matched)} matches)")
                print("=" * 60)
                for entry in matched:
                    print(format_entry_text(entry))

        return 0 if matched else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
