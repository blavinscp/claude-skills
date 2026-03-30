# Copado to Agentic Pipeline Migration Mapping

## Concept Mapping

| Copado Concept | New Pipeline Equivalent | Notes |
|---------------|------------------------|-------|
| Promotion | `/promote` skill | Single command replaces Copado UI |
| Promotion branch (`promotion/PXXXXX`) | Bundle branch (`bundle/BXXXXX`) | Same purpose, clearer naming |
| Back Promotion | `/back-promote` skill | Automated MR creation via GitLab MCP |
| Deployment | `/deploy` skill | User-initiated, supports quick-deploy |
| Validate | `/validate` skill | Wraps `sf project deploy validate` |
| User Story (commit) | Feature branch (`feature/US-XXXXX`) | Same pattern, no change |
| Copado Quality Gate | `/promote-ready` + `/validate` | Existing + new skills combined |
| Copado Conflict Resolution | Auto-resolve in `create_bundle.py` | Profiles/permsets auto-merged |
| Cleaned Full Profile | `/profile-clean` skill | Same functionality, transparent |
| Copado Test | Apex test execution in `/validate` | sf CLI handles tests directly |

## Workflow Comparison

### Copado Promotion Flow

```
1. Create User Story in Copado
2. Commit changes (Copado Git Snapshot)
3. Create Promotion (Copado UI)
4. Copado creates promotion/PXXXXX branch
5. Copado resolves conflicts (black box)
6. Copado cleans profiles (black box)
7. Copado validates deployment
8. Review and merge in Copado
9. Copado deploys to target
```

### New Agentic Flow

```
1. Create feature/US-XXXXX branch from dev1
2. Develop and commit changes
3. Invoke: /promote US-XXXXX --target qa
4. Agent creates bundle/BXXXXX branch (visible in git)
5. Agent resolves conflicts (transparent rules in create_bundle.py)
6. /profile-clean strips metadata (auditable)
7. /validate runs sf project deploy validate (full CLI output)
8. GitLab MR created for review (standard code review)
9. /deploy deploys to target (user-initiated)
```

## Key Differences

| Aspect | Copado | New Pipeline |
|--------|--------|-------------|
| Transparency | Black box operations | Every step visible in git + logs |
| Conflict resolution | Proprietary algorithm | Documented rules in create_bundle.py |
| Profile cleaning | Hidden step | Explicit `/profile-clean` with dry-run |
| Test execution | Copado wrapper | Direct `sf project deploy validate` |
| Audit trail | Copado's internal logs | JSON-lines in `pipeline-audit/` (HIPAA) |
| Rollback | Copado rollback feature | Quick-deploy from validated job ID |
| Cost | Copado license per user | $0 (open source tools) |

## State Tracking Migration

Copado tracks state internally. The new pipeline uses:

| State | Tracked In |
|-------|-----------|
| Story status | Jira (via Atlassian MCP) |
| Promotion status | GitLab MR labels + pipeline-audit/ |
| Deployment status | `sf project deploy report` + audit log |
| Bundle contents | Git branch history |
| Approval status | GitLab MR approvals |
| Release notes | `release-manager` plugin changelog |
