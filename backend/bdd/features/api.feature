Feature: REST API Functionality
  As an API consumer
  I want to interact with the trading system via REST API
  So that I can integrate it with other applications

  Background:
    Given the API server is running

  @api
  Scenario: API health check endpoint is accessible
    When I send a GET request to "/health"
    Then the response status should be 200
    And the response should indicate the system is healthy

  @api
  Scenario: User can fetch signals via API
    When I send a GET request to "/api/signals"
    Then the response status should be 200
    And the response should be a list of signals
    And each signal should have required fields

  @api
  Scenario: User can fetch portfolio via API
    When I send a GET request to "/api/portfolio"
    Then the response status should be 200
    And the response should contain portfolio information
    And the portfolio should have a total value

  @api
  Scenario: API requires authentication for protected endpoints
    When I send a GET request to "/api/portfolio" without credentials
    Then the response status should be 401
    And the response should indicate authentication is required

  @api
  Scenario: API validates request parameters
    When I send a POST request to "/api/position" with invalid data
    Then the response status should be 400
    And the response should describe the validation error

  @api
  Scenario: API returns appropriate error for not found resources
    When I send a GET request to "/api/signals/nonexistent"
    Then the response status should be 404
    And the response should indicate the resource was not found

  @api
  Scenario: API documents endpoints with OpenAPI
    When I request the OpenAPI documentation
    Then the documentation should list all available endpoints
    And each endpoint should have method, parameters, and responses documented

  @api
  Scenario: API rate limiting is enforced
    When I send 100 requests in rapid succession
    Then some requests should be rate limited
    And the response should include rate limit headers
