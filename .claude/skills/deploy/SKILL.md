---
name: "deploy"
description: "Deploy a validated Salesforce package to a target org. Supports quick-deploy from validation ID."
---

Deploy to a Salesforce org. Full workflow: [salesforce-cicd/deploy/SKILL.md](../../../salesforce-cicd/deploy/SKILL.md)

**This is always user-initiated. Never auto-deploy.**

## Quick Start

```bash
# Standard deploy from manifest
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org qa --manifest package.xml --format json

# Quick-deploy from prior validation
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org qa --validation-id 0Af3t00000XXXXXX --format json

# Dry run
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org qa --manifest package.xml --dry-run --format text
```

For OmniStudio, deploy in phases: DataRaptors -> IPs -> OmniScripts -> FlexCards.
