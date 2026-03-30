---
name: "profile-clean"
description: "Use when preparing a deployment package that contains profiles or permission sets. Strips field-level security, object permissions, class/page accesses, and other references from profiles and permission sets that point to metadata NOT included in the deployment package.xml manifest."
---

# Profile Clean

**Tier:** POWERFUL
**Category:** Engineering
**Domain:** Salesforce DevOps

## Overview

The Profile Clean skill parses `package.xml` to determine which metadata components are in the deployment, then strips profile and permission set XML elements that reference metadata outside that scope. Deploying full profiles with references to components not in the package causes deployment failures — this skill eliminates that class of error entirely.

This replaces Copado's "Cleaned full profile and permissionset" step with a transparent, scriptable process that produces a detailed report of every element removed.

## Prerequisites

- **Python 3.8+** (stdlib only, no external dependencies)
- **package.xml** manifest defining the deployment scope
- **Profile/PermissionSet files** in Salesforce metadata format (`.profile-meta.xml`, `.permissionset-meta.xml`)
- Source directory following standard SFDX or MDAPI layout
- **sf-decomposer (optional)** — `sf plugins install sf-decomposer`
- **force-md (optional)** — Go binary from GitHub releases

## Core Workflows

### Workflow 1: Dry-Run Mode

Preview what would be stripped without modifying any files. Use this to audit changes before committing.

```bash
python3 salesforce-cicd/profile-clean/scripts/strip_profiles.py \
  --manifest force-app/main/default/package.xml \
  --source-dir force-app/main/default \
  --dry-run \
  --format text
```

**Output:** A report listing every element that would be removed, grouped by file.

### Workflow 2: Standard Clean

Strip all out-of-scope references from every profile and permission set in the source directory.

```bash
python3 salesforce-cicd/profile-clean/scripts/strip_profiles.py \
  --manifest force-app/main/default/package.xml \
  --source-dir force-app/main/default \
  --format json
```

**Output:** JSON report of stripped elements. Files are modified in place.

### Workflow 3: Targeted Clean (Specific Files)

Strip references from specific profile or permission set files only.

```bash
python3 salesforce-cicd/profile-clean/scripts/strip_profiles.py \
  --manifest package.xml \
  --source-dir force-app/main/default \
  --files profiles/Sales.profile-meta.xml,permissionsets/CustomAccess.permissionset-meta.xml \
  --format text
```

### Workflow 4: CI Pipeline Integration

Run as a pre-deployment step in a CI pipeline. Exit code 0 means clean succeeded, exit code 1 means errors occurred, exit code 2 means invalid arguments.

```bash
python3 salesforce-cicd/profile-clean/scripts/strip_profiles.py \
  --manifest package.xml \
  --source-dir src/ \
  --format json > profile-clean-report.json

# Check exit code
if [ $? -ne 0 ]; then
  echo "Profile clean failed"
  exit 1
fi
```

### Workflow: Decomposed Profile Workflow

For projects using sf-decomposer, profiles are already split into granular files. The stripping process operates on individual files instead of monolithic XML:

```bash
# Recompose before stripping (if decomposed)
sf decomposer recompose -m "profile" -m "permissionset"

# Run standard strip
python3 salesforce-cicd/profile-clean/scripts/strip_profiles.py \
  --manifest package.xml --source-dir force-app/main/default --format json

# Re-decompose after stripping
sf decomposer decompose -m "profile" -m "permissionset" -s "grouped-by-tag" -p
```

### Workflow: Metadata Tidying with force-md

After stripping, sort XML elements for consistent diffs:

```bash
force-md profile tidy force-app/main/default/profiles/*.profile-meta.xml
force-md permissionset tidy force-app/main/default/permissionsets/*.permissionset-meta.xml
```

## How It Works

1. **Parse package.xml** — Reads the manifest and builds a set of all metadata components in the deployment, organized by metadata type (CustomObject, CustomField, ApexClass, ApexPage, CustomTab, RecordType, Layout, etc.).

2. **Scan profile/permset files** — Locates all `.profile-meta.xml` and `.permissionset-meta.xml` files in the source directory.

3. **Match elements to package scope** — For each XML element in a profile or permission set, checks whether the referenced metadata component exists in the package manifest. See [references/profile-permset-stripping-rules.md](references/profile-permset-stripping-rules.md) for the full mapping of element types to package.xml entries.

4. **Strip out-of-scope elements** — Removes XML elements whose referenced metadata is not in the deployment package.

5. **Preserve safe elements** — The Admin profile is never modified. Managed package references (elements containing a namespace prefix like `ns__`) are preserved. Standard object references (Account, Contact, etc.) are preserved when the profile is included in the package.

6. **Report** — Outputs a structured report of every element removed, including file path, element type, and referenced component name.

## Output Format

### JSON Output

```json
{
  "summary": {
    "files_scanned": 12,
    "files_modified": 8,
    "elements_stripped": 47,
    "dry_run": false
  },
  "details": [
    {
      "file": "profiles/Sales.profile-meta.xml",
      "stripped": [
        {
          "element_type": "fieldPermissions",
          "reference": "CustomObj__c.CustomField__c",
          "reason": "CustomField not in package.xml"
        },
        {
          "element_type": "objectPermissions",
          "reference": "CustomObj__c",
          "reason": "CustomObject not in package.xml"
        }
      ]
    }
  ],
  "preserved": {
    "admin_profile_skipped": true,
    "managed_package_refs_kept": 3
  }
}
```

### Text Output

```
Profile Clean Report
====================
Mode: LIVE (files modified)
Files scanned: 12 | Modified: 8 | Elements stripped: 47

profiles/Sales.profile-meta.xml (14 elements stripped)
  - fieldPermissions: CustomObj__c.CustomField__c (not in package)
  - objectPermissions: CustomObj__c (not in package)
  ...

profiles/Admin.profile-meta.xml (SKIPPED - Admin profile)

Managed package references preserved: 3
```

## Scripts

### strip_profiles.py

Core script that performs the profile and permission set cleaning.

```bash
python3 salesforce-cicd/profile-clean/scripts/strip_profiles.py --help
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--manifest` | Yes | Path to package.xml |
| `--source-dir` | Yes | Path to source directory containing profiles/permsets |
| `--files` | No | Comma-separated list of specific files to process (relative to source-dir) |
| `--dry-run` | No | Preview changes without modifying files |
| `--format` | No | Output format: `json` or `text` (default: `text`) |

## Anti-Patterns

- **Never deploy full profiles without cleaning** — Full profiles contain references to every component in the org; deploying them removes access to anything not in the package
- **Never strip the Admin profile** — Admin profile has system-level permissions that should be managed manually, not by automated stripping
- **Never strip managed package references** — Managed package metadata is not in your package.xml but removing its profile entries revokes user access to installed packages
- **Never skip dry-run on first use** — Always preview what will be stripped before modifying files in a new project
- **Never run profile-clean after deployment** — Run it before validation/deployment as a preparation step, not as a fix-up

## References

- [references/profile-permset-stripping-rules.md](references/profile-permset-stripping-rules.md) — Element mapping rules
- [references/decomposed-profiles-guide.md](references/decomposed-profiles-guide.md) — Working with sf-decomposer decomposed profiles
