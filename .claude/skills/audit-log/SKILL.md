---
name: "audit-log"
description: "Log and query HIPAA-compliant pipeline audit trail entries."
---

Manage the pipeline audit trail. Full workflow: [salesforce-cicd/audit-log/SKILL.md](../../../salesforce-cicd/audit-log/SKILL.md)

## Quick Start

```bash
# Log a pipeline action
python3 salesforce-cicd/audit-log/scripts/audit_logger.py \
  --action promote --environment qa --status success \
  --details '{"stories": ["US-1234"], "bundle": "bundle/B0042"}' \
  --format json

# Query audit history
python3 salesforce-cicd/audit-log/scripts/audit_logger.py \
  --query action=deploy --query environment=production --format text
```

All entries stored in `pipeline-audit/audit.jsonl`. No PHI — use Jira story keys only. Retained for minimum 6 years per HIPAA.
