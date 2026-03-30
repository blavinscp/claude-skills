# Back-Promotion Strategy

## Why Back-Promotion Is Needed

When code is deployed to a higher environment (e.g., production), changes that happened during the release process -- conflict resolutions, hotfixes, profile adjustments, last-minute configuration tweaks -- exist only on the higher environment branch. Without back-promotion, lower environment branches diverge from production, causing:

1. **Phantom merge conflicts** on the next promotion cycle
2. **Missing fixes** in QA/UAT that were applied during the release
3. **Inconsistent testing** because QA/UAT branches lack production-verified changes
4. **Compounding drift** that gets worse with every release cycle

Back-promotion eliminates drift by flowing changes downward after every deployment.

## The Back-Promotion Path

Changes always flow downward through the environment chain:

```
main (production)
  └── uat
       └── qa
            └── dev1
```

### Post-Production Deploy

After a successful production deployment:

| Step | Source | Target | Purpose |
|------|--------|--------|---------|
| 1 | main | uat | Sync UAT with production |
| 2 | uat | qa | Sync QA with UAT |
| 3 | qa | dev1 | Sync dev with QA |

### Post-UAT Deploy

After a successful UAT deployment:

| Step | Source | Target | Purpose |
|------|--------|--------|---------|
| 1 | uat | qa | Sync QA with UAT |
| 2 | qa | dev1 | Sync dev with QA |

### Post-QA Deploy

After a successful QA deployment:

| Step | Source | Target | Purpose |
|------|--------|--------|---------|
| 1 | qa | dev1 | Sync dev with QA |

## Conflict Resolution Rules

Back-promote merges follow specific conflict resolution rules. The guiding principle is: **the higher environment branch is the source of truth** for metadata, while code conflicts require human review.

### Auto-Resolve (Accept Source Branch)

These metadata types are safe to auto-resolve by accepting the source (higher environment) version:

| Metadata Type | File Pattern | Reasoning |
|--------------|--------------|-----------|
| Profiles | `*.profile-meta.xml` | Higher env always has the verified permission superset |
| Permission Sets | `*.permissionset-meta.xml` | Same as profiles |
| Page Layouts | `*.layout-meta.xml` | Higher env has the deployed layout |
| Custom Labels | `*.labels-meta.xml` | Higher env has the latest translations |
| package.xml | `manifest/package.xml` | Regenerate from branch contents |

### Require Manual Review

These types must be reviewed by a developer before the MR is merged:

| Metadata Type | File Pattern | Risk |
|--------------|--------------|------|
| Apex Classes | `*.cls`, `*.cls-meta.xml` | Logic conflicts can break functionality |
| Apex Triggers | `*.trigger`, `*.trigger-meta.xml` | Same as classes |
| LWC Components | `lwc/**/*` | UI/logic conflicts |
| Aura Components | `aura/**/*` | UI/logic conflicts |
| Flows | `*.flow-meta.xml` | Version conflicts can break automation |
| Custom Objects | `*.object-meta.xml` | Schema changes need careful review |
| Custom Fields | `*.field-meta.xml` | Schema changes |
| OmniStudio | `OmniScript/**`, `IntegrationProcedure/**` | Sequencing dependencies |

## Timing

Back-promotion should happen **immediately after deployment verification**. The sequence is:

1. Deploy to target environment
2. Run smoke tests / post-deployment validation
3. Confirm deployment succeeded (check deployment status in Salesforce)
4. Trigger back-promotion chain
5. Log all back-promote actions to audit trail

**Do not batch back-promotions.** Each deployment triggers its own back-promote chain. Batching causes larger conflict sets that are harder to resolve.

## Handling Unresolvable Conflicts

When a back-promote MR has conflicts that cannot be auto-resolved:

### Step 1: Identify the Conflict Owner

Look at `git log` for the conflicting file to find the last developer who modified it. Assign the MR to that developer.

### Step 2: Add Context to the MR

The MR description should include:
- Which deployment triggered the back-promote
- Which files are conflicted
- Which conflict resolution rule applies (auto-resolve or manual review)
- Link to the original Jira stories in the deployment

### Step 3: Set a Deadline

Back-promote MRs should be resolved within **24 hours** of creation. Longer delays increase the risk of additional drift.

### Step 4: Escalation

If a back-promote MR is not resolved within 24 hours:
1. Notify the team lead
2. Add the MR to the next standup agenda
3. Consider pausing new promotions until the back-promote chain is clear

### Step 5: Post-Resolution

After all conflicts are resolved and the MR is merged:
1. Continue the back-promote chain (create the next MR in sequence)
2. Log the resolution to the audit trail
3. Verify no additional conflicts were introduced

## Common Scenarios

### Hotfix Back-Promote

When a hotfix is deployed directly to production (bypassing normal promotion):
1. Back-promote follows the full chain: main -> uat -> qa -> dev1
2. Conflicts are more likely because the hotfix skipped environments
3. All environments must receive the fix to prevent regression

### Release-Day Back-Promote

During a production release:
1. Wait for all deployment verifications to complete
2. Run back-promote once (not after each component)
3. The single back-promote captures all release changes

### Failed Back-Promote

If a back-promote MR fails CI/pipeline:
1. Do NOT force-merge
2. Investigate the failure (usually a test failure caused by the merged changes)
3. Fix the test or code in the back-promote MR branch
4. Re-run the pipeline
5. Log the failure and resolution to audit trail
