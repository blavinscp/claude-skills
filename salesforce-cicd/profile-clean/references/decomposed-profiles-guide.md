# Decomposed Profiles Guide

## Why Decompose Profiles?

Monolithic profile XML files (often 5,000+ lines) cause:
- **Merge hell** — Every promotion touches the same giant file
- **Opaque diffs** — Hard to see what actually changed
- **Conflict storms** — Multiple teams modifying different fields in the same file

sf-decomposer solves this by splitting profiles into granular, per-element files.

## How sf-decomposer Works

### Before (Monolithic)

```
force-app/main/default/profiles/
  Admin.profile-meta.xml          (5,000+ lines)
  Custom__Sales.profile-meta.xml  (3,000+ lines)
```

### After Decomposition (Grouped by Tag)

```
force-app/main/default/profiles/
  Admin/
    fieldPermissions/
      Account.Active__c.fieldPermissions-meta.xml
      Contact.Email__c.fieldPermissions-meta.xml
    objectPermissions/
      Account.objectPermissions-meta.xml
    classAccesses/
      AccountService.classAccesses-meta.xml
    Admin.profile-meta.xml  (skeleton with non-decomposed elements)
```

Each file contains only one permission — merge conflicts become per-field instead of per-file.

## Setup

### Install

```bash
sf plugins install sf-decomposer
```

### Configure

Create `.sfdecomposer.config.json` in project root:

```json
{
  "metadataSuffixes": ["profile", "permissionset"],
  "decompositionStrategy": "grouped-by-tag",
  "decomposeNestedPermissions": true,
  "packageDirectoriesToIgnore": [],
  "purge": true
}
```

## CI/CD Integration

### Post-Retrieve: Decompose

After any `sf project retrieve`, decompose the profiles:

```bash
sf project retrieve start --target-org dev1 --manifest package.xml
sf decomposer decompose -m "profile" -m "permissionset" -s "grouped-by-tag" -p
```

### Pre-Deploy: Recompose

Before any deployment, recompose back to standard format:

```bash
sf decomposer recompose -m "profile" -m "permissionset"
sf project deploy start --target-org qa --manifest package.xml
```

### Git Workflow

```
1. Retrieve from org     -> sf project retrieve
2. Decompose             -> sf decomposer decompose
3. Commit granular files  -> git add && git commit
4. (Later) Deploy        -> sf decomposer recompose
5. Deploy recomposed     -> sf project deploy
```

## How force-md Complements sf-decomposer

**sf-decomposer** handles the file structure (split/merge).
**force-md** handles the content quality (sort/clean).

Use together:

```bash
# After decompose: sort elements for consistent diffs
force-md profile tidy force-app/main/default/profiles/*.profile-meta.xml
force-md permissionset tidy force-app/main/default/permissionsets/*.permissionset-meta.xml

# Add field permission to a specific permset
force-md permissionset fieldPermissions add \
  -p MyPermSet \
  -f Account.Custom_Field__c \
  --readable --editable
```

## Impact on /profile-clean

With decomposed profiles, `/profile-clean` (strip_profiles.py) operates on small individual files instead of parsing giant XML. The stripping logic remains the same, but:

- **Faster** — Each file is a few lines, not thousands
- **Safer** — Stripping one field can't accidentally break another
- **Reviewable** — Stripped files show as deleted in git diff

If sf-decomposer is NOT installed, strip_profiles.py falls back to its built-in XML parsing of monolithic files.

## Migration from Monolithic to Decomposed

1. Ensure all branches are clean (no pending profile changes)
2. Run decompose on the main branch
3. Commit the decomposed structure
4. Back-promote to all environments
5. Update CI/CD to include recompose before deploy

**Warning:** This is a one-time structural change that touches every profile file. Coordinate with all teams before executing.
