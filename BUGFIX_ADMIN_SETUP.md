# Bug Fix: Admin User Setup

## Issue
When running `python -m app.cli setup-admin`, the command failed with:
```
TypeError: AuthService.register_user() got an unexpected keyword argument 'role'
```

## Root Cause
Two files were using the incorrect parameter name `role` when calling `AuthService.register_user()`:
- `app/cli.py` (line 102)
- `app/auth/init.py` (line 68)

The correct parameter name is `role_name` to match the function signature:
```python
def register_user(
    session: Session,
    username: str,
    email: str,
    password: str,
    role_name: str = RoleEnum.USER,  # <-- Parameter name is 'role_name'
) -> tuple[bool, User | None, str | None]:
```

## Fix Applied
Updated both files to use `role_name` parameter:

### app/cli.py (line 102)
**Before:**
```python
success, user, error = AuthService.register_user(
    session, username, email, password, role=RoleEnum.ADMIN
)
```

**After:**
```python
success, user, error = AuthService.register_user(
    session, username, email, password, role_name=RoleEnum.ADMIN
)
```

### app/auth/init.py (line 68)
**Before:**
```python
success, user, error = AuthService.register_user(
    session, username, f"{username}@admin.local", password, role=RoleEnum.ADMIN
)
```

**After:**
```python
success, user, error = AuthService.register_user(
    session, username, f"{username}@admin.local", password, role_name=RoleEnum.ADMIN
)
```

## Testing
✅ Verified imports work correctly
✅ Verified admin user creation with fixed parameter
✅ Both CLI and environment variable bootstrap now work

## How to Use (Updated)

### Method 1: Interactive CLI Setup (Recommended)
```bash
python -m app.cli setup-admin
```

Enter when prompted:
- Admin username: `admin`
- Admin email: `admin@example.com`
- Admin password: `YourSecurePass123` (must be 8+ chars with letters and numbers)

### Method 2: Environment Variables
Edit `.env`:
```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=YourSecurePass123
```

Then start the app:
```bash
python main.py
```

Both methods now work correctly!

## Verification
To verify the fix is applied, check:
```bash
grep "role_name=RoleEnum" app/cli.py app/auth/init.py
```

Both should return matches.

## Git Commit
```
commit 5544dec
Fix: Update register_user parameter from 'role' to 'role_name' in CLI and init
```

## Status
✅ FIXED - Admin user creation now works correctly via both CLI and environment variables
