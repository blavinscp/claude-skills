# MCP Server Requirements

## Required: SalesforceDX MCP

Provides org authentication, SOQL queries, and metadata interaction.

```bash
claude mcp add-json "SalesforceDX" '{
  "command": "npx",
  "args": ["-y", "@salesforce/mcp", "--orgs", "<org-alias>", "--toolsets", "all"],
  "type": "stdio"
}'
```

Configure one instance per org:
- `sf-corehc-dev1` — Development
- `sf-corehc-qa` — QA
- `sf-corehc-uat` — UAT
- `production` — Production (read-only recommended)

## Required: GitLab MCP

Provides branch operations, merge request CRUD, comments, and pipeline status.

```bash
claude mcp add-json "GitLab" '{
  "command": "npx",
  "args": ["-y", "@gitlab/mcp-server"],
  "type": "stdio",
  "env": {
    "GITLAB_TOKEN": "<your-token>",
    "GITLAB_URL": "<your-gitlab-url>"
  }
}'
```

### Required Scopes

- `api` — Full API access for MR creation/merge
- `read_repository` — Branch listing and comparison
- `write_repository` — Branch creation and deletion

## Optional: Atlassian MCP

Enhances Jira integration for release management workflows.

```bash
claude mcp add-json "Atlassian" '{
  "command": "npx",
  "args": ["-y", "@anthropic/atlassian-mcp-server"],
  "type": "stdio",
  "env": {
    "JIRA_URL": "<your-jira-url>",
    "JIRA_EMAIL": "<your-email>",
    "JIRA_API_TOKEN": "<your-token>"
  }
}'
```

Used by `@release-mgr` and `@scrum-ops` agents for:
- Story status transitions
- Sprint analytics queries
- Release coordination comments
