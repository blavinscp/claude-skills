# CCB Approval Matrix

## Approval Levels

| Risk Level | Impact | Required Approvals |
|-----------|--------|-------------------|
| Low | Low (3) | Team Lead + Release Manager |
| Medium | Medium (2) | Team Lead + Release Manager + IT Manager |
| High | Medium-High (1-2) | Team Lead + Release Manager + IT Director + HIPAA Officer |
| Critical | High (1) | All above + CTO/CIO approval |

## HIPAA-Specific Requirements

For changes affecting PHI-accessible systems:

| Change Scope | Additional Approvals |
|-------------|---------------------|
| PHI field access changes | HIPAA Privacy Officer |
| User permission changes (PHI objects) | HIPAA Privacy Officer + Compliance |
| Integration endpoint changes | Security Team + HIPAA Officer |
| Audit logging changes | Compliance Team |
| Data migration involving PHI | HIPAA Privacy Officer + Legal |

## Environment-Specific Rules

| Environment | CCB Required? | Notes |
|------------|---------------|-------|
| Dev1 | No | Development — no CCB needed |
| QA | No | Testing — no CCB needed |
| UAT | Optional | Required for schema changes |
| Production | Always | Every deployment needs CCB approval |

## Timeline

```
Standard Changes:
  Submit ─── (24h) ─── Auto-approved ─── Deploy

Normal Changes:
  Submit ─── (5 days) ─── CAB Review ─── Approved/Rejected ─── Deploy

Emergency Changes:
  Verbal Approval ─── Deploy ─── (48h) ─── Post-Implementation Review
```

## Escalation Path

If a normal change is blocked at CAB:
1. Address feedback from CAB
2. Resubmit with updated risk assessment
3. If still blocked, escalate to IT Director
4. Final escalation: CTO/CIO override (documented)

## Blackout Periods

No production deployments during:
- Month-end close (last 3 business days of month)
- Quarter-end close (last 5 business days of quarter)
- Major regulatory audit periods (as announced)
- Holiday freezes (Thanksgiving week, Dec 20 - Jan 2)

Exceptions: Emergency changes only, with CTO approval.
