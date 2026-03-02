# Issue Guidelines for Traderrr

Welcome! These guidelines help us maintain clarity, context, and direction for all issues.

## Quick Summary

**Good issues have:**
- ✅ Clear title (what, not vague)
- ✅ Specific problem or request (context)
- ✅ Relevant details (environment, steps to reproduce)
- ✅ Expected vs. actual behavior (clarity)

**Avoid:**
- ❌ Vague titles ("Help!" "Broken")
- ❌ No context (system info, reproduction steps)
- ❌ Multiple unrelated problems in one issue
- ❌ Screenshots only (include text description too)

---

## Issue Types & Templates

### 🐛 Bug Report
**When**: Something isn't working as expected
- Clear title: `[BUG] Signals not updating when market data missing`
- What's happening + expected behavior
- Steps to reproduce (3-5 concrete steps)
- Environment: OS, Python version, branch
- Logs or error messages if available

**Example**:
```
Title: [BUG] ValueError when portfolio has zero positions

What's happening?
The API returns a 500 error when calling /api/v1/portfolio-performance
with an empty portfolio.

Expected behavior
Should return 200 with empty array or meaningful message.

Steps to reproduce
1. Create new account
2. Don't add any positions
3. Call GET /api/v1/portfolio-performance
```

---

### 💡 Feature Request
**When**: You want a new capability or improvement
- Clear title: `[FEATURE] Alert system for price targets`
- Problem this solves
- Proposed solution
- Example usage (if technical)
- Related issues

**Example**:
```
Title: [FEATURE] Support multiple API keys per user

What problem does this solve?
Currently users can only have one API key. This makes it hard to
rotate keys without downtime, or use different keys per service.

Proposed solution
Allow users to create multiple keys and deactivate old ones.
Store in API_keys table with username, created_date, last_used, is_active.

Priority: Medium
Effort: Small (2-3 hours)
```

---

### 📚 Documentation
**When**: Docs are unclear, missing, or outdated
- Clear title: `[DOCS] Add JWT configuration examples`
- What needs updating
- Current state (what's there)
- Suggested changes (what should be added)
- Who needs this (developers/users/both)

**Example**:
```
Title: [DOCS] Database schema documentation missing

What needs updating?
The database tables (daily_data, intraday_data, signal_history)
have no documentation describing their purpose or relationship.

Current state
Only code comments in config/database.py

Suggested changes
Add docs/DATABASE_SCHEMA.md with:
- Entity relationship diagram
- Each table's purpose
- Field descriptions
- Example queries

Impact: Developers onboarding or extending the schema
```

---

### 🔧 Maintenance
**When**: Technical debt, refactoring, performance, code quality
- Clear title: `[MAINT] Refactor data_manager.py - reduce duplication`
- What needs attention
- Why it matters
- Proposed approach
- Affected areas

**Example**:
```
Title: [MAINT] Remove unused yfinance mock code in tests

What needs attention?
YFinanceMockHelper class is defined but never used in tests.
All tests use SampleDataGenerator instead.

Why does it matter?
Code maintenance - reduces cognitive load and potential confusion.

Proposed approach
Remove YFinanceMockHelper class from tests/__init__.py
Keep SampleDataGenerator (actively used)

Severity: Nice-to-have (no functional impact)
```

---

### ❓ Other
**When**: Something doesn't fit above categories
- Clear title describing the topic
- What this is about
- Context and background
- What action is needed

---

## Writing a Good Title

| ❌ Bad | ✅ Good |
|--------|---------|
| Help! | [BUG] API returns 500 on missing market data |
| Broken | [FEATURE] Support multiple API keys per user |
| Question | [DOCS] Add deployment troubleshooting guide |
| Fix thing | [MAINT] Refactor signal generation to reduce duplication |

**Formula**: `[TYPE] Specific issue or request`

---

## Providing Context

For bugs, always include:
```
1. What you were doing
2. What happened
3. What should happen instead
4. Your environment
5. Any error messages or logs
```

For features:
```
1. The problem you're trying to solve
2. How you'd like to solve it
3. Example of how it would be used
4. Why this matters
```

---

## Labels

Issues are auto-labeled by template:
- `bug` - Something isn't working
- `enhancement` - New feature or improvement
- `documentation` - Docs need work
- `maintenance` - Technical debt or refactoring
- Additional labels added by maintainers:
  - `priority: high/medium/low`
  - `effort: small/medium/large`
  - `blocked` - Depends on other issues
  - `help wanted` - Open for community contributions
  - `good first issue` - Great for newcomers

---

## Response Time

Issues receive attention in this order:
1. **Critical bugs** (system broken, data loss risk) - < 24 hours
2. **Security issues** - Via private advisory, not GitHub issues
3. **High-priority features** (aligned with roadmap) - < 1 week
4. **Bugs & maintenance** - < 2 weeks
5. **Documentation** - < 1 month
6. **Lower-priority features** - Reviewed monthly

---

## Before Creating an Issue

- [ ] Check [existing issues](../../issues) (search, review closed issues)
- [ ] Check [Discussions](../../discussions) (if it's a question)
- [ ] Check [documentation](../../tree/develop/docs)
- [ ] Try the latest code on `develop` branch
- [ ] Include minimal reproducible example if possible

---

## Security Issues

**Do not** create public GitHub issues for security vulnerabilities.

Instead, use [GitHub Security Advisory](../../security/advisories):
- Click "Report a vulnerability"
- Describe the issue confidentially
- We'll respond within 24-48 hours

See [SECURITY.md](../SECURITY.md) for more details.

---

## Tips for Success

### 🎯 Be Specific
```
BAD:  "Signals are wrong"
GOOD: "BUY signals generated in downtrend when RSI > 70 (should be RSI < 30)"
```

### 📋 Show Your Work
```
BAD:  No reproduction steps
GOOD:
1. Load 1 year AAPL data
2. Set confidence threshold to 0.8
3. Run signal generator
4. Compare to expected output
```

### 🔍 Attach Evidence
- Error messages (full stack trace)
- Screenshots (with explanation)
- Code snippets (if relevant)
- Data samples (if applicable)

### 🔗 Link Related Issues
```
Relates to #123
Depends on #456
Fixes #789
```

### ⏱️ Set Expectations
```
Blocking us? Yes - API returns 500 in production
Can work around it? Yes - using local data instead
Urgency? High - affects 3 active users
```

---

## Examples

### ✅ Well-Written Bug Report
```
Title: [BUG] Signal history endpoint returns 500 when querying 2+ year date range

What's happening?
When calling GET /api/signal-history?start=2022-01-01&end=2024-11-27,
the API returns a 500 Internal Server Error.

Expected behavior
Should return 200 with an array of signal records, or 400 if request is invalid.

Steps to reproduce
1. Start API: cd backend && uvicorn app.main:app --reload
2. Create portfolio with 2+ years of signal history
3. Run: curl "http://localhost:8000/api/v1/signal-history?start=2022-01-01&end=2024-11-27" \
        -H "Authorization: Bearer <token>"
4. See 500 error

Environment
- OS: Windows 11
- Python: 3.11.5
- Branch: develop
- Commit: fd0bb63

Logs
```
Traceback (most recent call last):
  File "app/api/routes.py", line 245, in get_signal_history
    results = query_signals(start_date, end_date)
  File "app/core/signal_generator.py", line 89, in query_signals
    return results[:limit]
IndexError: string index out of range
```
```

Related: #215
Is this blocking you? Yes - production issue affecting 2 users
```

### ✅ Well-Written Feature Request
```
Title: [FEATURE] Export portfolio data to CSV

What problem does this solve?
Users want to analyze their portfolio data in Excel/spreadsheets.
Currently they can only view through API or web dashboard.

Proposed solution
Add endpoint: GET /api/v1/portfolio/export?format=csv
Returns CSV file with columns: ticker, shares, entry_price, current_price,
gain_loss, gain_loss_pct, last_updated

Example usage
```python
response = client.get(
    '/api/v1/portfolio/export?format=csv',
    headers={'Authorization': 'Bearer <token>'}
)
df = pd.read_csv(StringIO(response.text))
```

Alternatives considered
- JSON export (less useful for Excel)
- Excel format (requires additional dependency)

Priority: Medium
Effort: Small (4-6 hours)
Related: #89 (similar request for signals export)
```

### ✅ Well-Written Documentation Issue
```
Title: [DOCS] Add setup guide for Windows developers

What needs updating?
Installation instructions assume Unix-like environment (macOS/Linux).
Windows users have to troubleshoot virtual environment activation,
path separators, and other Windows-specific issues.

Current state
README.md has generic Python setup instructions.

Suggested changes
Create docs/WINDOWS_SETUP.md with:
- Virtual environment activation (PowerShell vs CMD.exe)
- Database path setup
- Running tests on Windows
- Common issues & fixes

Impact: New developers on Windows (at least 1-2 per month based on issues)
```

---

## Need Help?

- **General questions**: Use [Discussions](../../discussions)
- **How to use**: Check [README](../../blob/develop/README.md) and [docs/](../../tree/develop/docs)
- **Security concern**: Use [GitHub Security Advisory](../../security/advisories)
- **Something else**: Open a blank issue with clear details

---

**Thank you for contributing to Traderrr!** 🚀
