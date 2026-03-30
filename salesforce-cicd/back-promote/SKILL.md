---
name: "back-promote"
description: "Create merge requests from higher environments back to lower environments to keep branches in sync. After a production or UAT deploy, automatically generates MRs along the path main->uat->qa->dev1 via GitLab MCP."
---

# Back-Promote

**Tier:** POWERFUL
**Category:** Engineering
**Domain:** Salesforce DevOps

## Overview

Back-promotion keeps lower environment branches in sync after a deployment to a higher environment. When code is deployed to production, any release-time changes (hotfixes, conflict resolutions, profile tweaks) must flow back down to UAT, QA, and dev1 -- otherwise those environments drift and future promotions produce avoidable merge conflicts.

The back-promote skill generates a chain of merge request specifications that the agent creates via GitLab MCP. It does NOT execute git commands directly; it produces the MR plan and the agent acts on it.

## Prerequisites

- **GitLab MCP** configured for the project repository
- **Git** branches following the environment topology (`main`, `uat`, `qa`, `dev1`)
- **Audit log** skill available (all back-promotes are logged)
- **sfdx-git-delta (optional)** — Generates destructiveChanges.xml for removed metadata

## Core Workflows

### Workflow 1: Post-Production Back-Promote

After a successful deploy to production, back-promote through the full chain.

```bash
python3 salesforce-cicd/back-promote/scripts/back_promote.py \
  --deployed-env main \
  --format json
```

**Generated MR chain:**
1. `main` -> `uat` (MR title: "Back-promote: main -> uat")
2. `uat` -> `qa` (MR title: "Back-promote: uat -> qa")
3. `qa` -> `dev1` (MR title: "Back-promote: qa -> dev1")

Each MR is created sequentially. The agent waits for each MR to be merged before creating the next one in the chain.

### Workflow 2: Post-UAT Back-Promote

After a successful deploy to UAT, back-promote only the environments below UAT.

```bash
python3 salesforce-cicd/back-promote/scripts/back_promote.py \
  --deployed-env uat \
  --format json
```

**Generated MR chain:**
1. `uat` -> `qa` (MR title: "Back-promote: uat -> qa")
2. `qa` -> `dev1` (MR title: "Back-promote: qa -> dev1")

### Workflow 3: Selective Back-Promote

Back-promote to a specific target only (skip intermediate environments). Use when you know only one branch is out of sync.

```bash
python3 salesforce-cicd/back-promote/scripts/back_promote.py \
  --deployed-env main \
  --target-env qa \
  --format json
```

**Generated MR chain:**
1. `main` -> `uat` (MR title: "Back-promote: main -> uat")
2. `uat` -> `qa` (MR title: "Back-promote: uat -> qa")

The chain stops at the specified target environment.

### Workflow 4: Text Output

Human-readable output for review before executing.

```bash
python3 salesforce-cicd/back-promote/scripts/back_promote.py \
  --deployed-env main \
  --format text
```

### Workflow: Delta Back-Promotion with SGD
Use SGD to identify exactly what changed between environments and generate both package.xml and destructiveChanges.xml for back-promotion:
```bash
# Generate delta for back-promote: main -> uat
sf sgd source delta --from origin/uat --to origin/main --output-dir delta/ --generate-delta

# Clean manifest if @jayree available
sf jayree manifest cleanup --file delta/package/package.xml
```

## Conflict Resolution

Back-promote MRs frequently encounter merge conflicts. Apply these rules in order:

### Auto-Resolve (Safe Metadata)

The following metadata types can be auto-resolved by accepting the higher-environment version (source branch wins):

- **Profiles** (.profile-meta.xml) -- higher env always has the superset of permissions
- **Permission Sets** (.permissionset-meta.xml) -- same reasoning
- **Page Layouts** (.layout-meta.xml) -- higher env layout reflects latest requirements
- **Custom Labels** (.labels-meta.xml) -- higher env has latest translations
- **package.xml** -- regenerate from source branch contents

### Flag for Manual Review

These conflict types require human review:

- **Apex classes/triggers** -- logic conflicts must be reviewed by the developer
- **LWC/Aura components** -- UI changes may have environment-specific behavior
- **Flows** -- flow version conflicts can break automation
- **Custom Objects/Fields** -- schema changes need careful review
- **Integration Procedures / OmniScripts** -- OmniStudio conflicts need sequencing review

### Resolution Process

1. Agent creates the MR via GitLab MCP
2. If GitLab reports merge conflicts, agent checks each conflicted file against the rules above
3. Safe metadata conflicts: agent resolves by accepting source branch version
4. Code conflicts: agent adds a comment to the MR listing conflicted files and assigns the original developer
5. Log the conflict to audit trail via `/audit-log`

## Anti-Patterns

- **Skipping back-promotion** -- causes environment drift; every deploy must trigger a back-promote
- **Cherry-picking instead of merging** -- creates phantom conflicts on the next back-promote
- **Delaying back-promotion** -- the longer you wait, the more conflicts accumulate; back-promote immediately after deploy
- **Back-promoting before deploy verification** -- only back-promote after confirming the deploy succeeded in the target org
- **Manual branch merges without MR** -- bypasses GitLab audit trail and review process
