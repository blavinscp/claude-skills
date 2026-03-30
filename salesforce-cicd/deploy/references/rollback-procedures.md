# Rollback Procedures

Salesforce does not provide a native "undo deployment" command. Rollback requires deploying a corrective change — either re-deploying the prior version of affected components or deploying destructive changes to remove new components.

## Rollback Decision Matrix

| Situation | Strategy | Risk | Speed |
|-----------|----------|------|-------|
| Deployed updated metadata (Apex, LWC, configs) | Re-deploy previous version | Low — overwrites with known-good state | Fast (minutes) |
| Deployed new components that must be removed | Destructive changes manifest | Medium — must ensure no dependencies | Moderate |
| OmniStudio deployment broke processes | Deactivate in reverse order | Low — deactivation is non-destructive | Fast |
| Multiple components across types | Combined approach | Medium — coordinate order carefully | Slow (phased) |
| Unknown scope of impact | Full org comparison | High — requires metadata diff | Slow |

## Strategy 1: Re-Deploy Previous Version

The safest and most common rollback. Retrieve the prior version of affected components from source control and deploy them.

### Steps

1. **Identify the prior commit** — Find the last known-good commit in your branch history.

```bash
git log --oneline -10
```

2. **Check out the prior version of affected files.**

```bash
git diff HEAD~1 --name-only -- force-app/
```

3. **Build a manifest for only the changed components.** Use the existing package.xml or generate one from the diff.

4. **Deploy the prior version.**

```bash
python3 salesforce-cicd/deploy/scripts/deploy_package.py \
  --target-org production \
  --manifest rollback-package.xml \
  --format json
```

### When to Use

- Apex classes or triggers were modified (not newly created)
- Lightning Web Components were updated
- Custom metadata, validation rules, or flows were changed
- Page layouts or record types were modified

## Strategy 2: Destructive Changes Manifest

Use when new components were added and must be completely removed from the org. Salesforce requires a `destructiveChanges.xml` manifest to delete metadata.

### Steps

1. **Create `destructiveChanges.xml`** listing the components to remove.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>MyNewClass</members>
    <name>ApexClass</name>
  </types>
  <types>
    <members>myNewComponent</members>
    <name>LightningComponentBundle</name>
  </types>
  <version>62.0</version>
</Package>
```

2. **Create an empty `package.xml`** (required by the CLI even for destructive-only deploys).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <version>62.0</version>
</Package>
```

3. **Deploy the destructive changes.**

```bash
sf project deploy start \
  --target-org production \
  --manifest package.xml \
  --post-destructive-changes destructiveChanges.xml \
  --json \
  --wait 30
```

### When to Use

- New Apex classes or triggers were added and must be removed
- New LWC components were created in the deployment
- Custom objects or fields were added that should not exist in the org

### Warnings

- **Destructive deletes are permanent.** There is no undo for a destructive deployment.
- **Check for dependencies first.** If other metadata references the component you are deleting, the destructive deploy will fail. Remove references first.
- **Never delete components that existed before your deployment.** Only remove components that your deployment introduced.

## Strategy 3: OmniStudio Rollback

OmniStudio components (DataRaptors, Integration Procedures, OmniScripts, FlexCards) must be deactivated in reverse deployment order before re-deploying prior versions.

### Steps

1. **Deactivate in reverse order:**
   - Deactivate FlexCards first
   - Deactivate OmniScripts
   - Deactivate Integration Procedures
   - Deactivate DataRaptors

2. **Re-deploy previous versions** of each component type in forward order:
   - Deploy DataRaptors
   - Deploy Integration Procedures
   - Deploy OmniScripts
   - Deploy FlexCards

3. **Re-activate** the restored versions in forward order.

### Deactivation Commands

OmniStudio components are deactivated through the Salesforce UI or by deploying a version with `IsActive` set to `false`. The specific approach depends on whether you are using OmniStudio managed package or standard Salesforce Industries.

For standard Industries metadata:

```bash
# Deploy deactivated versions
sf project deploy start \
  --target-org production \
  --manifest rollback-deactivate.xml \
  --json \
  --wait 30
```

### When to Use

- OmniScript is producing errors for end users
- An Integration Procedure is returning incorrect data
- FlexCards are rendering incorrectly
- DataRaptor transformations are corrupting data

### Warnings

- **Deactivation affects all users immediately.** OmniStudio components are live the moment they are activated.
- **Version management is critical.** OmniStudio supports multiple versions — deactivating the current version does not automatically activate the prior version. You must explicitly activate the desired version.
- **Test in lower environments first** if possible. OmniStudio rollbacks in production should mirror a tested rollback from UAT.

## Strategy 4: Full Org Comparison

When the scope of impact is unclear, compare the target org's current metadata against the last known-good state.

### Steps

1. **Retrieve current org metadata.**

```bash
sf project retrieve start \
  --target-org production \
  --manifest package.xml \
  --output-dir org-current/ \
  --json
```

2. **Compare against the known-good source.**

```bash
diff -rq org-current/force-app/ git-prior-version/force-app/
```

3. **Build a targeted rollback manifest** from the diff results.

4. **Deploy the corrective package.**

### When to Use

- Multiple teams deployed simultaneously and it is unclear which change caused the issue
- A deployment included a large number of components and the failure is not easily isolated
- The deployment was performed outside of the standard pipeline (e.g., change sets, Salesforce UI)

## Post-Rollback Checklist

After any rollback, complete the following:

- [ ] Verify the rollback deployed successfully (check deployment status)
- [ ] Confirm the issue is resolved in the target org (smoke test)
- [ ] Log the rollback in the audit trail (`/audit-log`)
- [ ] Notify stakeholders (CCB, release manager, affected teams)
- [ ] Update the Jira story with rollback details and root cause
- [ ] If production, file an incident report per HIPAA compliance requirements
- [ ] Back-promote any rollback changes to lower environments to keep branches in sync
