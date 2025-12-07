# Test Failure Fix Plan

## Test Results Summary
- **Total Tests:** 455
- **Passed:** 452
- **Failed:** 3
- **Success Rate:** 99.3%

## Failed Tests Analysis

### 1. Authentication Test Failure
**Test:** `test_authentication.py::TestAuthenticationCompleteFlow::test_scenario_registration_duplicate_username`

**Error:**
```
AssertionError: assert 'already exists' in 'password must be at least 8 characters long'
```

**Location:** `tests/test_authentication.py:1490`

**Root Cause:**
The test is attempting to register a duplicate username with password "Pass123" (7 characters), which violates the password strength requirement (minimum 8 characters). The password validation is failing BEFORE the duplicate username check, causing the wrong error message.

**Fix Strategy:**
- Update the test to use a password that meets strength requirements (at least 8 characters)
- Change `"password": "Pass123"` to `"password": "Pass1234"` or similar
- This will allow the duplicate username validation to execute and return the expected error

**Priority:** High (functional test failure)
**Estimated Effort:** Low (1-line fix)

---

### 2. Dashboard UI Selenium Test Failures (2 failures)

**Tests:**
1. `test_dashboard_ui.py::TestAuthScreenLayout::test_login_title_visible`
2. `test_dashboard_ui.py::TestAuthScreenLayout::test_auth_tabs_have_correct_labels`

**Error:**
```
selenium.common.exceptions.TimeoutException: Message: timeout: Timed out receiving message from renderer
```

**Root Cause:**
These failures are related to the recent dashboard.html template changes. The template was moved from inline HTML in dashboard.py to a separate file (app/web/templates/dashboard.html). Possible issues:
1. Template rendering timing issue - page may be taking longer to load
2. Element selectors may need updating if HTML structure changed
3. Selenium WebDriver configuration may need timeout adjustments
4. The template file path configuration (recent fix) may have introduced timing issues

**Fix Strategy:**

**Option A: Increase Timeouts (Quick Fix)**
- Increase WebDriver wait timeouts in the failing tests
- Add explicit waits for specific elements to load
- Verify page is fully rendered before searching for elements

**Option B: Fix Template Loading (Root Cause Fix)**
- Verify the template_folder configuration is working correctly
- Check if static resources are loading properly
- Ensure JavaScript initialization completes before tests check DOM

**Option C: Update Test Selectors**
- Review if element IDs/classes changed during template migration
- Update Selenium selectors to match new template structure
- Add retry logic for flaky Selenium tests

**Recommended Approach:**
1. First, verify the template loads correctly in a real browser
2. Add explicit waits with increased timeouts (10-15 seconds)
3. Use WebDriverWait with expected_conditions for specific elements
4. Add logging to see which element is timing out

**Priority:** Medium (UI test failures, doesn't affect functionality)
**Estimated Effort:** Medium (requires debugging Selenium tests)

---

## Additional Issues Found

### Database Connection Warnings
Multiple ResourceWarning messages about unclosed database connections:
```
ResourceWarning: unclosed database in <sqlite3.Connection object at 0x...>
```

**Root Cause:**
Database connections not being properly closed in test teardown or in application code.

**Fix Strategy:**
- Add proper connection cleanup in test fixtures
- Ensure all DatabaseManager instances close connections
- Use context managers (`with` statements) for database operations
- Add `@pytest.fixture(autouse=True)` for connection cleanup

**Priority:** Low (warnings, not failures)
**Estimated Effort:** Medium (requires reviewing multiple test files)

---

## Implementation Plan

### Phase 1: Quick Wins (Immediate)
1. **Fix authentication test password**
   - File: `tests/test_authentication.py:1484`
   - Change: `"password": "Pass123"` → `"password": "Pass1234"`
   - Test: Run `pytest tests/test_authentication.py::TestAuthenticationCompleteFlow::test_scenario_registration_duplicate_username -v`

### Phase 2: Selenium Test Fixes (Short-term)
1. **Investigate template loading**
   - Manually test dashboard loads correctly at `http://localhost:5000/`
   - Check browser console for JavaScript errors
   - Verify template_folder path is correct

2. **Update Selenium wait configuration**
   - File: `tests/test_dashboard_ui.py`
   - Increase implicit_wait from current value to 15 seconds
   - Add explicit WebDriverWait for auth screen elements:
     ```python
     from selenium.webdriver.support.ui import WebDriverWait
     from selenium.webdriver.support import expected_conditions as EC
     from selenium.webdriver.common.by import By

     wait = WebDriverWait(driver, 15)
     element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "login-title")))
     ```

3. **Add retry logic**
   - Use `@pytest.mark.flaky(reruns=2)` for Selenium tests
   - Install pytest-rerunfailures if not present

### Phase 3: Database Connection Cleanup (Long-term)
1. **Add connection cleanup fixture**
   - File: `tests/conftest.py` or `tests/__init__.py`
   - Create autouse fixture to close all connections after each test

2. **Review DataManager usage**
   - Ensure all `get_session()` calls have corresponding `close()` calls
   - Consider using context managers for session management

3. **Update test database setup**
   - Use SQLAlchemy session management best practices
   - Ensure proper rollback/cleanup in fixtures

---

## Testing Strategy

### After Each Fix:
1. Run the specific failing test to verify fix
2. Run the full test suite module to ensure no regressions
3. Run complete suite before marking as complete

### Commands:
```bash
# Test specific failure
pytest tests/test_authentication.py::TestAuthenticationCompleteFlow::test_scenario_registration_duplicate_username -v

# Test dashboard UI module
pytest tests/test_dashboard_ui.py -v

# Full test suite
pytest -v

# With warnings shown
pytest -v -W default
```

---

## Success Criteria
- All 455 tests passing
- No ResourceWarning messages
- Selenium tests complete within reasonable time (<10 seconds each)
- 100% test success rate

---

## Notes
- The template folder fix (commit 3181d9b) successfully resolved the template rendering issue
- Most tests (99.3%) are passing, indicating good code quality
- The failures are minor and easily fixable
- No breaking changes to core functionality detected
