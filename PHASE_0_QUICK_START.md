# Phase 0: Quick Start Guide

## Overview

This document provides a quick summary of Phase 0 - Database Abstraction Layer Implementation.

**Full Specification**: See `PHASE_0_SPECIFICATION.md`

---

## What is Phase 0?

Transform the database layer from raw SQLite to a production-grade **SQLAlchemy ORM** + **Alembic migrations** system.

### Current State
```
Raw SQL → sqlite3 → SQLite Only
```

### Target State
```
SQLAlchemy ORM → SQLAlchemy Dialects → [SQLite | PostgreSQL | MySQL]
```

---

## Key Deliverables

### 1. SQLAlchemy Models (`app/models/`)
- Type-safe database models
- 7 existing tables → 7 ORM models
- Automatic timestamp tracking
- Index and constraint definitions

### 2. Database Manager (`app/db.py`)
- Connection pooling
- Multi-database support
- Session management
- Context managers for safe operations

### 3. Alembic Migrations (`migrations/`)
- Schema versioning framework
- Auto-generate migrations from model changes
- Upgrade/downgrade support
- Version control for database schema

### 4. Configuration (`config/settings.py`, `.env.example`)
- Database type selection
- Connection string configuration
- Pool and performance settings

---

## Installation Steps

### 1. Install Dependencies
```bash
pip install SQLAlchemy>=2.0.0 Alembic>=1.12.0 psycopg2-binary>=2.9.0 PyMySQL>=1.1.0
```

### 2. Create File Structure
```
app/models/
├── __init__.py
├── base.py                 # Base class + mixin
├── market_data.py          # DailyData, IntradayData, Metadata
├── trading.py              # SignalHistory, PortfolioPerformance
├── portfolio.py            # PortfolioPosition
└── system.py               # SystemEvent

app/db.py                    # DatabaseManager class
migrations/                  # Alembic migrations directory
```

### 3. Initialize Alembic
```bash
alembic init -t sqlalchemy migrations
# Update migrations/env.py with proper configuration
```

### 4. Create Initial Migration
```bash
alembic revision --autogenerate -m "initial schema"
```

---

## Core Components

### DatabaseManager Class
Located in `app/db.py`

```python
from app.db import init_db_manager, get_session

# Initialize at startup
db_manager = init_db_manager()

# Use in code
with db_manager.session_context() as session:
    result = session.query(DailyData).first()
```

### Model Definition Example
Located in `app/models/market_data.py`

```python
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class DailyData(Base, TimestampMixin):
    __tablename__ = "daily_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10))
    date: Mapped[date] = mapped_column()
    close: Mapped[Decimal] = mapped_column()
    # ... other fields ...
```

---

## Database Configuration

### Using Environment Variables

**SQLite (Development - Default)**:
```bash
DATABASE_TYPE=sqlite
DATABASE_PATH=data/market_data.db
```

**PostgreSQL (Production)**:
```bash
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:pass@localhost:5432/traderrr
```

**MySQL/MariaDB (Production)**:
```bash
DATABASE_TYPE=mysql
DATABASE_URL=mysql://user:pass@localhost:3306/traderrr
```

### Or Use Direct URL
```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

---

## Common Operations

### Create Tables
```python
from app.db import init_db_manager

db = init_db_manager()
# Tables are created automatically
```

### Query Examples
```python
from app.db import get_session
from app.models import DailyData
from sqlalchemy import desc

with get_session() as session:
    # Single record
    last_aapl = session.query(DailyData) \
        .filter(DailyData.ticker == "AAPL") \
        .order_by(desc(DailyData.date)) \
        .first()

    # Multiple records
    all_data = session.query(DailyData).all()

    # With conditions
    recent = session.query(DailyData) \
        .filter(DailyData.date >= "2025-01-01") \
        .order_by(desc(DailyData.date)) \
        .all()
```

### Insert Data
```python
from app.db import get_session
from app.models import DailyData

with get_session() as session:
    daily = DailyData(
        ticker="AAPL",
        date="2025-01-01",
        open=150.0,
        close=153.0,
        high=155.0,
        low=149.0,
        volume=1000000
    )
    session.add(daily)
    session.commit()
```

### Update Data
```python
with get_session() as session:
    daily = session.query(DailyData) \
        .filter_by(ticker="AAPL") \
        .first()

    if daily:
        daily.close = 155.0
        session.commit()
```

### Delete Data
```python
with get_session() as session:
    session.query(DailyData) \
        .filter_by(ticker="AAPL") \
        .delete()
    session.commit()
```

---

## Migration Commands

### Create Migration After Model Changes
```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "Add user_id column"

# Review generated migration
# Then apply it:
alembic upgrade head
```

### View Migrations
```bash
# Show current revision
alembic current

# Show migration history
alembic history --verbose

# View SQL that will be executed
alembic upgrade --sql head
```

### Rollback Migrations
```bash
# Rollback one step
alembic downgrade -1

# Rollback specific number of steps
alembic downgrade -3

# Rollback to specific revision
alembic downgrade 001
```

---

## Testing Phase 0

### Unit Test Example
```python
import pytest
from app.db import DatabaseManager
from app.models import DailyData

@pytest.fixture
def test_db():
    db = DatabaseManager("sqlite:///:memory:")
    db.init_db()
    yield db
    db.close()

def test_insert_daily_data(test_db):
    with test_db.session_context() as session:
        daily = DailyData(
            ticker="TEST",
            date="2025-01-01",
            open=100.0,
            close=102.0,
            high=105.0,
            low=95.0,
            volume=1000000
        )
        session.add(daily)
        session.commit()

        result = session.query(DailyData).filter_by(ticker="TEST").first()
        assert result.close == 102.0
```

---

## Checklist

### Setup
- [ ] Install SQLAlchemy and Alembic
- [ ] Create `app/models/` directory structure
- [ ] Create `app/db.py` with DatabaseManager
- [ ] Initialize Alembic: `alembic init -t sqlalchemy migrations`
- [ ] Update `migrations/env.py`

### Implementation
- [ ] Create base model class (`base.py`)
- [ ] Create market data models (`market_data.py`)
- [ ] Create trading models (`trading.py`)
- [ ] Create portfolio models (`portfolio.py`)
- [ ] Create system models (`system.py`)
- [ ] Create `app/models/__init__.py`
- [ ] Update `config/settings.py` with DB config
- [ ] Create `.env.example`

### Testing
- [ ] Test SQLite connection
- [ ] Test table creation
- [ ] Test CRUD operations
- [ ] Test with PostgreSQL (if available)
- [ ] Run existing test suite
- [ ] Test migrations (upgrade & downgrade)

### Documentation
- [ ] Update README with database setup
- [ ] Document database configuration options
- [ ] Document migration procedures

---

## Performance Considerations

### Connection Pooling
- SQLite: Static pool (one connection)
- PostgreSQL/MySQL: QueuePool with 20 connections, 40 overflow

### Query Optimization
- Indexes created on high-query columns
- Use `session.expire_on_commit=False` for better performance
- Consider lazy loading vs eager loading for relationships

### Database Selection
- **SQLite**: Development, small deployments, single-user
- **PostgreSQL**: Production, multi-user, cloud-ready
- **MySQL/MariaDB**: Production option, simpler setup than PostgreSQL

---

## Common Issues & Solutions

### Issue: "No such table" error
**Cause**: Database not initialized
**Solution**: Call `init_db_manager()` before queries

### Issue: "Module not found" for models
**Cause**: `app/models/__init__.py` not created
**Solution**: Create the file and add model imports

### Issue: Connection pool exhausted
**Cause**: Sessions not properly closed
**Solution**: Use `session_context()` or ensure `session.close()` in finally block

### Issue: Migrations out of sync
**Cause**: Manual database changes vs model definitions
**Solution**: Always use migrations for schema changes

---

## Next Steps

1. **Implement Phase 0** according to specification
2. **Test thoroughly** with SQLite and PostgreSQL
3. **Migrate all raw SQL** to ORM queries (Phase 1 task)
4. **Begin Phase 1** - User/Auth system once Phase 0 is stable

---

**See full specification**: `PHASE_0_SPECIFICATION.md`
