---
name: "ccb-submit"
description: "Use when preparing and submitting a ServiceNow Change Control Board (CCB) change request for production Salesforce deployments. Generates structured change request payloads with risk assessment and rollback plans."
---

# CCB Submit

**Tier:** POWERFUL
**Category:** Engineering
**Domain:** Salesforce DevOps / Change Management

## Overview

The CCB Submit skill prepares and submits ServiceNow Change Control Board change requests for production deployments. Every production deployment requires an approved CCB change request. This skill generates the structured payload from pipeline context (stories, validation results, risk assessment) and either submits via ServiceNow API or outputs for manual submission.

## Prerequisites

- **ServiceNow instance** with Change Management module
- **ServiceNow API credentials** (for automated submission) or access to ServiceNow UI (for manual)
- Completed `/validate` with passing results
- Approved GitLab MR for the promotion

## Core Workflows

### Workflow 1: Generate Change Request Payload

Generate the CCB payload without submitting (for manual submission or review).

```bash
python3 salesforce-cicd/ccb-submit/scripts/servicenow_submit.py \
  --change-type standard \
  --description "Deploy US-1234, US-1235 to production" \
  --risk-level low \
  --deployment-window "2026-04-01 06:00-08:00 UTC" \
  --rollback-plan "Quick-deploy previous validation ID 0Af3t00000XXXXXX" \
  --format json
```

### Workflow 2: Submit via API

Submit directly to ServiceNow (requires `--api-url` and `SERVICENOW_TOKEN` env var).

```bash
SERVICENOW_TOKEN=xxx python3 salesforce-cicd/ccb-submit/scripts/servicenow_submit.py \
  --change-type standard \
  --description "Deploy US-1234 to production" \
  --risk-level low \
  --deployment-window "2026-04-01 06:00-08:00 UTC" \
  --rollback-plan "Quick-deploy validation ID 0Af3t00000XXXXXX" \
  --api-url "https://instance.service-now.com/api/now/table/change_request" \
  --format json
```

### Workflow 3: Emergency Change

For P0/P1 hotfixes that need expedited approval.

```bash
python3 salesforce-cicd/ccb-submit/scripts/servicenow_submit.py \
  --change-type emergency \
  --description "Hotfix: Critical auth bypass in patient portal" \
  --risk-level high \
  --deployment-window "immediate" \
  --rollback-plan "Revert commit abc123, redeploy previous bundle" \
  --format json
```

## Change Types

| Type | When to Use | Approval Flow |
|------|-------------|--------------|
| `standard` | Planned releases with adequate lead time | Normal CAB review |
| `normal` | Changes requiring CAB discussion | Full CAB review |
| `emergency` | P0/P1 hotfixes requiring immediate deployment | Post-implementation review |

## Risk Assessment

| Risk Level | Criteria | Examples |
|-----------|----------|---------|
| `low` | Metadata-only, no Apex changes, tested in UAT | Profile updates, layout changes |
| `medium` | Apex changes with full test coverage, OmniStudio updates | New triggers, LWC components |
| `high` | Schema changes, integration changes, data migrations | New custom objects, API changes |
| `critical` | Production data manipulation, security changes | Permission changes, PHI field access |

## Scripts

### servicenow_submit.py

Constructs ServiceNow change request payload and optionally submits via REST API.

```bash
python3 salesforce-cicd/ccb-submit/scripts/servicenow_submit.py --help
```

## Anti-Patterns

- **Never deploy to production without an approved CCB** — Even hotfixes need post-implementation review
- **Never understate risk level** — Accurate risk assessment protects the team
- **Never omit rollback plan** — Every change request must have a tested rollback
