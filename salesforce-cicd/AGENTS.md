# Salesforce CI/CD Pipeline — Codex Agent Guide

This plugin provides a complete Salesforce CI/CD pipeline replacing Copado with GitLab MCP-based promotions, HIPAA-compliant audit trails, OmniStudio sequencing, and Health Cloud support.

## Skills

| Skill | Script(s) | Purpose |
|-------|-----------|---------|
| validate | `validate/scripts/validate_deployment.py`, `validate/scripts/parse_test_results.py` | Validate deployment packages against target orgs with Apex tests |
| promote | `promote/scripts/create_bundle.py`, `promote/scripts/promotion_orchestrator.py` | Create bundles and orchestrate promotions via GitLab MR |
| deploy | `deploy/scripts/deploy_package.py` | Deploy validated packages, supports quick-deploy |
| back-promote | `back-promote/scripts/back_promote.py` | Merge higher environments back to lower branches |
| profile-clean | `profile-clean/scripts/strip_profiles.py` | Strip profile/permission set references not in deployment package |
| audit-log | `audit-log/scripts/audit_logger.py` | Log HIPAA-compliant pipeline audit trail entries |
| ccb-submit | `ccb-submit/scripts/servicenow_submit.py` | Submit ServiceNow CCB change requests for production deployments |

## Environment Topology

| Branch | Org Alias | Purpose |
|--------|-----------|---------|
| `main` | production | Production |
| `uat` | sf-corehc-uat | UAT sandbox |
| `qa` | sf-corehc-qa | QA sandbox |
| `dev1` | sf-corehc-dev1 | Development sandbox |

## OmniStudio Deployment Order

OmniStudio components must deploy in this sequence:
1. DataRaptors
2. Integration Procedures
3. OmniScripts
4. FlexCards

See `references/omnistudio-sequencing.md` for details.

## External Tools

Scripts detect these tools at runtime and use them when available:

| Tool | Install | Used By |
|------|---------|---------|
| sfdx-git-delta | `sf plugins install sfdx-git-delta` | promote, back-promote |
| sf-decomposer | `sf plugins install sf-decomposer` | profile-clean |
| @jayree/manifest | `sf plugins install @jayree/sfdx-plugin-manifest` | promote |
| vlocity_build | `npm install -g vlocity` | validate, deploy |
| force-md | Go binary from GitHub | profile-clean |
| sfdx-hardis | `sf plugins install sfdx-hardis` | meta-analyst, pipeline-ops |

## HIPAA Compliance

All pipeline actions must be logged via audit-log. Audit entries must:
- Never contain PHI (use Jira story keys only)
- Include who, what, when, where, outcome
- Be retained for minimum 6 years
- Be stored as JSON-lines in `pipeline-audit/`

## Script Conventions

All Python scripts:
- Use standard library only (no external dependencies)
- Support `--help` for usage info
- Support `--format json|text` for output format
- Return exit codes: 0 (success), 1 (failure), 2 (warning)
