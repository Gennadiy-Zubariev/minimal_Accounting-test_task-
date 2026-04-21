# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
streamlit run app.py          # local dev
docker compose up -d          # via Docker (port 8501)
```

Reset the database (wipes all data):
```bash
rm data/accounting.db
```

## Architecture

This is a double-entry bookkeeping app built with Streamlit + SQLite. There are no tests and no linter configured.

**Layer responsibilities:**

| File | Role |
|---|---|
| `models.py` | Pure dataclasses + enums. No logic, no DB. Shared vocabulary across all layers. |
| `storage.py` | All SQL lives here. `Database` class returns domain model instances, never raw tuples. Amounts stored as TEXT to preserve `Decimal` precision. |
| `ledger.py` | Posting engine. `post_transaction()` is the only public write entry point. `_build_lines()` uses `match/case` on `TransactionType` to determine DR/CR accounts. |
| `reports.py` | Pure aggregation functions. Accept `Database`, return typed report models. No UI. |
| `ui_helpers.py` | Shared widgets — `partner_search_widget` is used on every page that needs a partner picker. |
| `pages/*.py` | One `render(db: Database)` function per page. Registered in `app.py`. |

**Data flow for a new transaction:**

```
pages/transaction.py  →  ledger.post_transaction()
                               ↓
                         ledger._build_lines()   ← TransactionType decides DR/CR
                               ↓
                         storage.Database (atomic: 1 Transaction + 2 JournalEntry rows)
```

**Chart of accounts** is fixed (seeded in `storage.py::_DDL`, never user-editable):
- 1000 Готівка · 1100 Дебіторська · 2000 Кредиторська · 3000 Капітал · 4000 Дохід · 5000 Витрати

**`TransactionType` enum** (in `models.py`) is the central dispatch key — adding a new transaction type requires: a new enum value, a new posting rule in `ledger._build_lines()`, and a `.label` entry.

## Key constraints

- `OPENING_BALANCE` transactions are excluded from the normal transaction UI (`_SELECTABLE_TYPES` in `pages/transaction.py`). Opening balances have their own page and use `ledger.post_opening_balances()`, not `post_transaction()`.
- Streamlit re-runs the entire script on every interaction. `@st.cache_resource` on `get_db()` in `app.py` ensures a single DB connection per server process.
- DB path is resolved as `Path(__file__).parent / "data" / "accounting.db"` — always absolute, so the app can be launched from any working directory.
- WAL mode is enabled (`PRAGMA journal_mode=WAL`) — the `.db-shm` and `.db-wal` sibling files are normal SQLite behaviour, not separate databases.
- Never write to `st.session_state[widget_key]` after the widget with that key has already been rendered in the current script run — Streamlit raises an error.
