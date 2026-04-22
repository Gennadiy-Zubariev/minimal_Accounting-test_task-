import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from app.chart import ACCOUNTS


_DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "accounting.db"
DB_PATH = Path(os.environ.get("ACCOUNTING_DB_PATH", str(_DEFAULT_DB_PATH)))


@contextmanager
def get_conn():
    """Open a SQLite connection; commit on success, rollback on error, always close."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables if they do not yet exist. Safe to call on every startup."""
    sql = """
    CREATE TABLE IF NOT EXISTS counterparties (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        name   TEXT NOT NULL,
        edrpou TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS operations (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        op_date         DATE NOT NULL,
        op_type         TEXT NOT NULL,
        amount          REAL NOT NULL CHECK (amount > 0),
        description     TEXT NOT NULL DEFAULT '',
        counterparty_id INTEGER REFERENCES counterparties(id)
    );

    CREATE TABLE IF NOT EXISTS journal_entries (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_id    INTEGER NOT NULL REFERENCES operations(id) ON DELETE CASCADE,
        entry_date      DATE NOT NULL,
        debit_account   TEXT NOT NULL,
        credit_account  TEXT NOT NULL,
        amount          REAL NOT NULL CHECK (amount > 0),
        description     TEXT NOT NULL DEFAULT '',
        counterparty_id INTEGER REFERENCES counterparties(id)
    );

    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_je_date    ON journal_entries(entry_date);
    CREATE INDEX IF NOT EXISTS idx_je_debit   ON journal_entries(debit_account);
    CREATE INDEX IF NOT EXISTS idx_je_credit  ON journal_entries(credit_account);
    CREATE INDEX IF NOT EXISTS idx_je_partner ON journal_entries(counterparty_id);
    """
    with get_conn() as conn:
        conn.executescript(sql)


def is_database_empty() -> bool:
    """Return True if no operations have been recorded yet."""
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM operations").fetchone()
        return row["c"] == 0


def add_counterparty(name: str, edrpou: str) -> int:
    """Insert a new counterparty and return its id. Raises IntegrityError on duplicate EDRPOU."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO counterparties (name, edrpou) VALUES (?, ?)",
            (name.strip(), edrpou.strip()),
        )
        return cur.lastrowid


def get_counterparty_by_edrpou(edrpou: str):
    """Return a counterparty dict by EDRPOU, or None if not found."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, edrpou FROM counterparties WHERE edrpou = ?",
            (edrpou.strip(),),
        ).fetchone()
        return dict(row) if row else None


def get_counterparty(cp_id: int):
    """Return a counterparty dict by id, or None if not found."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, edrpou FROM counterparties WHERE id = ?",
            (cp_id,),
        ).fetchone()
        return dict(row) if row else None


def list_counterparties(query: str = "") -> list:
    """Return all counterparties matching the substring query (name or EDRPOU). Empty query returns all."""
    sql = "SELECT id, name, edrpou FROM counterparties WHERE 1=1"
    params = []

    if query.strip():
        sql += " AND (name LIKE ? COLLATE NOCASE OR edrpou LIKE ?)"
        like = f"%{query.strip()}%"
        params.extend([like, like])

    sql += " ORDER BY name ASC"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def add_operation_with_entries(
    op_date: date,
    op_type: str,
    amount: float,
    description: str,
    counterparty_id: int | None,
    debit_account: str,
    credit_account: str,
) -> int:
    """Atomically insert an operation and its journal entry. Return the operation id."""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO operations
               (op_date, op_type, amount, description, counterparty_id)
               VALUES (?, ?, ?, ?, ?)""",
            (op_date.isoformat(), op_type, amount, description, counterparty_id),
        )
        op_id = cur.lastrowid

        conn.execute(
            """INSERT INTO journal_entries
               (operation_id, entry_date, debit_account, credit_account,
                amount, description, counterparty_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (op_id, op_date.isoformat(), debit_account, credit_account,
             amount, description, counterparty_id),
        )
        return op_id


def list_operations(date_from: date = None, date_to: date = None) -> list:
    """Return operations as a list of dicts, optionally filtered by date range."""
    sql = """
        SELECT o.id, o.op_date, o.op_type, o.amount, o.description,
               o.counterparty_id,
               c.name AS counterparty_name, c.edrpou AS counterparty_edrpou
        FROM operations o
        LEFT JOIN counterparties c ON c.id = o.counterparty_id
        WHERE 1=1
    """
    params = []
    if date_from:
        sql += " AND o.op_date >= ?"
        params.append(date_from.isoformat())
    if date_to:
        sql += " AND o.op_date <= ?"
        params.append(date_to.isoformat())
    sql += " ORDER BY o.op_date DESC, o.id DESC"

    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def list_journal_entries(
    date_from: date = None,
    date_to: date = None,
    account_code: str = None,
    counterparty_id: int = None,
    account_codes: list | None = None,
) -> list:
    """
    Return journal entries with optional filters.

    account_code: match entries where this account appears on either side.
    account_codes: same but for a list of accounts (e.g. ["1100", "2000"]).
    """
    sql = """
        SELECT je.id, je.entry_date, je.debit_account, je.credit_account,
               je.amount, je.description, je.counterparty_id,
               c.name AS counterparty_name,
               o.op_type
        FROM journal_entries je
        LEFT JOIN counterparties c ON c.id = je.counterparty_id
        LEFT JOIN operations o     ON o.id = je.operation_id
        WHERE 1=1
    """
    params = []
    if date_from:
        sql += " AND je.entry_date >= ?"
        params.append(date_from.isoformat())
    if date_to:
        sql += " AND je.entry_date <= ?"
        params.append(date_to.isoformat())
    if account_code:
        sql += " AND (je.debit_account = ? OR je.credit_account = ?)"
        params.extend([account_code, account_code])
    if account_codes:
        placeholders = ",".join("?" * len(account_codes))
        sql += (f" AND (je.debit_account IN ({placeholders}) "
                f"     OR je.credit_account IN ({placeholders}))")
        params.extend(account_codes)
        params.extend(account_codes)
    if counterparty_id is not None:
        sql += " AND je.counterparty_id = ?"
        params.append(counterparty_id)
    sql += " ORDER BY je.entry_date ASC, je.id ASC"

    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def account_balances(date_from: date = None, date_to: date = None) -> list:
    """Return balances for all accounts, optionally filtered by date range."""
    entries = list_journal_entries(date_from=date_from, date_to=date_to)

    totals = {code: {"dr": 0.0, "cr": 0.0} for code in ACCOUNTS}
    for e in entries:
        totals[e["debit_account"]]["dr"] += e["amount"]
        totals[e["credit_account"]]["cr"] += e["amount"]

    result = []
    for code, info in ACCOUNTS.items():
        dr = totals[code]["dr"]
        cr = totals[code]["cr"]
        if info["type"] in ("asset", "expense"):
            balance = dr - cr
        else:
            balance = cr - dr
        result.append({
            "code": code,
            "name": info["name"],
            "type": info["type"],
            "debit_total": dr,
            "credit_total": cr,
            "balance": balance,
        })
    return result


def get_balance(account_code: str, date_from=None, date_to=None) -> float:
    """Return the balance of a single account."""
    for b in account_balances(date_from, date_to):
        if b["code"] == account_code:
            return b["balance"]
    return 0.0


def profit_and_loss(date_from: date = None, date_to: date = None) -> dict:
    """Return a P&L summary: income, expense, and net_profit."""
    balances = account_balances(date_from, date_to)
    income_rows = [b for b in balances if b["type"] == "income"]
    expense_rows = [b for b in balances if b["type"] == "expense"]

    income_total = sum(b["balance"] for b in income_rows)
    expense_total = sum(b["balance"] for b in expense_rows)

    return {
        "income": income_total,
        "expense": expense_total,
        "net_profit": income_total - expense_total,
        "income_rows": income_rows,
        "expense_rows": expense_rows,
    }


def partner_ledger(counterparty_id: int, date_from=None, date_to=None) -> dict | None:
    """
    Return a chronological ledger for one partner covering both AR (1100) and AP (2000).

    Returns:
        {
          "counterparty": {...},
          "rows": [...],
          "receivable_balance": float,
          "payable_balance": float,
        }
    Returns None if the counterparty does not exist.
    """
    cp = get_counterparty(counterparty_id)
    if cp is None:
        return None

    entries = list_journal_entries(
        date_from=date_from,
        date_to=date_to,
        account_codes=["1100", "2000"],
        counterparty_id=counterparty_id,
    )

    rows = []
    running_ar = 0.0
    running_ap = 0.0

    for e in entries:
        touches_1100 = e["debit_account"] == "1100" or e["credit_account"] == "1100"
        touches_2000 = e["debit_account"] == "2000" or e["credit_account"] == "2000"

        debit_amount = 0.0
        credit_amount = 0.0

        if touches_1100:
            role = "receivable"
            dr_on_1100 = e["amount"] if e["debit_account"] == "1100" else 0.0
            cr_on_1100 = e["amount"] if e["credit_account"] == "1100" else 0.0
            running_ar += dr_on_1100 - cr_on_1100
            debit_amount = dr_on_1100
            credit_amount = cr_on_1100
        elif touches_2000:
            role = "payable"
            dr_on_2000 = e["amount"] if e["debit_account"] == "2000" else 0.0
            cr_on_2000 = e["amount"] if e["credit_account"] == "2000" else 0.0
            running_ap += cr_on_2000 - dr_on_2000
            debit_amount = dr_on_2000
            credit_amount = cr_on_2000
        else:
            continue

        rows.append({
            "date": e["entry_date"],
            "op_type": e["op_type"],
            "description": e["description"],
            "role": role,
            "debit": debit_amount,
            "credit": credit_amount,
            "running_receivable": running_ar,
            "running_payable": running_ap,
        })

    return {
        "counterparty": cp,
        "rows": rows,
        "receivable_balance": running_ar,
        "payable_balance": running_ap,
    }


def partners_summary(date_from=None, date_to=None) -> list:
    """Return a summary of receivable and payable balances for every counterparty."""
    result = []
    for cp in list_counterparties():
        ledger = partner_ledger(cp["id"], date_from=date_from, date_to=date_to)
        if ledger is None:
            continue
        result.append({
            "id": cp["id"],
            "name": cp["name"],
            "edrpou": cp["edrpou"],
            "receivable_balance": ledger["receivable_balance"],
            "payable_balance": ledger["payable_balance"],
        })
    return result


def get_setting(key: str, default: str = None) -> str | None:
    """Return the stored setting value, or default if not set."""
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    """Upsert a key-value setting."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )
