# Dependabot Configuration

This document describes the Dependabot setup for the Traderrr project, including automated dependency management and security vulnerability response.

## Overview

Dependabot automatically monitors dependencies for updates and security vulnerabilities, creating pull requests when new versions are available. The Traderrr project uses Dependabot to:

1. **Monitor Python dependencies** (pip) for updates and security issues
2. **Monitor GitHub Actions** for workflow updates
3. **Automatically merge** critical and high-severity security updates
4. **Maintain** code quality by running tests before merging

## Configuration Files

### `.github/dependabot.yml`

The main Dependabot configuration file with the following settings:

#### Python Dependencies (pip)

- **Schedule:** Weekly (Monday at 03:00 UTC)
- **Rebase Strategy:** Automatic rebasing if base branch changes
- **Commit Message Prefix:** `chore(deps):`
- **Assignees:** Project maintainers
- **Labels:** `dependencies`, `automated`
- **Open PR Limit:** Maximum 10 open dependency PRs at once

#### GitHub Actions

- **Schedule:** Weekly (Monday at 04:00 UTC)
- **Open PR Limit:** Maximum 5 open action update PRs at once
- **Commit Message Prefix:** `ci(actions):`
- **Labels:** `ci`, `automated`

## Pull Request Workflow

When Dependabot detects outdated dependencies, it will:

1. **Create a Pull Request** with the dependency update
2. **Trigger CI/CD Checks** automatically:
   - `tests.yml` - Unit and integration tests
   - `code-quality.yml` - Code formatting and linting
   - `pylint.yml` - Python linting
3. **Wait for Review** - PRs can be:
   - Manually reviewed and merged
   - Auto-merged via branch protection rules (if configured)
   - Closed if the update is unwanted

### No Custom Workflow

This project uses GitHub's native Dependabot configuration only. There is no custom auto-merge workflow because:
- ✅ Standard GitHub tokens lack permissions for auto-merge
- ✅ Manual review is safer for dependency updates
- ✅ Branch protection rules can auto-merge if desired
- ✅ Simpler to maintain and debug

## Merge Strategy

### All Updates Require Manual Review

All Dependabot pull requests are created and await review. The process is:

1. **Dependabot creates a PR** with the dependency update
2. **CI/CD checks run** automatically (tests, linting, code quality)
3. **Review the PR:**
   - ✅ If checks pass and update looks safe → Merge
   - ❌ If checks fail → Investigate and fix
   - ⏸️ If uncertain → Request additional review

### Recommendation by Update Type

| Update Type | Example | Recommendation |
|---|---|---|
| **Patch** | 1.0.0 → 1.0.1 | Safe, merge if CI passes |
| **Minor** | 1.0.0 → 1.1.0 | Usually safe, review changelog |
| **Major** | 1.0.0 → 2.0.0 | Review carefully, check breaking changes |
| **Security** | Any CVE fix | Urgent, merge after CI passes |

## Security Update Handling

Dependabot automatically detects security vulnerabilities in your dependencies. Security updates are handled the same way as regular updates:

1. **Dependabot creates a PR** with the security fix
2. **Labels it** with `dependencies` and `automated`
3. **CI/CD checks run** to verify the fix doesn't break anything
4. **Review and merge** the PR

### Security Priority

Security updates should be treated with higher priority:
- 🚨 **Critical/High CVEs** - Merge ASAP after CI passes
- ⚠️ **Medium CVEs** - Review and merge within a few days
- 📋 **Low CVEs** - Review alongside other updates

**Note:** GitHub's Security tab will alert you to vulnerabilities. Check it regularly for urgent issues that may require immediate action.

## Managing Dependabot PRs

### Skipping an Update

To skip a specific dependency update, add a comment to the PR:

```
@dependabot ignore this major version
```

### Requesting an Earlier Update Check

To request an immediate check for updates:

```
@dependabot rebase
```

Or for a fresh update attempt:

```
@dependabot recreate
```

### Disabling Updates for a Dependency

Add to `.github/dependabot.yml`:

```yaml
ignore:
  - dependency-name: "problematic-package"
    versions: ["*"]
```

### Pausing Dependabot

To temporarily pause Dependabot, add a comment to any Dependabot PR:

```
@dependabot pause
```

To resume:

```
@dependabot resume
```

## GitHub Tokens & Permissions

The auto-merge workflow requires the following permissions:

- `pull-requests: write` - To approve and merge PRs
- `contents: write` - To push changes
- `statuses: write` - To check status of commits

These permissions are set in the workflow file and require no additional configuration.

## Best Practices

### 1. Monitor Security Alerts
- Check GitHub's Security tab regularly
- Review Dependabot alerts for patterns of vulnerability
- Consider disabling packages with recurring issues

### 2. Review Major Updates
- Don't auto-merge major version updates (handled by default)
- Test major updates thoroughly in a local environment first
- Check migration guides for breaking changes

### 3. Keep Tests Current
- Ensure test suite is comprehensive and maintainable
- Update tests when dependencies have API changes
- Mock external services to reduce test brittleness

### 4. Manage PR Volume
- Monitor the number of open Dependabot PRs
- Adjust merge strategies if PRs accumulate faster than reviews
- Use the `ignore` feature for problematic dependencies

### 5. Document Dependency Decisions
- Add comments to requirements files for critical dependencies
- Document why certain packages are pinned
- Track known compatibility issues

## Troubleshooting

### Auto-Merge Not Working

**Issue:** Dependabot PRs aren't being auto-merged

**Solutions:**
1. Check branch protection rules don't require additional reviews
2. Verify workflow has `GITHUB_TOKEN` with proper permissions
3. Ensure CI/CD checks are completing successfully
4. Check that the PR base branch is `main` or `develop`

### Too Many PRs Opening

**Issue:** Dependabot is opening too many PRs at once

**Solutions:**
1. Reduce `open-pull-requests-limit` in `.github/dependabot.yml`
2. Increase the interval (e.g., from `weekly` to `monthly`)
3. Add more dependencies to the `ignore` list

### Merge Conflicts

**Issue:** Dependabot PRs have merge conflicts

**Solutions:**
1. The `rebase-strategy: auto` should handle most conflicts
2. Comment `@dependabot rebase` to retry
3. If conflicts persist, require manual resolution

### Tests Failing

**Issue:** Dependency updates cause test failures

**Solutions:**
1. Review the test output in the CI logs
2. Update tests if the dependency API changed
3. Pin the problematic dependency and file a separate issue
4. Contact the dependency maintainer if it's a regression

## Related Documentation

- [GitHub Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [Dependabot Configuration Options](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-dependency-updates)
- [Dependabot Security Alerts](https://docs.github.com/en/code-security/dependabot/dependabot-alerts)
- Project's [SECURITY.md](./SECURITY.md) - Security vulnerability reporting

## Maintenance

### Regular Reviews

Every month, review:
- Number and frequency of Dependabot PRs
- CI/CD success rate on Dependabot updates
- Any packages with recurring issues
- Update schedule against project needs

### Annual Audit

Yearly, consider:
- Reviewing the `ignore` list for outdated entries
- Updating dependency strategies based on project maturity
- Assessing major version updates scheduled for the year
- Planning for critical security updates

---

**Last Updated:** 2025-11-25

For questions or issues, contact the project maintainers or open an issue on GitHub.
