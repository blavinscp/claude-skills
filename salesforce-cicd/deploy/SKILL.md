---
name: "deploy"
description: "Use when performing a user-initiated Salesforce deployment to a target org. Supports standard manifest-based deploy, quick-deploy from a prior validation ID, and OmniStudio multi-step deployment. Never auto-triggered — always requires explicit user action."
---

# Deploy

**Tier:** POWERFUL
**Category:** Engineering
**Domain:** Salesforce DevOps

## Overview

The Deploy skill executes `sf project deploy start` (or `sf project deploy quick` for validated packages) against a target Salesforce org and returns structured results including component counts, failure details, and deployment duration.

**This skill is ALWAYS user-initiated.** It is never triggered automatically by a hook, scheduled job, or CI pipeline step. The user must explicitly request a deployment after reviewing validation results, CCB approvals, or promotion status. This is a deliberate safety control — deploying metadata to a Salesforce org is a destructive action that cannot be undone without a rollback deployment.

This replaces Copado's "Deploy" step with a transparent, scriptable process.

## Prerequisites

- **Salesforce CLI (sf)** installed and authenticated to target org
- **SalesforceDX MCP** configured for the target org
- **Successful validation** — either a passing `/validate` result or a stored validation job ID for quick-deploy
- **CCB approval** (production deployments) — see `/ccb-submit` skill

## Core Workflows

### Workflow 1: Standard Deploy from Manifest

Deploy a package.xml manifest to a target org. Runs without tests by default (tests were already executed during validation).

```bash
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org qa \
  --manifest force-app/main/default/package.xml \
  --format json
```

**Output:** JSON with deployment ID, status, component counts, failures, and duration.

### Workflow 2: Quick-Deploy from Validation ID

If a prior validation passed all tests, use the validation job ID to quick-deploy without re-running tests. This is the fastest and safest production deployment path.

```bash
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org production \
  --validation-id 0Af3t00000XXXXXX \
  --format json
```

Quick-deploy constraints:
- Validation must have completed successfully
- Validation expires after **10 days** — quick-deploy will fail after that
- No metadata changes can be made to the org between validation and quick-deploy

See [references/quick-deploy-guide.md](references/quick-deploy-guide.md) for the full workflow.

### Workflow 3: OmniStudio Multi-Step Deploy

OmniStudio components must be deployed in strict dependency order. Run separate deployments for each phase:

1. **DataRaptors** — deploy first (no dependencies)
2. **Integration Procedures** — depend on DataRaptors
3. **OmniScripts** — depend on Integration Procedures
4. **FlexCards** — depend on OmniScripts

```bash
# Phase 1: DataRaptors
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org qa \
  --manifest manifests/phase1-dataraptors.xml \
  --format json

# Phase 2: Integration Procedures
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org qa \
  --manifest manifests/phase2-integrationprocedures.xml \
  --format json

# Phase 3: OmniScripts
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org qa \
  --manifest manifests/phase3-omniscripts.xml \
  --format json

# Phase 4: FlexCards
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org qa \
  --manifest manifests/phase4-flexcards.xml \
  --format json
```

Each phase must succeed before proceeding. If a phase fails, do not continue — fix the issue and re-deploy that phase.

See [../references/omnistudio-sequencing.md](../references/omnistudio-sequencing.md) for dependency rules.

### Workflow: OmniStudio Deploy via Vlocity Build

```bash
vlocity -sfdx.username qa -job deploy.yaml packDeploy
```

Vlocity Build handles dependency ordering automatically. No need for manual phased deployment.

### Workflow 4: Dry Run

Preview the exact sf CLI command that would execute without running it.

```bash
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org production \
  --manifest package.xml \
  --dry-run
```

## Output Format

### JSON Output

```json
{
  "deployment_id": "0Af3t00000XXXXXX",
  "status": "Succeeded",
  "target_org": "qa",
  "manifest": "force-app/main/default/package.xml",
  "deploy_mode": "standard",
  "components": {
    "total": 42,
    "deployed": 42,
    "failed": 0
  },
  "failures": [],
  "duration_seconds": 87.3
}
```

### Text Output

```
Deployment: PASS
  Deploy ID:  0Af3t00000XXXXXX
  Target Org: qa
  Mode:       standard
  Manifest:   force-app/main/default/package.xml
  Duration:   87s

Components: 42/42 deployed, 0 failed
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Deployment succeeded |
| 1 | Deployment failed (non-error failure, e.g., still in progress) |
| 2 | Error (invalid arguments, CLI failure, component errors) |

## Rollback

If a deployment causes issues, see [references/rollback-procedures.md](references/rollback-procedures.md) for rollback strategies including re-deploying a prior version, destructive changes, and OmniStudio rollback procedures.

## Anti-Patterns

| Anti-Pattern | Why It Fails | Do This Instead |
|-------------|-------------|-----------------|
| Auto-deploy on merge | Deploys untested metadata to orgs | Always validate first, then deploy explicitly |
| Skip validation, deploy directly | No test coverage gate, breaks production | Run `/validate` and confirm results before `/deploy` |
| Quick-deploy after org changes | Validation is stale, may fail silently | Re-validate if any metadata was modified in the target org |
| Deploy OmniStudio in one package | Dependency failures on IP/OS/FC types | Use multi-step deploy in dependency order |
| Deploy without CCB for production | Compliance violation, audit gap | Submit `/ccb-submit` and get approval first |
| Auto-trigger deploy from CI | Removes human review gate | Keep deploy as a manual, user-initiated action |
