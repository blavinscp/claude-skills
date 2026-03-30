---
name: "promote"
description: "Promote Salesforce metadata from one environment to the next via bundle creation, validation, and GitLab MR."
---

Orchestrate a Salesforce promotion. Full workflow: [salesforce-cicd/promote/SKILL.md](../../../salesforce-cicd/promote/SKILL.md)

## Quick Start

```bash
# Standard promotion (dev1 -> qa)
python3 salesforce-cicd/promote/scripts/promotion_orchestrator.py \
  --stories US-1234,US-1235 --from-env dev1 --to-env qa --format json

# Hotfix (skip intermediate envs)
python3 salesforce-cicd/promote/scripts/promotion_orchestrator.py \
  --stories US-9999 --from-env dev1 --to-env uat --hotfix --format json

# Create bundle only (without full orchestration)
python3 salesforce-cicd/promote/scripts/create_bundle.py \
  --stories US-1234,US-1235 --target-env qa --format json

# Dry run (preview without executing)
python3 salesforce-cicd/promote/scripts/promotion_orchestrator.py \
  --stories US-1234 --from-env dev1 --to-env qa --dry-run --format text
```

Promotion path: `dev1 -> qa -> uat -> main (production)`. Hotfixes can skip intermediate environments with `--hotfix`.
