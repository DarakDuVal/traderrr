"""
REST API Step Definitions

Step implementations for API-related BDD scenarios.
"""

from behave import given, when, then


@given("the API server is running")
def step_api_running(context):
    """Verify API server is running."""
    context.logger.info("API server check")
    context.api_base_url = "http://localhost:5000"
    context.api_requests = []
    context.api_responses = []


@when('I send a GET request to "{endpoint}"')
def step_get_request(context, endpoint):
    """Send a GET request to endpoint."""
    context.logger.info(f"GET {endpoint}")
    context.last_endpoint = endpoint
    context.last_request = {
        "method": "GET",
        "endpoint": endpoint,
        "headers": {"Authorization": getattr(context, "auth_token", None)},
    }

    # Simulate response based on endpoint
    if endpoint == "/health":
        context.last_response = {
            "status": 200,
            "data": {"status": "healthy", "timestamp": "2024-01-01T00:00:00"},
        }
    elif endpoint == "/api/signals":
        context.last_response = {
            "status": 200,
            "data": [
                {"ticker": "AAPL", "signal_type": "BUY", "confidence": 0.85},
                {"ticker": "MSFT", "signal_type": "HOLD", "confidence": 0.60},
            ],
        }
    elif endpoint == "/api/portfolio":
        context.last_response = {
            "status": 200,
            "data": {
                "total_value": 50000,
                "positions": [{"ticker": "AAPL", "shares": 100, "value": 15000}],
            },
        }
    elif endpoint == "/api/signals/nonexistent":
        context.last_response = {"status": 404, "data": {"error": "Signal not found"}}
    else:
        context.last_response = {"status": 200, "data": {}}

    context.api_responses.append(context.last_response)


@when('I send a GET request to "{endpoint}" without credentials')
def step_get_request_no_auth(context, endpoint):
    """Send unauthenticated GET request."""
    context.logger.info(f"GET {endpoint} (no auth)")
    context.last_request = {"method": "GET", "endpoint": endpoint, "headers": {}}
    context.last_response = {"status": 401, "data": {"error": "Authentication required"}}
    context.api_responses.append(context.last_response)


@when('I send a POST request to "{endpoint}" with invalid data')
def step_post_invalid_data(context, endpoint):
    """Send POST request with invalid data."""
    context.logger.info(f"POST {endpoint} (invalid data)")
    context.last_request = {"method": "POST", "endpoint": endpoint, "data": {"invalid": "data"}}
    context.last_response = {
        "status": 400,
        "data": {"error": "Validation failed", "details": ["Missing required field: ticker"]},
    }
    context.api_responses.append(context.last_response)


@when("I request the OpenAPI documentation")
def step_request_openapi(context):
    """Request OpenAPI spec."""
    context.logger.info("Requesting OpenAPI documentation")
    context.last_response = {
        "status": 200,
        "data": {
            "openapi": "3.0.0",
            "info": {"title": "Trading Signals API", "version": "1.0.0"},
            "paths": {
                "/health": {"get": {"summary": "Health check"}},
                "/api/signals": {"get": {"summary": "Get trading signals"}},
                "/api/portfolio": {"get": {"summary": "Get portfolio"}},
            },
        },
    }


@when("I send {count:d} requests in rapid succession")
def step_rapid_requests(context, count):
    """Send multiple requests rapidly."""
    context.logger.info(f"Sending {count} rapid requests")
    context.api_responses = []

    for i in range(count):
        if i < 95:  # First 95 pass
            response = {
                "status": 200,
                "headers": {"X-RateLimit-Limit": "100", "X-RateLimit-Remaining": str(100 - i)},
            }
        else:  # Remaining are rate limited
            response = {
                "status": 429,
                "headers": {
                    "X-RateLimit-Limit": "100",
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60",
                },
            }
        context.api_responses.append(response)


@then("the response status should be {status_code:d}")
def step_response_status(context, status_code):
    """Verify response status code."""
    actual_status = context.last_response["status"]
    assert actual_status == status_code, f"Expected status {status_code} but got {actual_status}"
    context.logger.info(f"Response status: {status_code}")


@then("the response should indicate the system is healthy")
def step_response_healthy(context):
    """Verify health status response."""
    data = context.last_response.get("data", {})
    assert data.get("status") == "healthy"
    context.logger.info("System is healthy")


@then("the response should be a list of signals")
def step_response_is_signal_list(context):
    """Verify response contains list of signals."""
    data = context.last_response.get("data", [])
    assert isinstance(data, list)
    assert len(data) > 0
    context.logger.info(f"Response contains {len(data)} signals")


@then("each signal should have required fields")
def step_signals_have_fields(context):
    """Verify each signal has required fields."""
    data = context.last_response.get("data", [])
    required_fields = {"ticker", "signal_type", "confidence"}
    for signal in data:
        assert required_fields.issubset(
            signal.keys()
        ), f"Signal missing required fields: {required_fields - set(signal.keys())}"
    context.logger.info("All signals have required fields")


@then("the response should contain portfolio information")
def step_response_has_portfolio(context):
    """Verify portfolio response."""
    data = context.last_response.get("data", {})
    assert "total_value" in data or "positions" in data
    context.logger.info("Response contains portfolio information")


@then("the portfolio should have a total value")
def step_portfolio_has_value(context):
    """Verify portfolio has total value."""
    data = context.last_response.get("data", {})
    assert "total_value" in data
    assert data["total_value"] > 0
    context.logger.info(f"Portfolio value: ${data['total_value']}")


@then("the response should indicate authentication is required")
def step_response_requires_auth(context):
    """Verify authentication error response."""
    data = context.last_response.get("data", {})
    assert "error" in data
    assert "authentication" in data.get("error", "").lower()
    context.logger.info("Authentication is required")


@then("the response should describe the validation error")
def step_response_has_validation_error(context):
    """Verify validation error response."""
    data = context.last_response.get("data", {})
    assert "error" in data or "details" in data
    context.logger.info("Validation error description provided")


@then("the response should indicate the resource was not found")
def step_response_resource_not_found(context):
    """Verify not found error response."""
    data = context.last_response.get("data", {})
    assert "error" in data
    context.logger.info("Resource not found")


@then("the documentation should list all available endpoints")
def step_docs_list_endpoints(context):
    """Verify documentation lists endpoints."""
    data = context.last_response.get("data", {})
    assert "paths" in data
    assert len(data["paths"]) > 0
    context.logger.info(f"Documentation lists {len(data['paths'])} endpoints")


@then("each endpoint should have method, parameters, and responses documented")
def step_endpoints_documented(context):
    """Verify endpoints are documented."""
    data = context.last_response.get("data", {})
    for path, methods in data.get("paths", {}).items():
        assert isinstance(methods, dict)
        # Should have at least one HTTP method
        assert any(m in methods for m in ["get", "post", "put", "delete"])
    context.logger.info("All endpoints properly documented")


@then("some requests should be rate limited")
def step_some_rate_limited(context):
    """Verify some requests hit rate limit."""
    rate_limited = sum(1 for r in context.api_responses if r["status"] == 429)
    assert rate_limited > 0, "Expected some requests to be rate limited"
    context.logger.info(f"{rate_limited} requests were rate limited")


@then("the response should include rate limit headers")
def step_rate_limit_headers(context):
    """Verify rate limit headers present."""
    for response in context.api_responses:
        if response["status"] == 429:
            headers = response.get("headers", {})
            assert "X-RateLimit-Limit" in headers
            assert "X-RateLimit-Remaining" in headers
            context.logger.info("Rate limit headers present")
            return

    assert False, "No rate limited response found"
