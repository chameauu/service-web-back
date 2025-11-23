# Codecov Setup Guide

This guide explains how to set up Codecov for the IoTFlow Backend project.

## 🎯 What is Codecov?

Codecov is a code coverage reporting tool that:
- Tracks test coverage over time
- Shows which code is tested and which isn't
- Provides coverage reports on pull requests
- Helps maintain code quality

## 🚀 Setup Steps

### 1. Sign Up for Codecov

1. Go to [codecov.io](https://codecov.io)
2. Sign in with your GitHub account
3. Authorize Codecov to access your repositories

### 2. Add Repository

1. In Codecov dashboard, click "Add new repository"
2. Find and select your `iotflow-backend` repository
3. Codecov will provide you with a token

### 3. Add Codecov Token to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `CODECOV_TOKEN`
5. Value: Paste the token from Codecov
6. Click **Add secret**

### 4. Update README Badge

Replace `YOUR_USERNAME/YOUR_REPO` in the README.md badge with your actual GitHub username and repository name:

```markdown
[![codecov](https://codecov.io/gh/YOUR_USERNAME/iotflow-backend/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/iotflow-backend)
```

Example:
```markdown
[![codecov](https://codecov.io/gh/johndoe/iotflow-backend/branch/main/graph/badge.svg)](https://codecov.io/gh/johndoe/iotflow-backend)
```

## 📊 What Gets Tracked

The CI pipeline automatically:
- Runs tests with coverage on Python 3.10, 3.11, and 3.12
- Generates coverage reports
- Uploads to Codecov
- Comments on pull requests with coverage changes

### Coverage Targets

- **Project Coverage**: 80% minimum
- **Patch Coverage**: 80% minimum (new code in PRs)
- **Threshold**: 2% drop allowed

### Excluded from Coverage

- Test files (`tests/**/*`)
- Simulators (`simulators/**/*`)
- Scripts (`scripts/**/*`)
- Documentation (`docs/**/*`)

## 🔍 Viewing Coverage Reports

### On Codecov Dashboard

1. Go to [codecov.io](https://codecov.io)
2. Select your repository
3. View:
   - Overall coverage percentage
   - Coverage trends over time
   - File-by-file coverage
   - Uncovered lines

### On Pull Requests

Codecov automatically comments on PRs with:
- Coverage change (increase/decrease)
- Files with coverage changes
- Link to detailed report

### Locally

Generate coverage report locally:

```bash
# Run tests with coverage
poetry run pytest tests/ --cov=src --cov-report=html

# Open report in browser
open htmlcov/index.html
```

## 🎨 Coverage Badge

The README includes a Codecov badge that shows:
- Current coverage percentage
- Color-coded status (red/yellow/green)
- Links to detailed coverage report

## 🔧 Configuration

Coverage settings are in `codecov.yml`:

```yaml
coverage:
  status:
    project:
      default:
        target: 80%        # Minimum coverage
        threshold: 2%      # Allowed drop
```

## 📈 Best Practices

1. **Maintain Coverage**: Keep coverage above 80%
2. **Test New Code**: Ensure new features have tests
3. **Review Reports**: Check coverage on PRs before merging
4. **Fix Gaps**: Add tests for uncovered code
5. **Monitor Trends**: Watch for coverage drops over time

## 🐛 Troubleshooting

### Coverage Not Uploading

1. Check GitHub Actions logs
2. Verify `CODECOV_TOKEN` is set correctly
3. Ensure `coverage.xml` is generated
4. Check Codecov dashboard for errors

### Badge Not Showing

1. Update badge URL with correct username/repo
2. Ensure repository is public or Codecov token is valid
3. Wait a few minutes for badge to update

### Low Coverage Warning

1. Run tests locally: `make test-cov`
2. Open `htmlcov/index.html` to see uncovered lines
3. Add tests for uncovered code
4. Re-run tests to verify

## 📚 Resources

- [Codecov Documentation](https://docs.codecov.com/)
- [GitHub Actions Integration](https://docs.codecov.com/docs/github-actions)
- [Coverage Configuration](https://docs.codecov.com/docs/codecov-yaml)

## ✅ Verification

After setup, verify everything works:

1. Push a commit to trigger CI
2. Check GitHub Actions for successful coverage upload
3. Visit Codecov dashboard to see coverage report
4. Verify badge appears in README

---

**Note**: The first coverage report may take a few minutes to appear after setup.
