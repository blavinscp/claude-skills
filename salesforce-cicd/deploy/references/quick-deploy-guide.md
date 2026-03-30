# Quick-Deploy Guide

Quick-deploy allows you to deploy a previously validated package to a Salesforce org without re-running Apex tests. This is the fastest and safest path to production because all tests have already passed during validation.

## How Quick-Deploy Works

1. **Validate** — Run `sf project deploy validate` with full test execution. This stages the deployment on the Salesforce server and runs all specified tests.
2. **Store the job ID** — The validation returns a deployment job ID (starts with `0Af`). Save this ID.
3. **Quick-deploy** — Run `sf project deploy quick --job-id <ID>` to deploy the already-validated package without re-running tests.

The Salesforce server retains the validated deployment artifacts. Quick-deploy tells the server to proceed with the deployment it already prepared.

## CLI Commands

### Step 1: Validate

```bash
sf project deploy validate \
  --target-org production \
  --manifest package.xml \
  --test-level RunLocalTests \
  --json \
  --wait 120
```

Capture the job ID from the response:

```json
{
  "result": {
    "id": "0Af3t00000AbCdEFG",
    "status": "Succeeded"
  }
}
```

Or using the deploy skill's validate wrapper:

```bash
python3 salesforce-cicd/validate/scripts/validate_deployment.py \
  --target-org production \
  --manifest package.xml \
  --format json
```

### Step 2: Quick-Deploy

```bash
sf project deploy quick \
  --job-id 0Af3t00000AbCdEFG \
  --target-org production \
  --json \
  --wait 30
```

Or using the deploy skill:

```bash
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org production \
  --validation-id 0Af3t00000AbCdEFG \
  --format json
```

## Timing Constraints

| Constraint | Limit | What Happens |
|-----------|-------|-------------|
| Validation expiry | **10 days** | After 10 days the validated deployment is purged from the server. Quick-deploy will fail with `INVALID_ID_FIELD`. You must re-validate. |
| Org metadata changes | Any change invalidates | If any metadata is deployed to the target org between validation and quick-deploy (by anyone, including managed package upgrades), the quick-deploy may fail. Re-validate if the org has changed. |
| Concurrent deployments | One at a time | Only one deployment (validate or deploy) can run per org at a time. Wait for any in-progress deployment to finish. |

## When to Use Quick-Deploy

| Scenario | Use Quick-Deploy? | Reason |
|----------|-------------------|--------|
| Production deploy after CCB approval | Yes | Tests already ran, minimize deployment window |
| UAT deploy after QA validation | Yes, if same package | Avoids redundant test execution |
| Deploy after code fix to validation failures | No | Package changed, must re-validate |
| Deploy more than 10 days after validation | No | Validation expired |
| Deploy after someone else pushed metadata | No | Org state changed, validation may be stale |

## Troubleshooting

### INVALID_ID_FIELD

The validation job ID is not recognized. Causes:
- Validation expired (older than 10 days)
- Job ID is from a different org
- Job ID is from a validation that failed

**Fix:** Re-run validation with `/validate` and use the new job ID.

### ALREADY_IN_PROGRESS

Another deployment is running on the target org.

**Fix:** Wait for the current deployment to complete. Check status with:

```bash
sf project deploy report --target-org production --json
```

### Quick-Deploy Fails Despite Successful Validation

Metadata was modified in the target org after validation. Common causes:
- Another team member deployed changes
- A managed package was updated
- A change set was deployed via the Salesforce UI

**Fix:** Re-validate the package against the current org state, then quick-deploy with the new job ID.
