---
name: "audit-log"
description: "HIPAA-compliant structured audit trail for all pipeline actions. Logs who did what, when, where, and the outcome to a JSON-lines file. Supports querying, filtering, and compliance reporting."
---

# Audit Log

**Tier:** POWERFUL
**Category:** Engineering
**Domain:** Salesforce DevOps

## Overview

The Audit Log skill provides a HIPAA-compliant structured audit trail for every action in the Salesforce CI/CD pipeline. Every promotion, validation, deployment, back-promotion, and CCB submission is logged with a consistent schema. The audit trail supports querying, filtering, and compliance report generation.

All entries are stored as JSON-lines (one JSON object per line) in the `pipeline-audit/` directory. This format enables simple append operations, easy parsing, and compatibility with log aggregation tools.

## Prerequisites

- **Python 3.9+** (standard library only)
- **Git** (for automatic user detection via `git config user.email`)
- Write access to the `pipeline-audit/` directory (created automatically)

## Core Workflows

### Workflow 1: Log an Action

Record a pipeline action to the audit trail.

```bash
python3 salesforce-cicd/audit-log/scripts/audit_logger.py \
  --action promote \
  --user jane.doe@company.com \
  --environment qa \
  --status success \
  --details '{"stories": ["US-1234", "US-1235"], "bundle": "B042"}' \
  --format json
```

**Output:** The logged entry as JSON, confirming it was written.

### Workflow 2: Query Audit History

Search the audit trail with filters.

```bash
# Find all promotions to QA
python3 salesforce-cicd/audit-log/scripts/audit_logger.py \
  --query action=promote \
  --query environment=qa \
  --format json

# Find all failed actions
python3 salesforce-cicd/audit-log/scripts/audit_logger.py \
  --query status=failed \
  --format text

# Find actions by a specific user
python3 salesforce-cicd/audit-log/scripts/audit_logger.py \
  --query user=jane.doe@company.com \
  --format json
```

### Workflow 3: Generate Compliance Report

Query all actions within a date range for compliance review.

```bash
python3 salesforce-cicd/audit-log/scripts/audit_logger.py \
  --query action=deploy \
  --query status=success \
  --format text
```

### Workflow 4: Custom Output Directory

Store audit entries in a different location.

```bash
python3 salesforce-cicd/audit-log/scripts/audit_logger.py \
  --action validate \
  --environment uat \
  --status success \
  --output-dir /path/to/shared/audit \
  --format json
```

## Audit Entry Schema

Every audit entry contains these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string | auto | ISO 8601 UTC timestamp (e.g., `2026-03-30T14:22:00Z`) |
| `user` | string | yes | Email of the person who triggered the action |
| `action` | string | yes | Action type: `promote`, `validate`, `deploy`, `back-promote`, `profile-clean`, `ccb-submit` |
| `environment` | string | yes | Target environment: `dev1`, `qa`, `uat`, `main` |
| `status` | string | yes | Action outcome: `initiated`, `success`, `failed` |
| `details` | object | no | Freeform JSON with action-specific context |

### Example Entry

```json
{
  "timestamp": "2026-03-30T14:22:00Z",
  "user": "jane.doe@company.com",
  "action": "promote",
  "environment": "qa",
  "status": "success",
  "details": {
    "stories": ["US-1234", "US-1235"],
    "bundle": "B042",
    "mr_url": "https://gitlab.com/project/-/merge_requests/187"
  }
}
```

## HIPAA Compliance

### No PHI in Audit Entries

Audit entries must **never** contain Protected Health Information (PHI). Follow these rules:

- **Use Jira story keys only** (e.g., `US-1234`), never patient data or record IDs
- **No org record IDs** that could link to patient records
- **No query results** from Salesforce Health Cloud
- **No SOQL snippets** that reference health objects
- **Environment names and branch names** are safe to log
- **File paths and metadata type names** are safe to log

### Retention Policy

- **Minimum retention:** 6 years from creation date (HIPAA requirement)
- **Storage:** JSON-lines files in `pipeline-audit/` directory
- **Backup:** Audit files must be included in repository backups
- **Deletion:** Audit entries must never be manually deleted; use archival process instead
- **Access:** Audit files should be readable by the compliance team

### Compliance Review

- Monthly: Spot-check 10% of entries for PHI violations
- Quarterly: Full audit trail review with compliance officer
- Annually: Retention policy review and archival of entries older than 6 years

## Output Format

### JSON Format (--format json)

When logging: returns the created entry as a JSON object.
When querying: returns a JSON object with `count` and `entries` array.

### Text Format (--format text)

When logging: returns a human-readable confirmation line.
When querying: returns a formatted table of matching entries.

## Anti-Patterns

- **Logging PHI** -- never include patient data, record IDs, or health information
- **Skipping audit logging** -- every pipeline action must be logged, even failures
- **Editing audit entries** -- audit trail is append-only; corrections are logged as new entries
- **Storing audit files outside the repository** -- audit files must be in `pipeline-audit/` for version control and backup
- **Using audit log for debugging** -- audit entries track pipeline actions, not application errors; use separate logging for debug data
