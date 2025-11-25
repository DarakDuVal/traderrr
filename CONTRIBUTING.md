# Contributing to Traderrr

Thank you for your interest in contributing to Traderrr! This document outlines our development workflow, branching strategy, and contribution guidelines.

## Development Workflow

We follow a **Simplified Git Flow** branching strategy designed to maintain code quality while supporting team growth.

### Branch Structure

```
main              Production-ready code (protected)
  ↑
develop           Integration/staging branch (protected)
  ↑
feature/*         Individual feature branches
bugfix/*          Bug fix branches
hotfix/*          Critical production fixes
```

### Branch Naming Conventions

- **Features**: `feature/short-description` (e.g., `feature/add-rsi-indicator`)
- **Bug Fixes**: `bugfix/issue-name` (e.g., `bugfix/fix-portfolio-calculation`)
- **Hotfixes**: `hotfix/critical-issue` (e.g., `hotfix/api-auth-bypass`)

## Contributing Process

### For New Features or Non-Critical Bug Fixes

1. **Create a feature branch from `develop`:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write clear, descriptive commit messages
   - Follow commit convention: `<type>: description (closes #123)`
   - Examples:
     - `feat: add Stochastic indicator to indicators module (closes #15)`
     - `fix: correct portfolio variance calculation (closes #42)`
     - `docs: update README trading signals section`

3. **Ensure code quality:**
   ```bash
   # Run tests
   make test

   # Format code with Black
   make format

   # Run linting
   make lint

   # Check coverage (must be >= 70%)
   make test-cov
   ```

4. **Push and create a Pull Request:**
   ```bash
   git push origin feature/your-feature-name
   ```
   - Open PR on GitHub targeting `develop` branch
   - Fill in the PR template with:
     - What changes you made
     - Why you made them
     - How to test the changes
   - Link related issues (e.g., "Closes #123")

5. **Code Review:**
   - Address review comments
   - Push updates to the same branch
   - Wait for approval before merging

6. **Merge:**
   - Ensure all checks pass (tests, pylint, coverage)
   - Merge PR using "Squash and merge" or "Create a merge commit"
   - Delete your feature branch after merging

### For Critical Hotfixes (Production Issues)

1. **Create hotfix branch from `main`:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b hotfix/critical-issue-name
   ```

2. **Fix and test thoroughly:**
   - Must pass all tests and quality checks
   - Follow same code quality standards as features

3. **Create PR to `main`:**
   - High priority - requires immediate review
   - After merge, also merge back to `develop`

4. **Tag the release:**
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

## Code Quality Requirements

All contributions must meet these standards:

### Testing
- **Minimum coverage**: 70% across all code
- **All tests must pass**: `make test`
- **New features require tests** covering:
  - Normal operation
  - Edge cases
  - Error conditions

### Code Style
- **Format with Black**: `make format` (line length: 100)
- **Lint with Pylint**: `make lint` (using `.pylintrc`)
- **Type hints**: Encouraged for new code
- **Docstrings**: For public modules, classes, and functions

### Pre-commit Hook

A pre-commit git hook is automatically installed during setup to enforce code formatting:

- **Automatic formatting**: Runs Black on all staged Python files before each commit
- **Re-staging**: Automatically stages reformatted files
- **Line length**: 100 characters (PEP 8 extended)
- **Auto-deployment**: Hooks are installed automatically when you run `make setup` or `make dev-setup`

The hook scripts are located in `scripts/hooks/` and git is configured to use them via `core.hooksPath`.

**Installation**: The hooks are automatically installed during setup, but you can reinstall them manually:

```bash
bash scripts/install-hooks.sh
```

**Bypass** (not recommended):

```bash
git commit --no-verify  # Skips formatting checks
```

### Performance
- No significant performance regressions
- Large data operations should be documented
- Consider caching where appropriate

## Automated Checks

Your code will be automatically checked by:

1. **Pytest** - Unit test execution and coverage analysis
2. **Pylint** - Code quality and style analysis
3. **Black** - Code formatting verification
4. **Mypy** - Type checking (strict mode)

All checks must pass before merging to `develop` or `main`.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/DarakDuVal/traderrr.git
cd traderrr

# Set up development environment
make dev-setup

# Or manually:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
make setup
```

**Note**: Git hooks are automatically installed during setup. Make sure Black is installed (included in `requirements-dev.txt`) before making commits, as the pre-commit hook will run automatically on all staged Python files.

## Useful Make Commands

```bash
make setup          # Install all dependencies
make test           # Run test suite
make test-cov       # Run tests with coverage report
make format         # Auto-format code with Black
make lint           # Run Pylint and Flake8
make health         # Check system health
make docker-build   # Build Docker image
make docker-run     # Run in Docker
```

## Commit Message Guidelines

Use clear, descriptive commit messages that explain **what** and **why**, not just **what**:

**Good:**
```
feat: implement moving average crossover strategy (closes #18)

Add logic to generate buy/sell signals when fast MA crosses slow MA.
Includes threshold parameters for noise filtering.
```

**Bad:**
```
fixed stuff
updated code
```

## Pull Request Guidelines

When creating a PR:

1. **Title**: Should be descriptive and reference the issue
   - ✅ `Feature: Add RSI indicator to signals module (closes #12)`
   - ❌ `fix stuff`

2. **Description**: Include:
   - What problem does this solve?
   - How does it solve it?
   - How should it be tested?
   - Any breaking changes?

3. **Link issues**: Use "Closes #123" to auto-link and close issues

4. **Review**: Be responsive to feedback
   - Respond to comments promptly
   - Push new commits for changes (don't force push during review)

## Questions?

- Check the [README](README.md) for project overview
- Review existing code for patterns and conventions
- Create an issue for discussion before large changes
- Reach out to maintainers for guidance

## Code of Conduct

Be respectful and constructive in all interactions. We're building this together!

---

**Happy contributing!** 🚀
