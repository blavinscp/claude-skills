# Audit Retention Policy

## Retention Schedule

### Primary Retention: 6 Years

All pipeline audit entries must be retained for a minimum of **6 years** from the date of creation. This aligns with HIPAA Security Rule requirements (45 CFR 164.530(j)) for documentation retention.

### Retention Tiers

| Tier | Age | Storage | Access Time | Format |
|------|-----|---------|-------------|--------|
| **Active** | 0-12 months | `pipeline-audit/audit.jsonl` in repository | Immediate | JSONL (uncompressed) |
| **Warm Archive** | 1-3 years | Separate archive branch or artifact storage | < 1 hour | JSONL (gzip compressed) |
| **Cold Archive** | 3-6 years | Cloud object storage (S3, GCS, Azure Blob) | < 24 hours | JSONL (gzip compressed) |
| **Disposal** | 6+ years | Securely deleted per destruction policy | N/A | N/A |

### Annual Rotation

At the start of each calendar year:

1. The active `audit.jsonl` file is renamed to `audit-{YEAR}.jsonl`
2. A new empty `audit.jsonl` file is created for the current year
3. Files older than 12 months are compressed and moved to warm archive
4. Files older than 3 years are moved to cold archive
5. Files older than 6 years are reviewed for disposal eligibility

## Archival Process

### Step 1: Compress

```bash
gzip -k pipeline-audit/audit-2024.jsonl
```

Retain both the compressed and uncompressed versions during the transition period (30 days). After verification, remove the uncompressed version.

### Step 2: Verify Integrity

Before archiving, generate and store a SHA-256 checksum:

```bash
sha256sum pipeline-audit/audit-2024.jsonl.gz > pipeline-audit/audit-2024.jsonl.gz.sha256
```

After moving to archive storage, verify the checksum matches.

### Step 3: Move to Archive

Transfer the compressed file and its checksum to the appropriate archive tier. Document the transfer in a manifest file:

```json
{
  "file": "audit-2024.jsonl.gz",
  "checksum": "sha256:abc123...",
  "entries": 4827,
  "date_range": "2024-01-01 to 2024-12-31",
  "archived_date": "2025-01-15",
  "archive_location": "s3://company-audit-archive/pipeline/2024/",
  "retention_expires": "2031-01-15"
}
```

### Step 4: Verify Archive Accessibility

After archiving, verify the file can be retrieved and decompressed:

1. Download from archive storage
2. Verify SHA-256 checksum
3. Decompress and confirm valid JSONL
4. Spot-check 5 random entries for completeness

## Access Controls

### Who Can Read Audit Logs

| Role | Active Logs | Warm Archive | Cold Archive |
|------|------------|--------------|--------------|
| Pipeline agents (CI/CD) | Read + Append | No access | No access |
| DevOps engineers | Read only | Read only | Request access |
| Compliance officers | Read only | Read only | Read only |
| Security team | Read only | Read only | Read only |
| Auditors (external) | Via compliance officer | Via compliance officer | Via compliance officer |

### Who Can Modify Audit Logs

**No one.** Audit logs are append-only. The only permitted operations are:

- **Append** -- adding new entries (pipeline agents only)
- **Read** -- querying existing entries (authorized roles)
- **Archive** -- compressing and moving to archive tier (DevOps with compliance approval)
- **Dispose** -- deleting entries past retention period (compliance officer only, with documented approval)

### Prohibited Operations

- Editing existing entries
- Deleting individual entries
- Truncating the audit file
- Moving entries between files
- Changing timestamps or user fields

Any attempt to perform these operations should trigger a security alert.

## Audit Log Backup Strategy

### Repository Backups

The active `audit.jsonl` file lives in the repository and is covered by standard Git backups. However, Git is not sufficient as the sole backup because:

- Git does not guarantee point-in-time recovery
- Large JSONL files may be excluded from Git LFS
- Repository deletion would destroy the audit trail

### Additional Backup Requirements

| Backup Type | Frequency | Retention | Location |
|-------------|-----------|-----------|----------|
| Daily snapshot | Every 24 hours | 30 days | Cloud object storage |
| Weekly full backup | Every 7 days | 90 days | Separate cloud region |
| Monthly archive backup | Every 30 days | 6 years | Separate cloud account |

### Backup Verification

- **Weekly:** Automated checksum verification of latest backup
- **Monthly:** Manual restore test of a random backup to confirm recoverability
- **Quarterly:** Full disaster recovery drill including audit log restoration

### Disaster Recovery

Recovery Time Objective (RTO): 4 hours for active logs, 24 hours for archived logs.
Recovery Point Objective (RPO): 24 hours maximum data loss.

In the event of audit log loss:

1. Restore from most recent backup
2. Cross-reference Git history to identify any entries that may be missing
3. Log the incident itself as an audit entry once the system is restored
4. Notify the compliance officer within 24 hours
5. File an incident report documenting the gap in the audit trail

## Compliance Review Schedule

### Monthly Review

**Owner:** DevOps lead
**Duration:** 30 minutes

Checklist:
- [ ] Verify `audit.jsonl` is being actively written (check latest entry timestamp)
- [ ] Spot-check 10 random entries for completeness (all required fields present)
- [ ] Scan 10 random entries for PHI violations (no patient data, no record IDs)
- [ ] Verify file permissions have not changed
- [ ] Confirm daily backups are running

### Quarterly Review

**Owner:** Compliance officer + DevOps lead
**Duration:** 2 hours

Checklist:
- [ ] Complete monthly checklist
- [ ] Review all unique action types logged -- are any pipeline actions missing?
- [ ] Verify backup restore procedure works (restore and validate a random backup)
- [ ] Review access control list -- remove departed employees
- [ ] Check archive tier files for integrity (verify checksums)
- [ ] Generate summary report: total entries, entries by action type, entries by environment

### Annual Review

**Owner:** Compliance officer + Security team + DevOps lead
**Duration:** 4 hours

Checklist:
- [ ] Complete quarterly checklist
- [ ] Review retention policy against current HIPAA guidance and state laws
- [ ] Identify and dispose of entries past the retention period (with documented approval)
- [ ] Verify cold archive accessibility (retrieve and validate a 3+ year old file)
- [ ] Update this retention policy document if regulations have changed
- [ ] Conduct tabletop disaster recovery exercise for audit log loss scenario
- [ ] Document any policy changes and distribute to stakeholders
