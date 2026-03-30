---
name: "promote"
description: "Use when promoting Salesforce metadata from one environment to the next. Orchestrates bundle creation, feature merging, conflict resolution, profile cleaning, validation, and merge request creation via GitLab MCP. Replaces Copado promotions."
---

# Promote

**Tier:** POWERFUL
**Category:** Engineering
**Domain:** Salesforce DevOps

## Overview

The Promote skill is the primary orchestrator for the Salesforce CI/CD pipeline. It replaces Copado's promotion workflow with a transparent, agent-driven process. A single `/promote` invocation creates a deployment bundle, merges feature branches, resolves conflicts, cleans profiles, validates against the target org, and creates a GitLab merge request for review.

## Prerequisites

- **Salesforce CLI (sf)** authenticated to target orgs
- **GitLab MCP** configured for the project repository
- **SalesforceDX MCP** configured for target org
- **Git** with access to push branches
- **sfdx-git-delta (optional)** — `sf plugins install sfdx-git-delta` — Generates delta package.xml from git diff
- **@jayree/sfdx-plugin-manifest (optional)** — `sf plugins install @jayree/sfdx-plugin-manifest` — Manifest cleanup

## Core Workflows

### Workflow 1: Standard Promotion (Dev -> QA)

Promote one or more user stories from dev1 to QA.

```bash
python3 salesforce-cicd/promote/scripts/promotion_orchestrator.py \
  --stories US-1234,US-1235 \
  --from-env dev1 \
  --to-env qa \
  --format json
```

**Orchestration steps:**
1. Create `bundle/B{next_id}` branch from target env branch (`qa`)
2. Merge each `feature/US-XXXXX` branch into the bundle
3. Auto-resolve safe conflicts (profiles, permsets, layouts)
4. Flag code conflicts for manual review
5. Run `/profile-clean` on the bundle
6. Generate `package.xml` manifest
7. Run `/validate` against target org
8. Create GitLab MR via MCP (bundle -> target env branch)
9. Post results to Jira stories

### Workflow 2: Hotfix Promotion

Fast-track a critical fix directly to a higher environment.

```bash
python3 salesforce-cicd/promote/scripts/promotion_orchestrator.py \
  --stories US-9999 \
  --from-env dev1 \
  --to-env uat \
  --hotfix \
  --format json
```

**Differences from standard:**
- Skips intermediate environments
- Uses `RunSpecifiedTests` instead of `RunLocalTests`
- MR marked as urgent with hotfix label
- Requires explicit approval even if all checks pass

### Workflow 3: Multi-Story Bundle

Group multiple stories into a single promotion bundle.

```bash
python3 salesforce-cicd/promote/scripts/create_bundle.py \
  --stories US-1234,US-1235,US-1236 \
  --target-env qa \
  --format json
```

### Workflow 5: Delta Promotion with SGD

When sfdx-git-delta is installed, generate the deployment manifest automatically from the git diff between the bundle and target branch instead of using a manually-curated package.xml.

```bash
# Generate delta package from bundle branch
sf sgd source delta \
  --from origin/qa \
  --to bundle/B0042 \
  --output-dir delta/ \
  --generate-delta

# Clean up the manifest (if @jayree/sfdx-plugin-manifest installed)
sf jayree manifest cleanup --file delta/package/package.xml

# Validate using the delta manifest
python3 salesforce-cicd/validate/scripts/validate_deployment.py \
  --target-org qa --manifest delta/package/package.xml --format json
```

## Promotion Path

```
dev1 -> qa -> uat -> main (production)
```

| From | To | Branch Created | MR Target |
|------|-----|---------------|-----------|
| dev1 | qa | `bundle/B{id}` | `qa` |
| qa | uat | `bundle/B{id}` | `uat` |
| uat | main | `bundle/B{id}` | `main` |

## Bundle Naming Convention

Bundles replace Copado's `promotion/PXXXXX` branches:

- Format: `bundle/B{sequential_id}`
- Example: `bundle/B0042`
- Contains: merged features + cleaned profiles + generated manifest

## Conflict Resolution Rules

### Auto-Resolved (safe metadata)

These file types are auto-merged using union strategy:
- `.profile-meta.xml` — Union of field permissions
- `.permissionset-meta.xml` — Union of permissions
- `.layout-meta.xml` — Union of layout assignments
- `*-meta.xml` matching `.copado_exclude_autoresolve` patterns

### Manual Review Required

- `.cls` (Apex classes)
- `.trigger` (Apex triggers)
- `.js` (LWC JavaScript)
- `.html` (LWC templates)
- Any file with overlapping line changes

## Scripts

### create_bundle.py

Creates a deployment bundle branch and merges feature branches.

```bash
python3 salesforce-cicd/promote/scripts/create_bundle.py --help
```

### promotion_orchestrator.py

Orchestrates the full promotion workflow end-to-end.

```bash
python3 salesforce-cicd/promote/scripts/promotion_orchestrator.py --help
```

## Integration with Other Skills

| Step | Skill | Purpose |
|------|-------|---------|
| Profile cleaning | `/profile-clean` | Strip irrelevant metadata references |
| Validation | `/validate` | Run sf project deploy validate |
| Audit logging | `/audit-log` | Record promotion action |
| Jira updates | `@release-mgr` | Post status to Jira stories |
| Delta manifest | `sfdx-git-delta` (SGD) | Generate package.xml from git diff |
| Manifest cleanup | `@jayree/sfdx-plugin-manifest` | Remove stale entries from package.xml |

## Anti-Patterns

- **Never promote directly to production** — Always go through QA and UAT
- **Never skip validation** — Every bundle must validate before MR creation
- **Never auto-merge code conflicts** — Only metadata conflicts are safe to auto-resolve
- **Never reuse bundle branches** — Create a new bundle for each promotion
