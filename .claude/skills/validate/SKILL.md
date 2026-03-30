---
name: "validate"
description: "Validate a Salesforce deployment package against a target org with Apex tests."
---

Validate a Salesforce deployment package. Full workflow: [salesforce-cicd/validate/SKILL.md](../../../salesforce-cicd/validate/SKILL.md)

## Quick Start

```bash
# Standard validation (RunLocalTests)
python3 salesforce-cicd/validate/scripts/validate_deployment.py \
  --target-org qa --manifest package.xml --format json

# Specified tests (faster for hotfixes)
python3 salesforce-cicd/validate/scripts/validate_deployment.py \
  --target-org qa --manifest package.xml \
  --test-level RunSpecifiedTests --tests AccountTriggerTest --format json

# Check existing job status
python3 salesforce-cicd/validate/scripts/validate_deployment.py \
  --job-id 0Af3t00000XXXXXX --format text

# Parse test results
python3 salesforce-cicd/validate/scripts/parse_test_results.py \
  --input test-results.json --format text
```

For OmniStudio components, use sequential validation per [omnistudio-sequencing.md](../../../salesforce-cicd/references/omnistudio-sequencing.md).
