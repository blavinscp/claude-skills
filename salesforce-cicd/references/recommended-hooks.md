# Recommended Claude Code Hooks

Add these hooks to your project's `.claude/settings.json` to integrate the pipeline with your development workflow.

## Post-Commit: Jira Comment

Automatically post commit links to Jira stories when committing on feature branches.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "pattern": "git commit",
        "command": "bash -c 'BRANCH=$(git branch --show-current); if [[ $BRANCH == feature/US-* ]]; then JIRA_KEY=$(echo $BRANCH | grep -oE \"US-[0-9]+\"); echo \"Post commit to Jira: $JIRA_KEY\"; fi'"
      }
    ]
  }
}
```

## Pre-Push: Quality Gate

Block pushes to bundle branches if quality checks fail.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "pattern": "git push.*bundle/",
        "command": "bash -c 'echo \"Running pre-push quality gate...\"; python3 salesforce-cicd/validate/scripts/validate_deployment.py --target-org qa --format text'"
      }
    ]
  }
}
```

## Permissions

Allow pipeline scripts to execute:

```json
{
  "permissions": {
    "allow": [
      "Bash(sf project deploy:*)",
      "Bash(sf project retrieve:*)",
      "Bash(python3 salesforce-cicd/*/scripts/*)"
    ]
  }
}
```
