# Open Source Tools for Salesforce CI/CD

All tools below are optional enhancements. The pipeline works without them but gains significant capabilities when they're installed.

## Tier 1: High Value — Direct Integration

### sfdx-git-delta (SGD)

**What:** Generates delta `package.xml` + `destructiveChanges.xml` from git diff between two commits or branches.

**Install:**
```bash
sf plugins install sfdx-git-delta
```

**Key Commands:**
```bash
# Generate delta package from branch comparison
sf sgd source delta --from origin/qa --to HEAD --output-dir delta/ --generate-delta

# Scope to specific source directories
sf sgd source delta --from origin/qa --to HEAD --output-dir delta/ \
  --source-dir force-app/main/default --generate-delta

# Exclude patterns from destructive changes
sf sgd source delta --from origin/qa --to HEAD --output-dir delta/ \
  --ignore-destructive-file .sgdignore --generate-delta
```

**Output:** `delta/package/package.xml` + `delta/destructiveChanges/destructiveChanges.xml` + copied source files.

**Used by:** `/promote`, `/back-promote`, `@pipeline-ops`

**Source:** https://github.com/scolladon/sfdx-git-delta

---

### sf-decomposer

**What:** Splits monolithic profile/permset XML into per-field granular files for version control. Recomposes before deployment.

**Install:**
```bash
sf plugins install sf-decomposer
```

**Key Commands:**
```bash
# Decompose profiles into per-field files (after retrieve)
sf decomposer decompose -m "profile" -s "grouped-by-tag" -p

# Decompose permission sets
sf decomposer decompose -m "permissionset" -s "grouped-by-tag" -p

# Recompose before deployment
sf decomposer recompose -m "profile" -m "permissionset"
```

**Strategies:**
- `unique-id` — Each element gets its own file (most granular)
- `grouped-by-tag` — Elements grouped by type (e.g., all `fieldPermissions` in one file)

**Config:** `.sfdecomposer.config.json` in project root for automation.

**Used by:** `/profile-clean`, `@pipeline-ops`

**Source:** https://github.com/mcarvin8/sf-decomposer

---

### sfdx-plugin-manifest (@jayree)

**What:** Generates, cleans, and manages `package.xml` and `destructiveChanges.xml` from org metadata or git changes.

**Install:**
```bash
sf plugins install @jayree/sfdx-plugin-manifest
```

**Key Commands:**
```bash
# Generate package.xml from org metadata
sf jayree manifest generate --target-org qa

# Clean up manifest (remove unwanted components)
sf jayree manifest cleanup --file package.xml

# Generate from git diff (alternative to SGD)
sf jayree manifest git diff --source-dir force-app
```

**Used by:** `/promote`, `@meta-analyst`

**Source:** https://github.com/jayree/sfdx-plugin-manifest

---

### vlocity_build

**What:** Export and deploy OmniStudio/Vlocity DataPacks with automatic dependency ordering. Handles DataRaptors, Integration Procedures, OmniScripts, and FlexCards natively.

**Install:**
```bash
npm install --global vlocity
```
Requires Node 18+.

**Key Commands:**
```bash
# Deploy with automatic dependency ordering
vlocity -sfdx.username qa -job deploy.yaml packDeploy

# Export specific component types
vlocity -sfdx.username qa -job export.yaml packExport

# Validate deployment (dry run)
vlocity -sfdx.username qa -job deploy.yaml packDeploy --simulated
```

**YAML Job File:**
```yaml
projectPath: ./vlocity-datapacks
queries:
  - OmniScript
  - DataRaptor
  - IntegrationProcedure
  - FlexCard
```

**Used by:** `/validate`, `/deploy`, `@omnistudio-dev`

**Source:** https://github.com/vlocityinc/vlocity_build

---

### plugin-omnistudio-migration-tool

**What:** Official Salesforce CLI plugin for migrating OmniStudio components from unmanaged (Vlocity) to managed (Salesforce Industries) packages.

**Install:**
```bash
sf plugins install @salesforce/plugin-omnistudio-migration-tool
```

**Key Commands:**
```bash
# Migrate all component types
sf omnistudio migration migrate -u target_org --namespace=vlocity_cmt

# Migrate specific components only
sf omnistudio migration migrate -u target_org --namespace=vlocity_cmt --only=dr  # DataRaptors
sf omnistudio migration migrate -u target_org --namespace=vlocity_cmt --only=ip  # Integration Procedures
sf omnistudio migration migrate -u target_org --namespace=vlocity_cmt --only=os  # OmniScripts
sf omnistudio migration migrate -u target_org --namespace=vlocity_cmt --only=fc  # FlexCards

# Migrate all versions (not just active)
sf omnistudio migration migrate -u target_org --namespace=vlocity_cmt --allversions
```

**Used by:** `@omnistudio-dev`

**Source:** https://github.com/salesforcecli/plugin-omnistudio-migration-tool

---

## Tier 2: Medium Value — Patterns & Automation

### sfdx-hardis

**What:** Comprehensive Salesforce DevOps CLI with CI/CD pipeline generation, daily metadata backup, org monitoring with Grafana, and AI-enhanced documentation.

**Install:**
```bash
sf plugins install sfdx-hardis
```

**Key Commands:**
```bash
# Monitor org for changes
sf hardis:org:monitor --target-org production

# Generate CI/CD pipeline config
sf hardis:project:deploy:smart --check

# Backup org metadata
sf hardis:org:retrieve:full --target-org production
```

**Used by:** `@meta-analyst`, `@pipeline-ops` (reference patterns)

**Source:** https://github.com/hardisgroupcom/sfdx-hardis

---

### force-md

**What:** CLI for manipulating Salesforce metadata — sorts XML elements, adds field permissions, merges permission sets.

**Install:** Download Go binary from releases.

**Key Commands:**
```bash
# Sort profile elements in natural order
force-md profile tidy force-app/main/default/profiles/*.profile-meta.xml

# Sort permission set elements
force-md permissionset tidy force-app/main/default/permissionsets/*.permissionset-meta.xml

# Add field permission to a permission set
force-md permissionset fieldPermissions add -p MyPermSet -f Account.Custom_Field__c --readable --editable
```

**Used by:** `/profile-clean`

**Source:** https://github.com/ForceCLI/force-md

---

### octoforce-actions

**What:** GitHub's official lightweight Salesforce CI/CD template using GitHub Actions.

**Key Patterns:**
- Sandbox creation per issue
- PR-triggered UAT deployments
- Release note compilation
- Production deployment with approval gates

**Used by:** Reference patterns for CI workflow design.

**Source:** https://github.com/github/octoforce-actions

---

## Tier 3: Niche Value — Audit & Compliance

### AuditForce

**What:** Native Salesforce app for surfacing the Setup Audit Trail. Provides org-side visibility into admin configuration changes.

**Source:** https://github.com/danieljpeter/AuditForce

**Used by:** `/audit-log` (complementary), `@healthcloud-eng`

**Integration:** Provides the org-side audit trail that complements our pipeline-side JSONL audit log. Together they give full coverage: AuditForce tracks what changed in the org, `/audit-log` tracks what the pipeline did.

---

### hipaa-compliance-developers-guide

**What:** Developer-focused HIPAA compliance guide covering technical requirements, BAAs, breach notification, and security controls.

**Source:** https://github.com/truevault-safe/hipaa-compliance-developers-guide

**Used by:** `@healthcloud-eng` (reference material for compliance checklists)

---

## Quick Install (All Recommended Tools)

```bash
# Tier 1 — SF CLI Plugins
sf plugins install sfdx-git-delta
sf plugins install sf-decomposer
sf plugins install @jayree/sfdx-plugin-manifest
sf plugins install @salesforce/plugin-omnistudio-migration-tool

# Tier 1 — npm
npm install --global vlocity

# Tier 2 — SF CLI Plugins
sf plugins install sfdx-hardis

# Tier 2 — Standalone
# force-md: download from https://github.com/ForceCLI/force-md/releases
```

## Tool Detection in Scripts

Our Python scripts detect tools at runtime:

```python
def detect_tool(command: str) -> bool:
    """Check if a CLI tool is available."""
    try:
        subprocess.run([command, "--version"], capture_output=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
```

Tools are always optional — scripts fall back to built-in logic when tools aren't installed.
