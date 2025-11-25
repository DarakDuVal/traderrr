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

## Automated Workflow

### `.github/workflows/dependabot-auto-merge.yml`

This workflow handles automatic merging of Dependabot PRs with the following logic:

#### Step 1: Dependabot Metadata Fetch
- Extracts Dependabot PR information using the official metadata action
- Identifies dependency names, versions, and update types

#### Step 2: Auto-Approval
- Automatically approves all Dependabot PRs
- Requires only `pull-requests: write` permission
- Safe because CI/CD checks must pass before merge

#### Step 3: Smart Version-Based Merging
- **Patch Updates** (e.g., 2.1.0 → 2.1.1): Auto-merge if all CI/CD checks pass
- **Minor Updates** (e.g., 2.1.0 → 2.2.0): Auto-merge if all CI/CD checks pass
- **Major Updates** (e.g., 1.0.0 → 2.0.0): Requires manual review with warning comment

#### Step 4: CI/CD Checks
GitHub's native checks automatically verify before merge:
- `tests.yml` - Unit and integration tests
- `code-quality.yml` - Code formatting and linting
- `pylint.yml` - Python linting

Only PRs that pass **all checks** will be merged by auto-merge.

## Merge Strategy

### Auto-Merge (Automatic)

Pull requests from Dependabot will be **automatically approved and merged** if:

1. ✅ Update type is **patch** or **minor** version (semver)
2. ✅ All CI/CD checks pass (tests, linting, code quality)
3. ✅ No merge conflicts

**Examples:**
- `lodash` 4.17.20 → 4.17.21 (patch) ✅ Auto-merge
- `flask` 2.0.0 → 2.1.0 (minor) ✅ Auto-merge
- `django` 3.2 → 4.0 (major) ⏸️ Requires manual review

### Manual Review Required

The following scenarios require manual review:

- 🔴 **Major version updates** (e.g., 1.0.0 → 2.0.0) - Workflow adds warning comment
- 🔴 **Breaking changes** - Requires manual investigation
- 🔴 **Tests fail** - CI pipeline must pass for auto-merge to proceed
- 🔴 **Merge conflicts** - Cannot auto-merge if conflicts exist

## Security Update Handling

Security vulnerabilities are handled the same way as regular dependency updates:

### All Security Updates

1. **Automatic Approval:** Dependabot PR is approved automatically
2. **Version Check:**
   - Patch/minor security fixes → Auto-merge after CI passes ✅
   - Major version security fixes → Manual review required ⏸️
3. **CI/CD Validation:** Must pass all tests before merge
4. **Labels:** PR is labeled with `dependencies` and `automated`

### Why This Approach

- **Simplicity:** Single process for all updates reduces confusion
- **Safety:** All updates require CI/CD checks to pass
- **Efficiency:** Security patches merge quickly while major changes get review
- **Reliability:** Uses GitHub's native auto-merge instead of complex automation

**Note:** Security alerts from GitHub's vulnerability database are separate and may require urgent attention regardless of version type.

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
