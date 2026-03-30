# Promotion Path Guide

## Environment Topology

```
main (production) ─── Production Salesforce Org
  │
  uat ─────────────── UAT Sandbox (full copy)
  │
  qa ──────────────── QA Sandbox (full copy)
  │
  dev1 ────────────── Dev Sandbox (developer)
    │
    feature/US-XXXXX ─ Individual story branches
```

## Branch-to-Org Mapping

| Branch | Org Alias | Sandbox Type | Purpose |
|--------|-----------|-------------|---------|
| `main` | `production` | Production | Live system |
| `uat` | `sf-corehc-uat` | Full Copy | User acceptance testing |
| `qa` | `sf-corehc-qa` | Full Copy | Quality assurance |
| `dev1` | `sf-corehc-dev1` | Developer | Development |

## Standard Promotion Path

```
dev1 -> qa -> uat -> main
```

Each promotion:
1. Creates a `bundle/B{id}` branch from the target environment branch
2. Merges feature branches into the bundle
3. Validates against the target org
4. Creates a GitLab MR for review

## Hotfix Path

Hotfixes can skip intermediate environments:

```
dev1 -> uat (skip qa)
dev1 -> main (skip qa + uat) — requires CCB approval
```

Hotfix rules:
- Must use `--hotfix` flag
- Uses `RunSpecifiedTests` for speed
- MR requires explicit approval (no auto-merge)
- Must back-promote to all skipped environments after deployment

## Back-Promotion Path

After deploying to a higher environment:

```
main -> uat -> qa -> dev1
```

Back-promotion ensures lower environments stay in sync with production.

## Bundle Lifecycle

```
1. Created    — bundle/B0042 branch created from target
2. Merging    — Feature branches being merged
3. Cleaning   — /profile-clean running
4. Validating — /validate running against target org
5. Review     — GitLab MR open for review
6. Merged     — MR approved and merged
7. Deployed   — /deploy executed against target org
8. Archived   — Bundle branch deleted after 60 days
```
