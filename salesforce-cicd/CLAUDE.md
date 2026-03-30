# Salesforce CI/CD — Domain Guide

## Quick Reference

| Skill | Slash Command | Script(s) |
|-------|--------------|-----------|
| validate | `/validate` | `validate_deployment.py`, `parse_test_results.py` |
| promote | `/promote` | `create_bundle.py`, `promotion_orchestrator.py` |
| profile-clean | `/profile-clean` | `strip_profiles.py` |
| deploy | `/deploy` | `deploy_package.py` |
| back-promote | `/back-promote` | `back_promote.py` |
| audit-log | `/audit-log` | `audit_logger.py` |
| ccb-submit | `/ccb-submit` | `servicenow_submit.py` |

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

See [references/omnistudio-sequencing.md](references/omnistudio-sequencing.md).

## HIPAA Compliance

All pipeline actions must be logged via `/audit-log`. Audit entries must:
- Never contain PHI (use Jira story keys only)
- Include who, what, when, where, outcome
- Be retained for minimum 6 years
- Be stored as JSON-lines in `pipeline-audit/`

## External Tools

Scripts detect these tools at runtime and use them when available:

| Tool | Install | Used By |
|------|---------|---------|
| sfdx-git-delta | `sf plugins install sfdx-git-delta` | `/promote`, `/back-promote` |
| sf-decomposer | `sf plugins install sf-decomposer` | `/profile-clean` |
| @jayree/manifest | `sf plugins install @jayree/sfdx-plugin-manifest` | `/promote`, `@meta-analyst` |
| vlocity_build | `npm install -g vlocity` | `/validate`, `/deploy`, `@omnistudio-dev` |
| force-md | Go binary from GitHub | `/profile-clean` |
| sfdx-hardis | `sf plugins install sfdx-hardis` | `@meta-analyst`, `@pipeline-ops` |

See [references/open-source-tools.md](references/open-source-tools.md) for complete documentation.

### Tool Detection Pattern

All scripts use this pattern for graceful degradation:

```python
def detect_tool(cmd_parts: list) -> bool:
    try:
        subprocess.run(cmd_parts, capture_output=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
```

## Creating New Skills

Follow the standard pattern:
```
skill-name/
├── SKILL.md              # Frontmatter (name, description) + docs
├── scripts/              # Python stdlib-only tools
└── references/           # Expert knowledge bases
```

Python scripts must support `--help`, `--format json|text`, and return exit codes 0/1/2.
