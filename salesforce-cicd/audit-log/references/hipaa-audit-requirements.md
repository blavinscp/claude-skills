# HIPAA Audit Trail Requirements

## Regulatory Basis

The HIPAA Security Rule (45 CFR 164.312(b)) requires covered entities and business associates to implement audit controls -- hardware, software, and/or procedural mechanisms that record and examine activity in information systems that contain or use electronic protected health information (ePHI).

While the Salesforce CI/CD pipeline does not directly handle ePHI, it deploys code to systems that do (Salesforce Health Cloud). Therefore, pipeline audit trails must meet HIPAA standards to demonstrate that changes to ePHI-handling systems are tracked, authorized, and reviewable.

## What Must Be Logged

### Required Fields

Every pipeline action must record:

| Field | Description | Example |
|-------|-------------|---------|
| **Who** | The authenticated user who initiated the action | `jane.doe@company.com` |
| **What** | The specific action performed | `promote`, `deploy`, `validate` |
| **When** | UTC timestamp in ISO 8601 format | `2026-03-30T14:22:00Z` |
| **Where** | The target environment | `qa`, `uat`, `main` |
| **Outcome** | Whether the action succeeded or failed | `success`, `failed`, `initiated` |

### Required Action Types

All of these pipeline actions must be logged:

1. **Promotion** -- moving code from one environment branch to the next
2. **Validation** -- running deployment validation against a target org
3. **Deployment** -- executing a deployment to a target org
4. **Back-promotion** -- merging higher environment changes back down
5. **Profile cleaning** -- stripping unauthorized profile permissions
6. **CCB submission** -- submitting a change control board request
7. **Rollback** -- reverting a deployment
8. **Hotfix** -- emergency deployment bypassing normal promotion path

### Optional Detail Fields

Additional context that should be logged when available:

- Jira story keys involved in the action
- Bundle identifier
- Merge request URL
- Deployment ID from Salesforce
- Test results summary (pass/fail counts only -- no test data)
- Conflicted file paths (for back-promotes)

## No PHI in Audit Entries

This is the most critical compliance rule for the pipeline audit trail.

### Prohibited Content

Audit entries must **never** contain:

- Patient names, DOBs, SSNs, or any demographic data
- Salesforce record IDs that could link to patient records (e.g., Account IDs, Contact IDs for patients)
- SOQL query results from Health Cloud objects
- Field values from health-related custom objects
- Error messages that might contain patient data from validation failures
- Screenshots or logs from Salesforce orgs that display patient information

### Permitted Content

Audit entries **may** contain:

- Jira story keys (e.g., `US-1234`)
- Environment names (e.g., `qa`, `uat`, `main`)
- Branch names (e.g., `feature/US-1234`, `bundle/B042`)
- Metadata type names (e.g., `ApexClass`, `CustomObject`)
- File paths within the repository
- Deployment IDs (Salesforce async request IDs are safe)
- Aggregate test results (e.g., `42 passed, 0 failed`)
- Git commit SHAs
- Merge request URLs
- Timestamps and user emails

### PHI Incident Response

If PHI is discovered in an audit entry:

1. Immediately notify the compliance officer
2. Do not delete the entry (deletion itself must be audited)
3. Create a new corrective entry noting the incident
4. File a HIPAA incident report per organizational policy
5. Review the pipeline step that generated the entry to prevent recurrence

## Retention Periods

### HIPAA Minimum: 6 Years

HIPAA requires that audit logs be retained for a minimum of **6 years** from the date of creation or the date when the policy was last in effect, whichever is later.

### Organizational Policy

Many healthcare organizations extend retention beyond the HIPAA minimum:

| Retention Tier | Duration | Applies To |
|---------------|----------|------------|
| Active | 0-1 years | Current audit file, actively appended |
| Warm archive | 1-3 years | Read-only, available for quick queries |
| Cold archive | 3-6 years | Compressed, available within 24 hours |
| Extended | 6-10 years | Per organizational policy if required |

### State Law Considerations

Some states require longer retention periods for healthcare records. The pipeline audit trail should follow the longest applicable retention requirement. Common extensions:

- California: 7 years
- New York: 6 years (matches HIPAA)
- Florida: 7 years
- Texas: 7 years

## Structured Format Requirements

### JSON-Lines Format

Audit entries must be stored in JSON-lines (JSONL) format:

- One complete JSON object per line
- No multi-line formatting within entries
- UTF-8 encoding
- No trailing commas

This format was chosen because:

1. **Append-only** -- new entries are appended without reading/rewriting the file
2. **Streamable** -- entries can be processed line-by-line without loading the full file
3. **Compatible** -- JSONL is supported by log aggregation tools (Splunk, ELK, Datadog)
4. **Grep-friendly** -- individual entries can be found with simple text search

### Schema Validation

Every entry must be valid against the audit entry schema. Invalid entries (missing required fields, malformed JSON) must be rejected at write time, not silently written.

### Immutability

Audit entries, once written, must not be modified or deleted. If a correction is needed, append a new entry with:

```json
{
  "timestamp": "2026-03-30T15:00:00Z",
  "user": "compliance@company.com",
  "action": "audit-correction",
  "environment": "qa",
  "status": "success",
  "details": {
    "corrects_timestamp": "2026-03-30T14:22:00Z",
    "reason": "Incorrect environment recorded",
    "original_environment": "uat",
    "corrected_environment": "qa"
  }
}
```
