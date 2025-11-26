# Testing API Routes with Bearer Token Authentication

## Summary

After implementing Bearer token authentication for all API endpoints, the test suite required updates to include the `Authorization` header with valid API keys in all requests.

## Changes Made

### 1. Updated `tests/__init__.py` - BaseTestCase Class

Added helper method for authentication headers:

```python
# Demo API key for testing (from app/api/auth.py)
TEST_API_KEY = "test-api-key-67890"

def get_auth_headers(self, api_key=None):
    """Get headers with Bearer token authentication

    Args:
        api_key: API key to use (default: TEST_API_KEY)

    Returns:
        dict: Headers dict with Authorization bearer token
    """
    if api_key is None:
        api_key = self.TEST_API_KEY
    return {"Authorization": f"Bearer {api_key}"}
```

**Why**: Provides a centralized, reusable method for adding authentication headers to all API requests. Eliminates code duplication and makes it easy to change the test API key globally.

### 2. Updated `tests/test_api_routes.py` - All API Calls

#### Pattern 1: Simple GET/POST/PUT/DELETE Requests

**Before:**
```python
response = self.client.get("/api/health")
```

**After:**
```python
response = self.client.get("/api/health", headers=self.get_auth_headers())
```

#### Pattern 2: POST/PUT Requests with JSON Data

**Before:**
```python
response = self.client.post(
    "/api/portfolio/positions",
    data=json.dumps(position_data),
    content_type="application/json",
)
```

**After:**
```python
response = self.client.post(
    "/api/portfolio/positions",
    data=json.dumps(position_data),
    content_type="application/json",
    headers=self.get_auth_headers(),
)
```

#### Pattern 3: Requests with Custom Headers

**Before:**
```python
response = self.client.get(
    "/api/health",
    headers={"X-Custom-Header": "test-value"},
)
```

**After:**
```python
headers = self.get_auth_headers()
headers["X-Custom-Header"] = "test-value"
response = self.client.get(
    "/api/health",
    headers=headers,
)
```

### 3. Added Authentication Tests

Added new tests in `TestAPIAuthenticationHeaders` class:

```python
def test_missing_api_key(self):
    """Test API request without Authorization header"""
    response = self.client.get("/api/health")
    # Should return 401 Unauthorized
    self.assertEqual(response.status_code, 401)

def test_invalid_api_key(self):
    """Test API request with invalid API key"""
    response = self.client.get(
        "/api/health",
        headers={"Authorization": "Bearer invalid-api-key-xyz"},
    )
    # Should return 401 Unauthorized
    self.assertEqual(response.status_code, 401)

def test_malformed_auth_header(self):
    """Test API request with malformed Authorization header"""
    response = self.client.get(
        "/api/health",
        headers={"Authorization": "InvalidFormat api-key"},
    )
    # Should return 401 Unauthorized
    self.assertEqual(response.status_code, 401)

def test_valid_api_key_works(self):
    """Test API request with valid API key"""
    response = self.client.get(
        "/api/health",
        headers=self.get_auth_headers(),
    )
    # Should succeed with valid key
    self.assertIn(response.status_code, [200, 503])  # 200 or 503 (degraded)
```

## API Keys for Testing

The following demo API keys are available in `app/api/auth.py`:

- **`test-api-key-67890`** (test_user) - Used by default in tests
- **`demo-api-key-12345`** (demo_user) - Alternative test key

To use a different API key in tests:

```python
# Use alternative API key
response = self.client.get(
    "/api/health",
    headers=self.get_auth_headers("demo-api-key-12345")
)
```

## Running Tests

### Run All API Route Tests

```bash
pytest tests/test_api_routes.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_api_routes.py::TestAPIHealth -v
```

### Run Specific Test

```bash
pytest tests/test_api_routes.py::TestAPIAuthenticationHeaders::test_missing_api_key -v
```

### Run with Coverage

```bash
pytest tests/test_api_routes.py --cov=app.api --cov-report=html
```

## Test Results

All 46 API route tests pass successfully:

- **TestAPIHealth**: 1 test ✓
- **TestAPISignals**: 6 tests ✓
- **TestAPIPortfolioPerformance**: 6 tests ✓
- **TestAPIPortfolioManagement**: 7 tests ✓
- **TestAPIRiskAnalysis**: 4 tests ✓
- **TestAPITickerData**: 4 tests ✓
- **TestAPIErrorHandling**: 4 tests ✓
- **TestAPIResponseFormats**: 3 tests ✓
- **TestAPIParameterValidation**: 5 tests ✓
- **TestAPIAuthenticationHeaders**: 6 tests ✓ (including new auth tests)

**Total: 46 PASSED in 23.43s**

## Key Points

1. **Authentication is Required**: All API endpoints now require Bearer token authentication
2. **Use `get_auth_headers()`**: Always use the helper method from BaseTestCase to get authentication headers
3. **Test API Keys**: Use `test-api-key-67890` by default (defined as `TEST_API_KEY`)
4. **Custom Headers**: When combining custom headers with authentication, create the auth headers first, then add custom headers to the dict
5. **Error Testing**: Test both successful requests (with valid key) and failure cases (missing/invalid key)

## No .env Changes Required

The test API keys are hardcoded in `app/api/auth.py` and available immediately without needing `.env` configuration. The `FLASK_ENV=testing` is already set in the `BaseTestCase.setUp()` method.

## Production API Keys

For production use, API keys should be:
- Generated dynamically using `generate_api_key()` function
- Stored securely in a database (not hardcoded)
- Managed through a key management system
- Rotated regularly

See `docs/API.md` for production usage examples.
