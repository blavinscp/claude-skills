# OmniStudio Deployment Sequencing

## Dependency Order

OmniStudio components have strict deployment dependencies. Deploy in this order:

```
Phase 1: DataRaptors (no dependencies)
Phase 2: Integration Procedures (depend on DataRaptors)
Phase 3: OmniScripts (depend on Integration Procedures + DataRaptors)
Phase 4: FlexCards (depend on OmniScripts + Integration Procedures)
```

## Why Sequential Deployment?

OmniStudio components are stored as VlocityDataPack metadata. Unlike standard Salesforce metadata, they have runtime dependencies that must be resolved at deploy time:

- **DataRaptors** define data extraction/transformation logic
- **Integration Procedures** orchestrate DataRaptors into callable services
- **OmniScripts** render UI and invoke Integration Procedures
- **FlexCards** display data from OmniScripts and Integration Procedures

Deploying out of order causes `Unable to resolve reference` failures.

## Validation Strategy

When validating OmniStudio components:

1. **Split the manifest** — Separate OmniStudio components from standard metadata
2. **Validate standard first** — Run standard metadata validation
3. **Validate OmniStudio sequentially** — Validate each phase in order
4. **Combine results** — Aggregate pass/fail across all validations

```bash
# Phase 1: DataRaptors
sf project deploy validate --manifest dataraptors-package.xml --target-org qa

# Phase 2: Integration Procedures
sf project deploy validate --manifest ip-package.xml --target-org qa

# Phase 3: OmniScripts
sf project deploy validate --manifest omniscripts-package.xml --target-org qa

# Phase 4: FlexCards
sf project deploy validate --manifest flexcards-package.xml --target-org qa
```

## Component Type Mapping

| OmniStudio Component | Metadata Type | Package.xml Member |
|----------------------|---------------|-------------------|
| DataRaptor | `OmniDataTransform` | `OmniDataTransform/*` |
| Integration Procedure | `OmniProcess` (type=IP) | `OmniProcess/*` |
| OmniScript | `OmniProcess` (type=OS) | `OmniProcess/*` |
| FlexCard | `OmniUiCard` | `OmniUiCard/*` |

## Failure Recovery

If a phase fails:
1. Fix the failing component
2. Re-validate from the failed phase (not from the beginning)
3. Each phase's validation is independent once its dependencies are deployed
