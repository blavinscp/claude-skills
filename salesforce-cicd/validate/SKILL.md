---
name: "validate"
description: "Use when validating a Salesforce deployment package against a target org. Runs sf project deploy validate with Apex test execution and returns structured pass/fail results with coverage metrics."
---

# Validate

**Tier:** POWERFUL
**Category:** Engineering
**Domain:** Salesforce DevOps

## Overview

The Validate skill runs `sf project deploy validate` against a target Salesforce org, executes Apex tests at the appropriate level, and returns structured results including pass/fail status, test outcomes, and code coverage metrics. It stores the validation job ID for subsequent quick-deploy via the `/deploy` skill.

This replaces Copado's "Validate Deployment" step with a transparent, scriptable process.

## Prerequisites

- **Salesforce CLI (sf)** installed and authenticated to target org
- **SalesforceDX MCP** configured for the target org
- **package.xml** manifest or source-tracked project

## Core Workflows

### Workflow 1: Standard Validation

Validate a deployment package with default test level (RunLocalTests).

```bash
python3 salesforce-cicd/validate/scripts/validate_deployment.py \
  --target-org qa \
  --manifest force-app/main/default/package.xml \
  --format json
```

**Output:** JSON with validation ID, pass/fail, test results, coverage percentage.

### Workflow 2: Specified Test Classes

Validate with specific test classes (faster for targeted changes).

```bash
python3 salesforce-cicd/validate/scripts/validate_deployment.py \
  --target-org qa \
  --manifest package.xml \
  --test-level RunSpecifiedTests \
  --tests AccountTriggerTest,ContactServiceTest \
  --format json
```

### Workflow 3: Quick-Validate (Re-use Prior Validation)

Check status of a running or completed validation.

```bash
python3 salesforce-cicd/validate/scripts/validate_deployment.py \
  --job-id 0Af3t00000XXXXXX \
  --format text
```

### Workflow 4: OmniStudio Sequential Validation

For deployments containing OmniStudio components, split into phases:

1. Validate standard metadata first
2. Validate DataRaptors
3. Validate Integration Procedures
4. Validate OmniScripts
5. Validate FlexCards

See [../references/omnistudio-sequencing.md](../references/omnistudio-sequencing.md) for dependency rules.

## Test Level Decision Matrix

| Scenario | Test Level | Why |
|----------|-----------|-----|
| QA promotion (standard metadata) | `RunLocalTests` | Covers all non-managed tests |
| QA promotion (targeted fix) | `RunSpecifiedTests` | Faster, tests only affected areas |
| UAT promotion | `RunLocalTests` | Full regression before UAT |
| Production deployment | `RunLocalTests` | Required for production |
| Hotfix (P0/P1) | `RunSpecifiedTests` | Speed critical, test affected areas only |

## Output Format

### JSON Output

```json
{
  "validation_id": "0Af3t00000XXXXXX",
  "status": "Succeeded",
  "target_org": "qa",
  "test_level": "RunLocalTests",
  "components": {
    "total": 45,
    "deployed": 45,
    "errors": 0
  },
  "tests": {
    "total": 128,
    "passing": 126,
    "failing": 2,
    "skipped": 0
  },
  "coverage": {
    "overall": 82.5,
    "classes_below_75": ["AccountHelper", "ContactUtil"]
  },
  "errors": [],
  "duration_seconds": 342
}
```

## Scripts

### validate_deployment.py

Orchestrates the validation lifecycle: initiates validation, polls for completion, parses results.

```bash
python3 salesforce-cicd/validate/scripts/validate_deployment.py --help
```

### parse_test_results.py

Parses raw Apex test result JSON into a structured summary with coverage analysis.

```bash
python3 salesforce-cicd/validate/scripts/parse_test_results.py --input test-results.json --format text
```

## Common Failure Patterns

See [references/common-validation-failures.md](references/common-validation-failures.md) for a catalog of failure patterns and resolutions.

## Anti-Patterns

- **Never skip tests for production** — Always use `RunLocalTests` minimum
- **Never validate and deploy in one step** — Always validate first, then quick-deploy
- **Never ignore coverage warnings** — Classes below 75% block production deployments
- **Never validate OmniStudio in bulk** — Always use sequential phase validation
