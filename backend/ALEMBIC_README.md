# Alembic Database Migration Guide

This guide explains how to use Alembic for database migrations in your FastAPI project.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up your environment variables in `.env`:

```
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
# OR use Supabase credentials:
SUPABASE_URL=your_supabase_url
SUPABASE_DB_PASSWORD=your_supabase_db_password
```

## Alembic Commands

### Initialize Alembic (already done)

```bash
alembic init alembic
```

### Create a new migration

```bash
alembic revision --autogenerate -m "Add new table"
```

### Run migrations

```bash
alembic upgrade head
```

### Downgrade migrations

```bash
alembic downgrade -1  # Go back one migration
alembic downgrade base  # Go back to the beginning
```

### Check current migration status

```bash
alembic current
```

### View migration history

```bash
alembic history
```

## Project Structure

```
backend/
├── alembic/
│   ├── versions/           # Migration files
│   ├── env.py             # Alembic environment config
│   └── script.py.mako     # Migration template
├── app/
│   ├── database/
│   │   ├── config.py      # SQLAlchemy configuration
│   │   └── models.py      # SQLAlchemy models
│   ├── models/            # Pydantic models
│   └── services/          # Business logic
├── alembic.ini            # Alembic configuration
└── requirements.txt       # Dependencies
```

## Adding New Models

1. Create your SQLAlchemy model in `app/database/models.py`
2. Import the model in `alembic/env.py`
3. Generate migration: `alembic revision --autogenerate -m "Add new model"`
4. Review the generated migration file
5. Run migration: `alembic upgrade head`

## Hybrid Database Approach

This project supports both SQLAlchemy (for local/production PostgreSQL) and Supabase as a fallback. The `ItemService` automatically detects which database to use based on the presence of a database session.

- When `db` parameter is provided: Uses SQLAlchemy
- When `db` is None: Falls back to Supabase direct API calls

This allows for flexible deployment options and easy testing.
