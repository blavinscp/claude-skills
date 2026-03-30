---
name: "ccb-submit"
description: "Prepare and submit ServiceNow CCB change requests for production deployments."
---

Submit CCB change requests. Full workflow: [salesforce-cicd/ccb-submit/SKILL.md](../../../salesforce-cicd/ccb-submit/SKILL.md)

## Quick Start

```bash
# Generate payload (for manual submission or review)
python3 salesforce-cicd/ccb-submit/scripts/servicenow_submit.py \
  --change-type standard \
  --description "Deploy US-1234, US-1235 to production" \
  --risk-level low \
  --deployment-window "2026-04-01 06:00-08:00 UTC" \
  --rollback-plan "Quick-deploy validation ID 0Af3t00000XXXXXX" \
  --format json

# Submit via API
SERVICENOW_TOKEN=xxx python3 salesforce-cicd/ccb-submit/scripts/servicenow_submit.py \
  --change-type standard \
  --description "Deploy US-1234" \
  --risk-level low \
  --deployment-window "2026-04-01 06:00-08:00 UTC" \
  --rollback-plan "Quick-deploy ID" \
  --api-url "https://instance.service-now.com/api/now/table/change_request" \
  --format json
```

Change types: `standard` (pre-approved), `normal` (CAB review), `emergency` (P0/P1 hotfix).
