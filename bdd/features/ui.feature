Feature: graphical user interface (GUI/UI)
  As an application user
  I want to interact with the trading system via graphical user interface
  So that I can edit portfolios, watch and see signals, maintain user settings interactively

Background:
  Given the API server is running
  Given the database is available


@ui
Scenario: First-time logon
  When a user logs on a freshly deployed system for the first time
  And no admin user has been specified in the environment
  Then the user registers as admin user to assert user with highest privilege is available for administering the app.

@ui
Scenario: New user registers on logon screen
  When I register as new user
  And I enter my chosen user name (optional, defaults to email address), password and email address via UI
  Then the system makes sure my user name is unique
  And the credentials are being stored for logon purposes
  And I receive feedback on success or fail during my registration

@ui
Scenario: Returning user logs on
  When I previously registered
  And I return to logon screen
  And I enter my credentials (username, password)
  Then the system performs all steps necessary for user authentication and authorization
  And on successful logon redirects me to my user-configured or default dashboard.

@ui
Scenario: Returning user has valid token and is already logged on
  When I previously logged on
  And I return before expiry of my token
  Then the system handles my user logon correctly otherwise returns me to logon page.