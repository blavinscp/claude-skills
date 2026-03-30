---
name: "back-promote"
description: "Create merge requests from higher environments back to lower environments to keep branches in sync."
---

Generate back-promotion MRs. Full workflow: [salesforce-cicd/back-promote/SKILL.md](../../../salesforce-cicd/back-promote/SKILL.md)

## Quick Start

```bash
# After production deploy — creates MRs: main -> uat -> qa -> dev1
python3 salesforce-cicd/back-promote/scripts/back_promote.py \
  --deployed-env main --format json

# After UAT deploy — creates MRs: uat -> qa -> dev1
python3 salesforce-cicd/back-promote/scripts/back_promote.py \
  --deployed-env uat --format json
```

Output is a list of MR specs to create via GitLab MCP. Auto-resolves safe metadata, flags code conflicts for manual review.
