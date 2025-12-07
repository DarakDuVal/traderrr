# Database Schema Fix Plan

## Problem Identified

**Error:** `(sqlite3.OperationalError) no such column: portfolio_positions.id`

**Root Cause:**
The database was created before the `PortfolioPosition` model was updated to include SQLAlchemy ORM columns. The current database schema is missing columns that the model expects.

### Current Error Log:
```
2025-12-06 12:05:41,011 - app.api.routes - ERROR - Get positions API error: (sqlite3.OperationalError) no such column: portfolio_positions.id
[SQL: SELECT portfolio_positions.id AS portfolio_positions_id, portfolio_positions.user_id AS portfolio_positions_user_id, ...
```

## Model Definition (Correct)
From `app/models/portfolio.py`:
```python
class PortfolioPosition(Base, TimestampMixin):
    __tablename__ = "portfolio_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ticker: Mapped[str] = mapped_column(String(10))
    shares: Mapped[Decimal] = mapped_column()
    # Plus created_at, updated_at from TimestampMixin
```

## Solution Options

### Option 1: Reinitialize Database (Recommended - Clean Slate)
**Pros:**
- Ensures schema matches models perfectly
- Fixes all potential schema mismatches
- Clean development environment

**Cons:**
- Deletes all existing data

**Steps:**
1. Stop the Flask server
2. Delete the existing database file:
   ```bash
   rm data/trading_system.db
   # or on Windows:
   del data\trading_system.db
   ```
3. Run database initialization:
   ```bash
   python -m app.cli init-db
   ```
4. Recreate admin user:
   ```bash
   python -m app.cli setup-admin
   ```
5. Restart server and test

### Option 2: Database Migration (Production-Safe)
**Pros:**
- Preserves existing data
- Production-safe approach

**Cons:**
- More complex
- Requires migration tool setup

**Steps:**
1. Install Alembic (if not installed):
   ```bash
   pip install alembic
   ```
2. Initialize Alembic:
   ```bash
   alembic init alembic
   ```
3. Configure alembic.ini and env.py
4. Create migration:
   ```bash
   alembic revision --autogenerate -m "Add id column to portfolio_positions"
   ```
5. Apply migration:
   ```bash
   alembic upgrade head
   ```

### Option 3: Manual SQL ALTER (Quick Fix)
**Pros:**
- Quick fix for development
- No data loss

**Cons:**
- Manual SQL risk
- May not catch all schema issues

**Steps:**
1. Connect to database:
   ```bash
   sqlite3 data/trading_system.db
   ```
2. Check current schema:
   ```sql
   PRAGMA table_info(portfolio_positions);
   ```
3. If `id` column is missing, drop and recreate table:
   ```sql
   BEGIN TRANSACTION;

   -- Backup existing data
   CREATE TEMP TABLE portfolio_positions_backup AS
   SELECT * FROM portfolio_positions;

   -- Drop old table
   DROP TABLE portfolio_positions;

   -- Create new table with correct schema
   CREATE TABLE portfolio_positions (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       user_id INTEGER NOT NULL,
       ticker VARCHAR(10) NOT NULL,
       shares DECIMAL NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (user_id) REFERENCES users(id)
   );

   -- Restore data (if any exists and columns match)
   INSERT INTO portfolio_positions (user_id, ticker, shares, created_at, updated_at)
   SELECT user_id, ticker, shares, created_at, updated_at
   FROM portfolio_positions_backup;

   COMMIT;
   ```

## Recommended Approach for Development

Since this is a development environment and the issue was just discovered:

**Use Option 1 - Clean Database Reinit**

### Quick Fix Commands:
```bash
# 1. Stop Flask server (Ctrl+C in terminal)

# 2. Delete database
del data\trading_system.db  # Windows
# or
rm data/trading_system.db   # Linux/Mac

# 3. Reinitialize
python -m app.cli init-db

# 4. Create admin user
python -m app.cli setup-admin

# 5. Restart server
python main.py
```

## Verification Steps

After fix:
1. Start the server
2. Log in as admin
3. Try to add a portfolio position:
   - Go to dashboard
   - Click "Add Position"
   - Enter ticker (e.g., "AAPL") and shares (e.g., "10")
   - Submit
4. Verify no errors in logs
5. Verify position appears in portfolio

## Prevention

To prevent this in the future:
1. Use Alembic for schema migrations
2. Document schema changes
3. Version the database with migrations
4. Add schema validation on startup
5. Include database initialization in development setup docs

## Additional Errors Found in Logs

### SQLite Interface Errors
```
(sqlite3.InterfaceError) bad parameter or other API misuse
```

These may be related to:
- Datetime handling (passing datetime objects instead of strings)
- Query parameter formatting

After fixing the schema, monitor for these errors and fix if they persist.
