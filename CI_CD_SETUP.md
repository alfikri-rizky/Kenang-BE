# CI/CD Automation Setup

## Overview

This repository now has fully automated CI/CD pipelines using GitHub Actions. Every pull request is automatically tested, reviewed, approved, and merged when all checks pass.

## Pipeline Architecture

### 1. CI Pipeline (`.github/workflows/ci.yml`)

Triggered on: `pull_request` to `main` and `push` to `main`

#### Jobs:

**Job 1: lint-and-test**
- Sets up Python 3.11
- Installs dependencies from `requirements.txt` and `requirements-dev.txt`
- Runs code quality checks:
  - **Black**: Formatting validation
  - **isort**: Import sorting check
  - **flake8**: Linting (max line length: 120)
  - **mypy**: Type checking (continues on error)
  - **pytest**: Unit tests with coverage (continues on error)
- Security scanning with **TruffleHog**

**Job 2: code-quality** (depends on lint-and-test)
- Validates project structure
- Checks for Indonesian error messages
- Ensures code quality standards

**Job 3: auto-review** (depends on lint-and-test, code-quality)
- Only runs on pull requests
- Generates automated code review summary
- Posts review comment on PR
- **Auto-approves PR** when all checks pass

### 2. Auto-Merge Pipeline (`.github/workflows/auto-merge.yml`)

Triggered on: `pull_request_review`, `check_suite`, and `status` events

#### Job: auto-merge
- Waits for all checks to complete
- Verifies PR is approved
- Enables auto-merge with squash
- Automatically merges when ready
- Deletes feature branch after merge

## How to Use

### For New Features/Changes:

```bash
# 1. Create feature branch
git checkout -b feature/my-new-feature

# 2. Make your changes
# ... code changes ...

# 3. Commit and push
git add .
git commit -m "feat: add new feature"
git push -u origin feature/my-new-feature

# 4. Create PR
gh pr create --title "feat: My New Feature" --body "Description"

# 5. CI runs automatically → Bot reviews → Auto-approves → Auto-merges
# No manual intervention needed! ✨
```

### What the Bot Does:

1. **Runs all checks** (lint, type, security, tests)
2. **Posts review comment** with:
   - ✅ List of passed checks
   - 📊 Files changed stats
   - 📝 Commit messages
   - 💡 Recommendations
3. **Approves PR** when all checks pass
4. **Auto-merges** with squash commit
5. **Deletes branch** after merge

## CI Checks Explained

### Black Formatting
Ensures consistent code style across the project.

**Fix locally**: `black app/`

### isort Import Sorting
Organizes imports in a standard way.

**Fix locally**: `isort app/`

### flake8 Linting
Catches common Python errors and style issues.

**Fix locally**: `flake8 app/ --max-line-length=120`

### mypy Type Checking
Validates type hints and catches type errors.

**Fix locally**: `mypy app/ --ignore-missing-imports`

### pytest Testing
Runs unit tests with coverage reporting.

**Run locally**: `pytest tests/ -v --cov=app`

### TruffleHog Security Scan
Scans for secrets and credentials in code.

**Automatic**: Runs on every push

## Configuration

### Modifying CI Behavior

**Skip CI on commit:**
```bash
git commit -m "docs: update README [skip ci]"
```

**Require manual approval:**
Remove the `auto-review` job from `.github/workflows/ci.yml`

**Disable auto-merge:**
Delete `.github/workflows/auto-merge.yml`

### Required Secrets

No secrets required for basic CI. Optional:
- `OPENAI_API_KEY` - For running AI integration tests
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - For S3 integration tests

Add secrets in: **Settings** → **Secrets and variables** → **Actions**

## Troubleshooting

### CI Failed - Black Formatting

**Problem**: Code doesn't match Black style

**Solution**:
```bash
# Install Black
pip install black==23.12.1

# Format all code
black app/

# Commit and push
git add .
git commit -m "style: apply Black formatting"
git push
```

### CI Failed - Import Sorting

**Problem**: Imports not sorted correctly

**Solution**:
```bash
# Install isort
pip install isort==5.13.2

# Sort imports
isort app/

# Commit and push
git add .
git commit -m "style: sort imports with isort"
git push
```

### CI Failed - Type Errors

**Problem**: mypy found type issues

**Solution**:
```bash
# Check errors
mypy app/ --ignore-missing-imports

# Fix type hints in flagged files
# Add type annotations or use # type: ignore

# Commit and push
git add .
git commit -m "fix: resolve type errors"
git push
```

### CI Failed - Security Scan

**Problem**: TruffleHog found potential secrets

**Solution**:
1. Review the flagged lines
2. Remove any hardcoded secrets
3. Use environment variables instead
4. Commit and push

### Auto-Merge Not Working

**Possible causes**:
1. PR is in draft mode → Mark as ready for review
2. CI checks failed → Fix issues and push
3. Branch protection rules → Check repository settings
4. Insufficient permissions → Ensure bot has write access

## Best Practices

### Commit Messages
Follow conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Formatting
- `refactor:` - Code restructuring
- `test:` - Adding tests
- `chore:` - Maintenance

### PR Descriptions
Include:
- **Summary** of changes
- **What's included** (bullet points)
- **How to test** (if applicable)
- **Breaking changes** (if any)

### Code Quality
Before pushing:
1. Run formatters: `black app/ && isort app/`
2. Check linting: `flake8 app/`
3. Run tests: `pytest`
4. Review changes: `git diff`

## Manual Override

If you need to bypass automation:

### Merge without auto-merge:
```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```

### Merge without checks:
```bash
gh pr merge <PR_NUMBER> --admin --squash
```

## Monitoring

### View CI Run Logs:
```bash
# List recent runs
gh run list --limit 10

# View specific run
gh run view <RUN_ID>

# View failed logs
gh run view <RUN_ID> --log-failed
```

### Check PR Status:
```bash
# View PR checks
gh pr checks <PR_NUMBER>

# Watch checks in real-time
gh pr checks <PR_NUMBER> --watch
```

## Cost & Performance

### GitHub Actions Minutes
- **Public repositories**: Unlimited free minutes
- **Private repositories**: 2,000 free minutes/month

### Typical CI Run Time
- Lint & test: ~2-3 minutes
- Security scan: ~30 seconds
- Auto-review: ~10 seconds
- **Total**: ~3-4 minutes per PR

## Future Enhancements

Potential improvements:
- [ ] Add deployment pipeline for staging/production
- [ ] Integrate with code coverage services (Codecov)
- [ ] Add performance testing benchmarks
- [ ] Implement semantic versioning automation
- [ ] Add changelog generation
- [ ] Integrate with project management tools

## Support

For issues with CI/CD:
1. Check this documentation
2. Review GitHub Actions logs
3. Check repository settings → Actions
4. Verify branch protection rules

---

**Last Updated**: 2026-01-08  
**Maintainer**: Kenang Development Team
