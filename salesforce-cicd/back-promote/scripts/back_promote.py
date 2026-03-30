#!/usr/bin/env python3
"""Generate back-promotion merge request specifications.

Determines which branches need back-promotion based on where a deployment
happened, and outputs MR specifications for the agent to create via GitLab MCP.

Environment topology (high -> low):
    main -> uat -> qa -> dev1

Usage:
    python3 back_promote.py --deployed-env main --format json
    python3 back_promote.py --deployed-env uat --format text
    python3 back_promote.py --deployed-env main --target-env qa --format json
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone

# Ordered from highest to lowest environment
ENV_CHAIN = ["main", "uat", "qa", "dev1"]

# Map environment names to their branch names (they happen to match here,
# but this mapping allows for future divergence)
ENV_TO_BRANCH = {
    "main": "main",
    "uat": "uat",
    "qa": "qa",
    "dev1": "dev1",
}

VALID_DEPLOY_ENVS = {"main", "uat", "qa"}


def detect_tool(tool_name: str) -> bool:
    """Detect whether a CLI tool is available on the system PATH."""
    return shutil.which(tool_name) is not None


def build_mr_specs(deployed_env: str, target_env: str | None = None) -> list[dict]:
    """Build a list of MR specifications for the back-promote chain.

    Args:
        deployed_env: The environment where the deployment happened.
        target_env: Optional. Stop the chain at this environment (inclusive).
                    If None, back-promote all the way down to dev1.

    Returns:
        List of MR specification dicts.
    """
    if deployed_env not in VALID_DEPLOY_ENVS:
        return []

    start_idx = ENV_CHAIN.index(deployed_env)

    if target_env:
        if target_env not in ENV_CHAIN:
            return []
        end_idx = ENV_CHAIN.index(target_env)
        if end_idx <= start_idx:
            return []
    else:
        end_idx = len(ENV_CHAIN) - 1

    sgd_available = detect_tool("sf") and detect_tool("git")
    mr_specs = []
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for i in range(start_idx, end_idx):
        source = ENV_CHAIN[i]
        target = ENV_CHAIN[i + 1]
        source_branch = ENV_TO_BRANCH[source]
        target_branch = ENV_TO_BRANCH[target]

        sgd_commands = []
        if sgd_available:
            sgd_commands.append(
                f"sf sgd source delta --from origin/{target_branch} --to origin/{source_branch} --output-dir delta/ --generate-delta"
            )

        mr_spec = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "sgd_commands": sgd_commands,
            "title": f"Back-promote: {source_branch} -> {target_branch}",
            "description": (
                f"## Back-Promotion\n\n"
                f"**Source:** `{source_branch}` (deployed to {deployed_env})\n"
                f"**Target:** `{target_branch}`\n"
                f"**Date:** {timestamp}\n\n"
                f"This MR keeps `{target_branch}` in sync with `{source_branch}` "
                f"after a successful deployment to **{deployed_env}**.\n\n"
                f"### Conflict Resolution\n\n"
                f"- Profiles, permission sets, layouts, labels: accept source branch version\n"
                f"- Apex, LWC, flows, custom objects: flag for manual review\n\n"
                f"### Checklist\n\n"
                f"- [ ] All safe metadata conflicts auto-resolved\n"
                f"- [ ] Code conflicts assigned to original developer\n"
                f"- [ ] Pipeline passes on target branch\n"
                f"- [ ] Audit log entry created"
            ),
            "order": i - start_idx + 1,
            "remove_source_branch": False,
            "squash": False,
        }
        mr_specs.append(mr_spec)

    return mr_specs


def format_text(mr_specs: list[dict], deployed_env: str) -> str:
    """Format MR specs as human-readable text."""
    if not mr_specs:
        return f"No back-promotion needed for deployed environment: {deployed_env}"

    lines = [
        f"Back-Promotion Plan",
        f"===================",
        f"Deployed environment: {deployed_env}",
        f"MRs to create: {len(mr_specs)}",
        "",
    ]

    for spec in mr_specs:
        lines.extend([
            f"--- MR {spec['order']} ---",
            f"  Title:  {spec['title']}",
            f"  Source: {spec['source_branch']}",
            f"  Target: {spec['target_branch']}",
            "",
        ])

    lines.append(
        "Execute MRs in order. Wait for each MR to merge before creating the next."
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate back-promotion MR specifications for GitLab MCP.",
        epilog="Example: python3 back_promote.py --deployed-env main --format json",
    )
    parser.add_argument(
        "--deployed-env",
        required=True,
        choices=sorted(VALID_DEPLOY_ENVS),
        help="The environment where the deployment happened (main, uat, qa).",
    )
    parser.add_argument(
        "--target-env",
        choices=ENV_CHAIN,
        default=None,
        help=(
            "Optional. Stop back-promotion at this environment (inclusive). "
            "Must be lower than --deployed-env. Default: back-promote all the way to dev1."
        ),
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text).",
    )

    args = parser.parse_args()

    # Validate target-env is lower than deployed-env
    if args.target_env:
        deployed_idx = ENV_CHAIN.index(args.deployed_env)
        target_idx = ENV_CHAIN.index(args.target_env)
        if target_idx <= deployed_idx:
            print(
                f"Error: --target-env ({args.target_env}) must be a lower environment "
                f"than --deployed-env ({args.deployed_env}).",
                file=sys.stderr,
            )
            print(
                f"Environment order (high to low): {' -> '.join(ENV_CHAIN)}",
                file=sys.stderr,
            )
            return 2

    mr_specs = build_mr_specs(args.deployed_env, args.target_env)

    sgd_available = detect_tool("sf") and detect_tool("git")

    if args.format == "json":
        output = {
            "deployed_env": args.deployed_env,
            "target_env": args.target_env or ENV_CHAIN[-1],
            "sgd_available": sgd_available,
            "mr_count": len(mr_specs),
            "mr_specs": mr_specs,
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_text(mr_specs, args.deployed_env))

    return 0 if mr_specs else 1


if __name__ == "__main__":
    sys.exit(main())
