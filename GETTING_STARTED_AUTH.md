# Getting Started with Phase 1 Authentication

This guide walks you through setting up and using the new multi-user authentication system.

## Quick Start (5 minutes)

### 1. Initialize Admin User

Choose one of two methods:

**Option A: Interactive CLI (Recommended)**
```bash
python -m app.cli setup-admin
```

Follow the prompts to enter:
- Admin username
- Admin email
- Admin password (8+ chars, letters + numbers)

**Option B: Environment Variables**

Edit `.env`:
```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=YourSecurePass123
```

Then start the app:
```bash
python main.py
```

### 2. Start the Application

```bash
python main.py
```

You should see:
```
============================================================
>> Trading Signals System Starting
============================================================
...
2025-11-28 07:39:53,002 - app.auth.init - INFO - Authentication system initialized successfully
```

### 3. Register a User

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePassword123"
  }'
```

Expected response (201 Created):
```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": 2,
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

### 4. Login to Get JWT Token

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePassword123"
  }'
```

Expected response (200 OK):
```json
{
  "success": true,
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 2,
    "username": "john_doe",
    "email": "john@example.com",
    "role": "user"
  }
}
```

**Save the `access_token` - you'll need it for API calls.**

### 5. Access Protected Endpoints

Use the JWT token to access your portfolio:

```bash
curl http://localhost:5000/api/portfolio/positions \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

## Authentication Methods

### Method 1: JWT Token (Best for Web/Mobile)

Get token from login endpoint, then use it:
```bash
curl http://localhost:5000/api/portfolio/positions \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

**Pros**: Standard, can refresh, per-session
**Cons**: Expires after 24 hours (configurable)

### Method 2: API Key (Best for Scripts/Bots)

**Create an API key:**
```bash
curl -X POST http://localhost:5000/api/auth/api-keys \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Bot Key",
    "expires_in_days": 90
  }'
```

Response includes your key (only shown once):
```json
{
  "success": true,
  "api_key": "dlKxH2-vJ8zQ9mP7nR4sT5...",
  "warning": "Save the API key now. It will not be displayed again."
}
```

**Use the API key:**
```bash
curl http://localhost:5000/api/portfolio/positions \
  -H "Authorization: Bearer dlKxH2-vJ8zQ9mP7nR4sT5..."
```

**Pros**: Long-lived, no refresh needed, good for automation
**Cons**: Never shows again once created, needs secure storage

### Method 3: Refresh Token (JWT Only)

After token expires, get a new one:
```bash
curl -X POST http://localhost:5000/api/auth/refresh \
  -H "Authorization: Bearer <EXPIRING_TOKEN>"
```

## User Management (Admin Only)

Login as admin first:
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "YourAdminPass123"}'
```

### List All Users
```bash
curl http://localhost:5000/api/admin/users \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>"
```

### Get User Details
```bash
curl http://localhost:5000/api/admin/users/2 \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>"
```

### Update User (Status/Role)
```bash
curl -X PATCH http://localhost:5000/api/admin/users/2 \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "inactive",
    "role": "analyst"
  }'
```

### Reset User Password (Admin Only)
```bash
curl -X POST http://localhost:5000/api/admin/users/2/reset-password \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "NewSecurePass456"}'
```

### Delete User
```bash
curl -X DELETE http://localhost:5000/api/admin/users/2 \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>"
```

## CLI Commands

### Setup Admin User
```bash
python -m app.cli setup-admin
```

Interactive prompts for username, email, password.

### Initialize Database
```bash
python -m app.cli init-db
```

Creates tables and default roles.

### List All Users
```bash
python -m app.cli list-users
```

Shows all users with their roles and status.

### Delete a User
```bash
python -m app.cli delete-user
```

Prompts for username, requires confirmation.

## Configuration

Edit `.env` to configure:

```
# JWT Token Expiration (in seconds, default 24 hours)
JWT_ACCESS_TOKEN_EXPIRES=86400

# Admin bootstrap (optional, if not set use CLI)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=YourSecurePass123

# Allow open registration (default true)
ALLOW_REGISTRATION=true

# JWT Secret (CHANGE IN PRODUCTION!)
JWT_SECRET_KEY=your-jwt-secret-key-here-change-in-production
```

## Common Tasks

### Change JWT Secret (IMPORTANT!)

In production, you MUST change the JWT secret:

```bash
# Generate a secure secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Update `.env`:
```
JWT_SECRET_KEY=<generated-secret-here>
```

### Manage API Keys for a User

List keys:
```bash
curl http://localhost:5000/api/auth/api-keys \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

Revoke a key:
```bash
curl -X DELETE http://localhost:5000/api/auth/api-keys/1 \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

### Check User's Own Info

Get current user details (from JWT claims):
```bash
curl http://localhost:5000/api/auth/profile \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

### Recover Lost Admin Password

If you lose the admin password and didn't set it in env vars:

1. Delete the database:
   ```bash
   rm data/market_data.db
   ```

2. Re-run setup:
   ```bash
   python -m app.cli setup-admin
   ```

## Troubleshooting

### "Authentication required" Error
- Missing or invalid JWT token
- API key not sent correctly
- Check: `Authorization: Bearer <token>` format

### "Invalid password" Error
- Password must be 8+ characters
- Password must have letters AND numbers
- Example: `SecurePass123`

### "User not found" Error
- Check username spelling
- User may have been deleted
- Try registering a new user

### Database Lock Error
- SQLite file is locked
- Stop all running instances
- Or use PostgreSQL for multi-process apps

### ADMIN_USERNAME not being set
- Must be in `.env` file
- Reload app after changing `.env`
- Or use CLI: `python -m app.cli setup-admin`

## Security Best Practices

1. **Change JWT Secret in Production**
   ```bash
   # Generate new secret
   JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

2. **Use HTTPS Only in Production**
   - JWT tokens are sent in Authorization header
   - Always use HTTPS to prevent token interception

3. **Rotate API Keys Regularly**
   ```bash
   # Create new key
   curl -X POST http://localhost:5000/api/auth/api-keys ...

   # Revoke old key
   curl -X DELETE http://localhost:5000/api/auth/api-keys/<old-id> ...
   ```

4. **Disable Registration After Setup**
   ```
   ALLOW_REGISTRATION=false
   ```

5. **Use Strong Passwords**
   - Minimum 8 characters
   - Mix of letters and numbers
   - Consider adding special characters

6. **Monitor Admin Accounts**
   - Check last login: `python -m app.cli list-users`
   - Review API key usage
   - Audit logs for suspicious activity

## Next Steps

- Read `PHASE_1_COMPLETION.md` for architecture details
- Read `PHASE_1_TEST_RESULTS.md` for test coverage info
- Review API docs at: http://localhost:5000/api/docs
- Check database schema: Look at `app/models/user.py`

## Support

For detailed implementation info, see:
- `PHASE_1_COMPLETION.md` - Full feature list
- `PHASE_1_TEST_RESULTS.md` - Test results (22/22 passing)
- `tests/test_authentication.py` - Test examples

For API reference, see Swagger UI at:
- http://localhost:5000/api/docs
