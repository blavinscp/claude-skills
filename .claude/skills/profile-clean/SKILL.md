---
name: "profile-clean"
description: "Strip profile and permission set references to metadata not in the deployment package."
---

Clean profiles and permission sets. Full workflow: [salesforce-cicd/profile-clean/SKILL.md](../../../salesforce-cicd/profile-clean/SKILL.md)

## Quick Start

```bash
# Dry run (preview changes)
python3 salesforce-cicd/profile-clean/scripts/strip_profiles.py \
  --manifest package.xml --source-dir force-app/main/default --dry-run --format text

# Apply cleaning
python3 salesforce-cicd/profile-clean/scripts/strip_profiles.py \
  --manifest package.xml --source-dir force-app/main/default --format json
```

Strips fieldPermissions, objectPermissions, classAccesses, pageAccesses, and other references for metadata not in the deployment. Admin profile is never modified.
