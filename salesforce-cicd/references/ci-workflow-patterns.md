# CI/CD Workflow Patterns

Reference patterns from open source Salesforce CI/CD implementations, adapted for both GitHub Actions and GitLab CI.

## GitHub Actions Patterns (from octoforce-actions)

### Sandbox Creation per Issue

```yaml
name: Create Dev Sandbox
on:
  issues:
    types: [opened]

jobs:
  create-sandbox:
    if: contains(github.event.issue.labels.*.name, 'dev-sandbox')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Authenticate
        run: sf org login sfdx-url --sfdx-url-file auth/devhub.txt --alias devhub
      - name: Create Sandbox
        run: |
          sf org create sandbox \
            --definition-file config/dev-sandbox-def.json \
            --alias dev-${{ github.event.issue.number }} \
            --target-org devhub \
            --wait 30
```

### PR-Triggered UAT Deployment

```yaml
name: Deploy to UAT
on:
  pull_request:
    branches: [uat]
    types: [opened, synchronize]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install SGD
        run: sf plugins install sfdx-git-delta
      - name: Generate Delta
        run: |
          sf sgd source delta \
            --from origin/uat \
            --to HEAD \
            --output-dir delta/ \
            --generate-delta
      - name: Validate
        run: |
          sf project deploy validate \
            --manifest delta/package/package.xml \
            --target-org uat \
            --test-level RunLocalTests
```

### Production Deployment with Approval

```yaml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production  # Requires approval in GitHub settings
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for SGD
      - name: Generate Delta
        run: |
          sf sgd source delta \
            --from HEAD~1 \
            --to HEAD \
            --output-dir delta/ \
            --generate-delta
      - name: Deploy
        run: |
          sf project deploy start \
            --manifest delta/package/package.xml \
            --target-org production \
            --test-level RunLocalTests
```

## GitLab CI Equivalents

### Delta Validation on MR

```yaml
validate-mr:
  stage: validate
  image: salesforce/cli:latest
  before_script:
    - sf plugins install sfdx-git-delta
    - sf org login sfdx-url --sfdx-url-file $AUTH_FILE --alias target
  script:
    - sf sgd source delta --from origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME --to HEAD --output-dir delta/ --generate-delta
    - sf project deploy validate --manifest delta/package/package.xml --target-org target --test-level RunLocalTests
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### Production Deployment

```yaml
deploy-production:
  stage: deploy
  image: salesforce/cli:latest
  before_script:
    - sf org login sfdx-url --sfdx-url-file $PROD_AUTH --alias production
  script:
    - sf sgd source delta --from HEAD~1 --to HEAD --output-dir delta/ --generate-delta
    - sf project deploy start --manifest delta/package/package.xml --target-org production --test-level RunLocalTests
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
  when: manual  # Requires manual approval
  environment:
    name: production
```

### OmniStudio Sequential Deploy

```yaml
deploy-omnistudio:
  stage: deploy
  image: node:18
  before_script:
    - npm install --global vlocity
  script:
    - vlocity -sfdx.username $TARGET_ORG -job deploy.yaml packDeploy
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      changes:
        - "force-app/main/default/omniDataTransforms/**"
        - "force-app/main/default/omniProcesses/**"
        - "force-app/main/default/omniUiCards/**"
```

## Combining CI with Agent Orchestration

The CI pipeline handles automated stages (lint, test, validate). Agents handle complex orchestration:

```
CI Pipeline (automated):
  push -> lint -> unit-test -> validate-delta

Agent Orchestration (on demand):
  /promote -> bundle -> merge -> clean -> validate -> MR
  /deploy -> quick-deploy -> back-promote -> audit-log
```

**Pattern:** Use CI for fast feedback loops on every push. Use agents for multi-step workflows that require decision-making, conflict resolution, or human approval.

## sfdx-hardis Integration

sfdx-hardis can generate these CI configs automatically:

```bash
# Generate GitLab CI config from project analysis
sf hardis:project:deploy:smart --check
```

It also provides:
- Grafana dashboards for org monitoring
- Automated daily metadata backup
- AI-enhanced documentation generation
- Multi-platform support (GitHub, GitLab, Bitbucket, Azure)
