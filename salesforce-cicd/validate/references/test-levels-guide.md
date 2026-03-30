# Apex Test Level Decision Guide

## Test Levels

| Level | What Runs | When to Use |
|-------|-----------|-------------|
| `NoTestRun` | No tests | Metadata-only deploys (layouts, profiles, page layouts) |
| `RunSpecifiedTests` | Named test classes only | Hotfixes, targeted changes where you know the affected tests |
| `RunLocalTests` | All non-managed package tests | Standard promotions to QA/UAT/Production |
| `RunAllTestsInOrg` | All tests including managed packages | Rare — only when managed package interactions are suspected |

## Decision Matrix

### By Environment

| Target Env | Default Level | Override Allowed? |
|------------|--------------|-------------------|
| Dev1 | `NoTestRun` | Yes — development iteration |
| QA | `RunLocalTests` | Yes — `RunSpecifiedTests` for hotfixes |
| UAT | `RunLocalTests` | No — full regression required |
| Production | `RunLocalTests` | No — Salesforce enforces minimum 75% coverage |

### By Change Type

| Change Type | Recommended Level | Rationale |
|-------------|------------------|-----------|
| Apex class/trigger | `RunLocalTests` | Must validate all dependent tests |
| LWC only | `NoTestRun` | No server-side tests needed |
| Profile/PermSet | `NoTestRun` | Metadata-only |
| OmniStudio | `RunSpecifiedTests` | Test only OmniStudio-specific tests |
| Mixed (Apex + metadata) | `RunLocalTests` | Full coverage for safety |
| Hotfix (P0) | `RunSpecifiedTests` | Speed critical — name affected tests |
| Hotfix (P1) | `RunLocalTests` | Less urgent — full regression |

## Coverage Requirements

- **Production deployments**: 75% overall org coverage required by Salesforce
- **Per-class minimum**: No enforced minimum, but recommend 75% per class
- **Trigger coverage**: 1% minimum (at least one test fires the trigger)

## Quick Reference

```bash
# Standard QA promotion
sf project deploy validate --target-org qa --manifest package.xml --test-level RunLocalTests

# Hotfix with specific tests
sf project deploy validate --target-org qa --manifest package.xml \
  --test-level RunSpecifiedTests --tests AccountTriggerTest,ContactServiceTest

# Metadata-only (no tests needed)
sf project deploy validate --target-org qa --manifest package.xml --test-level NoTestRun
```
