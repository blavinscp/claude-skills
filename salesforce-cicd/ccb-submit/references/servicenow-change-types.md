# ServiceNow Change Types

## Change Types

### Standard Change

Pre-approved, low-risk changes that follow established procedures.

- **Approval:** Pre-approved (no CAB review needed)
- **Lead Time:** 24 hours minimum
- **Examples:** Profile permission updates, layout changes, report modifications
- **Risk:** Low only

### Normal Change

Changes requiring CAB review and approval before implementation.

- **Approval:** CAB review required
- **Lead Time:** 5 business days minimum
- **Examples:** New Apex code, LWC components, OmniStudio updates, integration changes
- **Risk:** Low, Medium, or High

### Emergency Change

Critical fixes requiring immediate deployment with post-implementation review.

- **Approval:** Emergency CAB (verbal approval, documented post-implementation)
- **Lead Time:** None (immediate)
- **Examples:** Security vulnerabilities, production outages, data integrity issues
- **Risk:** Any level
- **Requirements:** Post-implementation review within 48 hours

## Decision Matrix

| Change Scope | Risk | Has UAT Sign-off | Type |
|-------------|------|-------------------|------|
| Metadata only | Low | Yes | Standard |
| Apex/LWC changes | Medium | Yes | Normal |
| Schema changes | High | Yes | Normal |
| Security fix (P0) | Any | Bypass | Emergency |
| Production outage | Any | Bypass | Emergency |
| Data migration | High/Critical | Yes | Normal |

## Required Fields

| Field | Standard | Normal | Emergency |
|-------|----------|--------|-----------|
| Short Description | Required | Required | Required |
| Description | Required | Required | Required |
| Risk Assessment | Required | Required | Required |
| Rollback Plan | Required | Required | Required |
| Test Plan | Required | Required | Post-impl |
| Implementation Plan | Required | Required | Required |
| Deployment Window | Required | Required | "Immediate" |
| CAB Approval | Pre-approved | Required | Post-impl |
