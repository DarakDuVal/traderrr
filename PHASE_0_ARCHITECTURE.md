# Phase 0: Architecture Diagrams and Data Model

## 1. Layered Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLASK ROUTES & ENDPOINTS                      │
│              (app/api/routes.py, app/web/dashboard.py)          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│          BUSINESS LOGIC LAYER (SERVICE LAYER)                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ PortfolioManager │  │ DataManager      │  │SignalGenerator │ │
│  │ (Read/Write)     │  │ (Read)           │  │(Generate)      │ │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬───────┘ │
└───────────┼──────────────────────┼────────────────────┼──────────┘
            │                      │                    │
            └──────────────────────┼────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│            ORM LAYER (NEW IN PHASE 0)                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           SQLAlchemy ORM Models (app/models/)              │ │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │ │
│  │ │DailyData │ │Signal    │ │Portfolio │ │SystemEvent       │ │
│  │ │IntradayData │History  │ │Position  │ │          │       │ │
│  │ │Metadata  │ │Performance│          │          │       │ │
│  │ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                  │                               │
│                                  ↓                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │        Database Manager (app/db.py)                        │ │
│  │  - Session Management                                      │ │
│  │  - Connection Pooling                                      │ │
│  │  - Database Initialization                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│           DATABASE ABSTRACTION LAYER (SQLAlchemy)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ SQLite       │  │ PostgreSQL   │  │ MySQL        │          │
│  │ Dialect      │  │ Dialect      │  │ Dialect      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│                   DATABASE DRIVERS                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ sqlite3      │  │ psycopg2     │  │ PyMySQL      │          │
│  │ (built-in)   │  │ (PostgreSQL) │  │ (MySQL)      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│                   ACTUAL DATABASES                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ SQLite File  │  │ PostgreSQL   │  │ MySQL        │          │
│  │ (Local)      │  │ Server       │  │ Server       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Model ER Diagram (Current - Phase 0)

```
┌─────────────────────────────┐
│       DAILY_DATA            │
├─────────────────────────────┤
│ PK: ticker + date           │
│ - open (REAL)               │
│ - high (REAL)               │
│ - low (REAL)                │
│ - close (REAL)              │
│ - volume (INTEGER)          │
│ - dividends (REAL)          │
│ - stock_splits (REAL)       │
│ - created_at (TIMESTAMP)    │
│ - updated_at (TIMESTAMP)    │
└─────────────────────────────┘
        ↑
        │ ticker lookup
        │
┌─────────────────────────────┐
│       METADATA              │
├─────────────────────────────┤
│ PK: ticker                  │
│ - company_name (TEXT)       │
│ - sector (TEXT)             │
│ - industry (TEXT)           │
│ - market_cap (REAL)         │
│ - last_updated (TIMESTAMP)  │
│ - created_at (TIMESTAMP)    │
│ - updated_at (TIMESTAMP)    │
└─────────────────────────────┘


┌─────────────────────────────┐         ┌──────────────────────────┐
│  PORTFOLIO_POSITIONS        │         │   SIGNAL_HISTORY         │
├─────────────────────────────┤         ├──────────────────────────┤
│ PK: ticker                  │         │ PK: id (AUTO)            │
│ - shares (REAL)             │ ───────→│ - ticker (FK)            │
│ - created_at (TIMESTAMP)    │         │ - date (DATE)            │
│ - updated_at (TIMESTAMP)    │         │ - signal_type (TEXT)     │
└─────────────────────────────┘         │ - signal_value (REAL)    │
                                        │ - confidence (REAL)      │
                                        │ - entry_price (REAL)     │
                                        │ - target_price (REAL)    │
                                        │ - stop_loss (REAL)       │
                                        │ - regime (TEXT)          │
                                        │ - reasons (TEXT)         │
                                        │ - created_at (TIMESTAMP) │
                                        │ - updated_at (TIMESTAMP) │
                                        └──────────────────────────┘


┌──────────────────────────────────┐
│  PORTFOLIO_PERFORMANCE           │
├──────────────────────────────────┤
│ PK: id (AUTO)                    │
│ - date (DATE)                    │
│ - portfolio_value (REAL)         │
│ - daily_return (REAL)            │
│ - volatility (REAL)              │
│ - sharpe_ratio (REAL)            │
│ - max_drawdown (REAL)            │
│ - created_at (TIMESTAMP)         │
│ - updated_at (TIMESTAMP)         │
└──────────────────────────────────┘


┌──────────────────────────────────┐
│  INTRADAY_DATA                   │
├──────────────────────────────────┤
│ PK: ticker + datetime            │
│ - open (REAL)                    │
│ - high (REAL)                    │
│ - low (REAL)                     │
│ - close (REAL)                   │
│ - volume (INTEGER)               │
│ - created_at (TIMESTAMP)         │
│ - updated_at (TIMESTAMP)         │
└──────────────────────────────────┘


┌──────────────────────────────────┐
│  SYSTEM_EVENTS                   │
├──────────────────────────────────┤
│ PK: id (AUTO)                    │
│ - event_type (TEXT)              │
│ - description (TEXT)             │
│ - details (TEXT)                 │
│ - severity (TEXT)                │
│ - created_at (TIMESTAMP)         │
│ - updated_at (TIMESTAMP)         │
└──────────────────────────────────┘
```

---

## 3. Phase 0 vs Phase 1 Data Model

### Phase 0 (Current - Single User)
```
User Actions → [No User Table] → All Data Global
         ↓
    SQLite Only
```

### Phase 1 (Multi-User - After Phase 0)
```
┌─────────────────────────────────────────────────────┐
│  NEW USER MANAGEMENT TABLES (Phase 1)               │
├─────────────────────────────────────────────────────┤
│  USERS                                              │
│  ├── id (PK)                                        │
│  ├── username (UNIQUE)                              │
│  ├── email (UNIQUE)                                 │
│  ├── password_hash                                  │
│  └── created_at, updated_at                         │
│                                                     │
│  ROLES                                              │
│  ├── id (PK)                                        │
│  ├── name (UNIQUE)                                  │
│  └── description                                    │
│                                                     │
│  USER_ROLES (user_id, role_id)                     │
│  PERMISSIONS (id, name, description)               │
│  ROLE_PERMISSIONS (role_id, permission_id)        │
│  API_KEYS (id, user_id, key_hash, ...)            │
│  AUDIT_LOGS (id, user_id, action, ...)            │
└─────────────────────────────────────────────────────┘
        ↑
        │ FK relationships
        │
┌─────────────────────────────────────────────────────┐
│  MODIFIED EXISTING TABLES (Phase 1)                 │
├─────────────────────────────────────────────────────┤
│  PORTFOLIO_POSITIONS                                │
│  ├── user_id (FK → USERS) ← NEW COLUMN            │
│  ├── ticker                                         │
│  ├── shares                                         │
│  └── ...                                            │
│                                                     │
│  SIGNAL_HISTORY                                     │
│  ├── user_id (FK → USERS) ← NEW COLUMN            │
│  ├── ticker                                         │
│  ├── ...                                            │
│                                                     │
│  PORTFOLIO_PERFORMANCE                              │
│  ├── user_id (FK → USERS) ← NEW COLUMN            │
│  ├── date                                           │
│  └── ...                                            │
└─────────────────────────────────────────────────────┘
```

---

## 4. Session Management Flow

```
┌────────────────────────────────────────────────────────┐
│              Flask Request Comes In                    │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────┐
│     Middleware: Extract User Context (Phase 1)        │
│     (Store user_id in g.current_user)                 │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────┐
│      Route Handler / Service Function Executes        │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
    ╔════════════════════════════════════════════════╗
    ║    Option A: Use session_context()             ║
    ║  with db.session_context() as session:         ║
    ║      result = session.query(...).first()       ║
    ║      # Auto-commit on exit, rollback on error  ║
    ╚────────────┬─────────────────────────────────╝
                 │
    ╔════════════════════════════════════════════════╗
    ║    Option B: Manual Session Management         ║
    ║  session = get_session()                       ║
    ║  try:                                          ║
    ║      result = session.query(...).first()       ║
    ║      session.commit()                          ║
    ║  finally:                                      ║
    ║      session.close()                           ║
    ╚────────────┬─────────────────────────────────╝
                 │
                 ↓
┌────────────────────────────────────────────────────────┐
│        Connection Fetched from Pool                    │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────┐
│      SQL Query Executed via SQLAlchemy                │
│    (Converted to dialect-specific SQL)                 │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────┐
│      Database Executes Query                          │
│  ┌──────────────────────────────────────────────────┐ │
│  │  [SQLite] / [PostgreSQL] / [MySQL]              │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────┐
│      Results Returned to SQLAlchemy                   │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────┐
│      ORM Objects Created/Updated                      │
│      (Result rows → Model instances)                   │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────┐
│      Results Returned to Route Handler                │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────┐
│      Session Closed, Connection Returned to Pool      │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────┐
│      Response Sent to Client                          │
└────────────────────────────────────────────────────────┘
```

---

## 5. Connection Pool Architecture

### SQLite (Single Connection)
```
┌──────────────────────────────────────┐
│      Application (Flask)             │
└────────┬─────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────┐
│   SQLAlchemy Engine                  │
│   (StaticPool - Single Connection)   │
└────────┬─────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────┐
│   sqlite3 Driver                     │
└────────┬─────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────┐
│   SQLite Database File               │
│   (data/market_data.db)              │
└──────────────────────────────────────┘
```

### PostgreSQL/MySQL (Connection Pool)
```
┌────────────────────────────────────────────┐
│         Application (Flask)                │
│  ┌─────────────┐  ┌─────────────┐        │
│  │ Thread 1    │  │ Thread 2    │        │
│  │ Request A   │  │ Request B   │        │
│  └──────┬──────┘  └──────┬──────┘        │
└─────────┼─────────────────┼──────────────┘
          │                 │
          ↓                 ↓
   ┌───────────────────────────────┐
   │  SQLAlchemy QueuePool         │
   │  (pool_size=20)               │
   │  ┌─────┐  ┌─────┐  ┌─────┐   │
   │  │ Cx1 │  │ Cx2 │  │Cx20 │   │ Available
   │  └─────┘  └─────┘  └─────┘   │
   │                               │
   │  max_overflow=40 (temp expand)│
   └───────────────────────────────┘
          │
          ↓
   ┌───────────────────────────────┐
   │  psycopg2 / PyMySQL Driver    │
   └───────────────────────────────┘
          │
          ↓
   ┌───────────────────────────────┐
   │  Database Server              │
   │  (PostgreSQL/MySQL)           │
   └───────────────────────────────┘
```

---

## 6. File Structure Evolution

### Before Phase 0
```
app/
├── api/
│   ├── routes.py          (raw SQL queries)
│   └── auth.py
├── core/
│   ├── data_manager.py    (raw SQL queries)
│   ├── portfolio_manager.py
│   └── signal_generator.py
├── web/
│   └── dashboard.py
└── __init__.py

config/
├── database.py            (sqlite3 connections)
└── settings.py
```

### After Phase 0
```
app/
├── models/                (NEW - ORM Models)
│   ├── __init__.py
│   ├── base.py
│   ├── market_data.py
│   ├── trading.py
│   ├── portfolio.py
│   └── system.py
├── db.py                  (NEW - Database Manager)
├── api/
│   ├── routes.py          (uses ORM)
│   └── auth.py
├── core/
│   ├── data_manager.py    (uses ORM)
│   ├── portfolio_manager.py
│   └── signal_generator.py
├── web/
│   └── dashboard.py
└── __init__.py

config/
├── database.py            (kept for backward compat)
└── settings.py            (updated with DB config)

migrations/                (NEW - Alembic)
├── env.py
├── script.py.mako
└── versions/
    └── 001_initial_schema.py

alembic.ini                (NEW - Alembic config)
.env.example               (NEW - Environment vars)
PHASE_0_SPECIFICATION.md   (NEW - This spec)
```

---

## 7. Migration Path: Raw SQL → ORM

### Current: Raw SQL in data_manager.py
```python
def get_daily_data(self, ticker: str, limit: int = 100) -> pd.DataFrame:
    cursor = self.conn.cursor()
    cursor.execute(
        "SELECT * FROM daily_data WHERE ticker = ? ORDER BY date DESC LIMIT ?",
        (ticker, limit)
    )
    rows = cursor.fetchall()
    # Manual conversion to DataFrame
    return pd.DataFrame(rows, columns=[...])
```

### After Phase 0: ORM in data_manager.py
```python
def get_daily_data(self, ticker: str, limit: int = 100) -> pd.DataFrame:
    session = get_session()
    try:
        results = session.query(DailyData) \
            .filter(DailyData.ticker == ticker) \
            .order_by(desc(DailyData.date)) \
            .limit(limit) \
            .all()

        # Convert ORM objects to DataFrame
        df = pd.DataFrame([
            {
                'ticker': r.ticker,
                'date': r.date,
                'open': float(r.open),
                'high': float(r.high),
                'low': float(r.low),
                'close': float(r.close),
                'volume': r.volume,
            }
            for r in results
        ])
        return df
    finally:
        session.close()
```

---

## 8. Testing Architecture

```
┌─────────────────────────────────────┐
│     Test Suite (pytest)             │
├─────────────────────────────────────┤
│  Unit Tests                         │
│  ├── test_models.py                 │
│  │   └── Test ORM models in memory  │
│  └── test_db.py                     │
│      └── Test DatabaseManager       │
│                                     │
│  Integration Tests                  │
│  ├── test_routes.py                 │
│  │   └── Test API with database     │
│  └── test_migrations.py             │
│      └── Test upgrade/downgrade     │
│                                     │
│  Multi-Database Tests               │
│  └── test_all_databases.py          │
│      ├── SQLite in-memory           │
│      ├── PostgreSQL (if available)  │
│      └── MySQL (if available)       │
└──────────┬──────────────────────────┘
           │
           ↓
    ┌──────────────────────┐
    │  In-Memory DB        │
    │  (sqlite:///:memory)  │
    │                      │
    │  Fast, isolated,     │
    │  no side effects     │
    └──────────────────────┘
```

---

## 9. Database Type Selection Flow

```
                    ┌─────────────────────┐
                    │ Application Starts  │
                    └──────────┬──────────┘
                               │
                               ↓
                    ┌─────────────────────┐
                    │ Check Environment   │
                    │ DATABASE_TYPE var   │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ↓                 ↓                 ↓
        ┌────────┐        ┌────────┐      ┌────────────┐
        │SQLite? │        │PostgreSQL?   │MySQL?      │
        └───┬────┘        └────┬────┘    └─────┬──────┘
            │                  │              │
            ↓                  ↓              ↓
    ┌───────────────┐ ┌──────────────┐ ┌──────────────┐
    │sqlite:///path │ │postgresql:// │ │mysql://      │
    │               │ │user:pass@    │ │user:pass@    │
    │File-based DB  │ │host/dbname   │ │host/dbname   │
    │               │ │              │ │              │
    │Development    │ │Production    │ │Production    │
    │Single-user    │ │Multi-user    │ │Multi-user    │
    │No setup       │ │Port 5432     │ │Port 3306     │
    │               │ │High capacity │ │High capacity │
    └───────────────┘ └──────────────┘ └──────────────┘
            │                  │              │
            └─────────────────┬┴──────────────┘
                              │
                              ↓
                    ┌──────────────────┐
                    │ Create Engine    │
                    │ with SQLAlchemy  │
                    └────────┬─────────┘
                             │
                             ↓
                    ┌──────────────────┐
                    │ Initialize Tables│
                    │ (if not exist)   │
                    └────────┬─────────┘
                             │
                             ↓
                    ┌──────────────────┐
                    │ Ready to Use!    │
                    └──────────────────┘
```

---

This architecture enables:
✅ Type-safe database operations
✅ Multi-database support (SQLite → PostgreSQL → MySQL)
✅ Automatic migrations and schema versioning
✅ Connection pooling and performance optimization
✅ Foundation for multi-user support (Phase 1)
✅ Full backward compatibility with existing data

