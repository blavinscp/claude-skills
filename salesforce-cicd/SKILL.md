---
name: "salesforce-cicd-pipeline"
description: "Use when the user needs to validate, promote, deploy, or manage Salesforce metadata across environments. Provides a complete CI/CD pipeline replacing Copado with agent-orchestrated promotions, GitLab MCP integration, HIPAA audit trails, and OmniStudio sequencing."
---

# Salesforce CI/CD Pipeline

**Tier:** POWERFUL
**Category:** Engineering
**Domain:** Salesforce DevOps & Release Management

## Overview

The Salesforce CI/CD Pipeline skill suite provides a complete replacement for Copado-based CI/CD workflows. It orchestrates metadata promotions across Dev1 -> QA -> UAT -> Production using Claude Code agents, GitLab MCP for merge request management, and Salesforce CLI for deployments. Every pipeline action is logged for HIPAA compliance.

**Core principle:** Agents orchestrate, humans approve, SF CLI executes.

## Skills Included

| Skill | Priority | Description |
|-------|----------|-------------|
| [validate](validate/SKILL.md) | P0 | Run `sf project deploy validate` with Apex tests and structured results |
| [promote](promote/SKILL.md) | P0 | Orchestrate promotions: bundle creation, merge, validate, MR via GitLab MCP |
| [profile-clean](profile-clean/SKILL.md) | P1 | Strip profile/permset references not in deployment package |
| [deploy](deploy/SKILL.md) | P1 | User-initiated deployment with quick-deploy support |
| [back-promote](back-promote/SKILL.md) | P1 | Create MRs from higher to lower environments to keep branches in sync |
| [audit-log](audit-log/SKILL.md) | P1 | HIPAA-compliant structured audit trail for all pipeline actions |
| [ccb-submit](ccb-submit/SKILL.md) | P2 | Prepare and submit ServiceNow CCB change requests |

## Prerequisites

### Required CLI Tools

- **Salesforce CLI (sf)** — `npm install -g @salesforce/cli`
- **Python 3.8+** — For automation scripts

### Required MCP Servers

- **SalesforceDX MCP** — Org authentication, SOQL queries, metadata interaction
- **GitLab MCP** (official) — Branch ops, MR creation/merge/comment, pipeline status

### Optional MCP Servers

- **Atlassian MCP** — Jira issue CRUD, workflow transitions (for release management)

See [references/mcp-requirements.md](references/mcp-requirements.md) for configuration details.

### Recommended Open Source Tools (Optional)

These tools enhance the pipeline but are not required. Scripts detect their availability at runtime and fall back to built-in logic when not installed.

```bash
# Tier 1 — High value
sf plugins install sfdx-git-delta                              # Delta package.xml from git diff
sf plugins install sf-decomposer                               # Granular profile/permset files
sf plugins install @jayree/sfdx-plugin-manifest                # Manifest generation + cleanup
sf plugins install @salesforce/plugin-omnistudio-migration-tool # OmniStudio migration
npm install --global vlocity                                   # OmniStudio dependency-ordered deploy

# Tier 2 — Patterns & automation
sf plugins install sfdx-hardis                                 # Monitoring, backup, CI generation
# force-md: download from https://github.com/ForceCLI/force-md/releases
```

See [references/open-source-tools.md](references/open-source-tools.md) for full documentation.

## Pipeline Architecture

```
STAGE 1: DEVELOP
  Developer creates feature/US-XXXXX from dev1
  Pre-commit hooks run linting

STAGE 2: PROMOTE (replaces Copado promotion)
  /promote US-XXXXX --target qa
  -> Creates bundle/BXXXXX branch
  -> Merges feature into bundle
  -> /profile-clean strips irrelevant metadata
  -> /validate runs sf project deploy validate
  -> GitLab MCP creates MR for review

STAGE 3: REVIEW & MERGE
  Human reviews GitLab MR
  Human merges (or agent merges if all checks pass)

STAGE 4: DEPLOY (user-initiated only)
  /deploy --target <org-alias>
  Supports quick-deploy via stored validation job ID

STAGE 5: BACK-PROMOTE (automated MR creation)
  /back-promote creates MRs: main -> uat -> qa -> dev1
```

### Branching Strategy

```
main (production)
  uat (UAT sandbox)
    qa (QA sandbox)
      dev1 (Dev sandbox)
        feature/US-XXXXX (individual stories)
  bundle/B0001 (groups features for promotion)
```

## Python Scripts

All scripts follow repository conventions:
- Standard library only (no pip dependencies)
- `argparse` with `--help` support
- `--format json|text` output modes
- Exit codes: 0 (success), 1 (warning), 2 (error)

| Script | Skill | Purpose |
|--------|-------|---------|
| `validate_deployment.py` | validate | Wraps sf project deploy validate |
| `parse_test_results.py` | validate | Parses Apex test results |
| `create_bundle.py` | promote | Assembles deployment bundles |
| `promotion_orchestrator.py` | promote | Coordinates promotion workflow |
| `strip_profiles.py` | profile-clean | Strips irrelevant profile/permset refs |
| `deploy_package.py` | deploy | Wraps sf project deploy start |
| `back_promote.py` | back-promote | Generates back-promotion MR specs |
| `audit_logger.py` | audit-log | Logs and queries pipeline audit trail |
| `servicenow_submit.py` | ccb-submit | Constructs ServiceNow change request |

## Companion Agents

These agents (in `.claude/agents/`) orchestrate the skills:

| Agent | Role |
|-------|------|
| @pipeline-ops | Primary orchestrator — bundles, merges, promotions |
| @dx-ops | SF DX operations — validate, deploy, OmniStudio |
| @reviewer | Structured code review for pipeline gates |
| @meta-analyst | Metadata drift detection |
| @omnistudio-dev | OmniStudio deployment sequencing |
| @healthcloud-eng | Health Cloud compliance, HIPAA checks |
| @release-mgr | Release coordination, audit trails, CCB |
| @scrum-ops | Sprint analytics, pipeline health |

## Related Skills

- `engineering/release-manager` — Changelog generation, semantic versioning
- `engineering/ci-cd-pipeline-builder` — GitLab CI config generation
- `engineering/migration-architect` — Phased migration planning

## References

- [Open Source Tools](references/open-source-tools.md) — All 10 recommended tools with install commands
- [CI Workflow Patterns](references/ci-workflow-patterns.md) — GitHub Actions + GitLab CI patterns
- [MCP Requirements](references/mcp-requirements.md) — MCP server configuration
- [OmniStudio Sequencing](references/omnistudio-sequencing.md) — Component dependency ordering
- [Recommended Hooks](references/recommended-hooks.md) — Claude Code hook configuration
