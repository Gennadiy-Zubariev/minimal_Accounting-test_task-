"""
============================================================================
database.py — УСЯ РОБОТА З БАЗОЮ ДАНИХ (SQLite)
============================================================================

ЩО ЦЕ ЗА ФАЙЛ:
    Тут у одному місці:
    1) Підключення до SQLite і створення таблиць (init_db).
    2) Функції для запису даних: add_counterparty, add_operation_with_entries.
    3) Функції для читання даних: list_counterparties, list_operations, ...
    4) Функції для звітів: account_balances, profit_and_loss, partner_ledger.

ДЕ ПРАВИТИ ЩО:
    • Хочу додати НОВЕ ПОЛЕ в таблицю (напр. телефон контрагента)
      → знайти CREATE TABLE у init_db() і додати колонку
      → потім оновити add_counterparty() і list_counterparties().
      УВАГА: якщо БД вже створена, треба її видалити (data/accounting.db)
      або робити ALTER TABLE вручну — ми для простоти не робимо міграцій.

    • Хочу ЗМІНИТИ, як рахується сальдо
      → функція account_balances() внизу.

    • Хочу ЗМІНИТИ логіку книги партнера
      → функція partner_ledger().

    • Хочу ПЕРЕВІРИТИ, чи БД ПОРОЖНЯ (для стартової сторінки)
      → функція is_database_empty().

ВАЖЛИВО — МОДЕЛЬ КОНТРАГЕНТІВ:
    Контрагент НЕ має типу (клієнт/постачальник). Один і той самий
    контрагент може виступати в обох ролях — продавати нам і купувати у нас.
    Роль визначається типом операції і рахунками у проводці:
      • рухи по 1100 (дебіторка) — коли контрагент виступає як клієнт;
      • рухи по 2000 (кредиторка) — коли контрагент виступає як постачальник.
    Книга партнера показує обидві лінії одночасно.
============================================================================
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

# Імпорт з нашого файлу chart.py — для обчислення сальдо треба знати тип рахунку.
from app.chart import ACCOUNTS


# ---------------------------------------------------------------------------
# 1. ШЛЯХ ДО ФАЙЛУ БД
# ---------------------------------------------------------------------------
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "accounting.db"
DB_PATH = Path(os.environ.get("ACCOUNTING_DB_PATH", str(_DEFAULT_DB_PATH)))


# ---------------------------------------------------------------------------
# 2. ДОПОМІЖНИЙ КОНТЕКСТНИЙ МЕНЕДЖЕР ДЛЯ ПІДКЛЮЧЕННЯ
# ---------------------------------------------------------------------------
@contextmanager
def get_conn():
    """
    Відкриває підключення до SQLite, а при виході — commit/rollback/close.

    Використання:
        with get_conn() as conn:
            conn.execute("INSERT ...")
    """
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


# ---------------------------------------------------------------------------
# 3. СТВОРЕННЯ ТАБЛИЦЬ (викликається один раз при старті додатку)
# ---------------------------------------------------------------------------
def init_db():
    """Створює таблиці, якщо їх ще нема. Безпечно викликати щоразу."""
    sql = """
    -- Контрагенти: назва + ЄДРПОУ. БЕЗ поля kind — контрагент може
    -- виступати і як клієнт, і як постачальник у різних операціях.
    CREATE TABLE IF NOT EXISTS counterparties (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        name   TEXT NOT NULL,
        edrpou TEXT NOT NULL UNIQUE
    );

    -- Операції (верхній рівень: одна бізнес-подія).
    CREATE TABLE IF NOT EXISTS operations (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        op_date         DATE NOT NULL,
        op_type         TEXT NOT NULL,           -- код з chart.py OPERATION_TYPES
        amount          REAL NOT NULL CHECK (amount > 0),
        description     TEXT NOT NULL DEFAULT '',
        counterparty_id INTEGER REFERENCES counterparties(id)
    );

    -- Проводки (одна операція → 1 або більше проводок Дт/Кт).
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
    """Чи немає ще жодної операції в БД (для стартової сторінки)."""
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM operations").fetchone()
        return row["c"] == 0


# ===========================================================================
# === КОНТРАГЕНТИ ===========================================================
# ===========================================================================

def add_counterparty(name: str, edrpou: str) -> int:
    """
    Додає нового контрагента. Повертає id.
    Якщо ЄДРПОУ уже є — sqlite кине IntegrityError (ловимо в services.py).
    """
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO counterparties (name, edrpou) VALUES (?, ?)",
            (name.strip(), edrpou.strip()),
        )
        return cur.lastrowid


def get_counterparty_by_edrpou(edrpou: str):
    """Повертає dict контрагента або None, якщо не знайдено."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, edrpou FROM counterparties WHERE edrpou = ?",
            (edrpou.strip(),),
        ).fetchone()
        return dict(row) if row else None


def get_counterparty(cp_id: int):
    """Повертає dict контрагента за id або None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, edrpou FROM counterparties WHERE id = ?",
            (cp_id,),
        ).fetchone()
        return dict(row) if row else None


def list_counterparties(query: str = "") -> list:
    """
    Шукає контрагентів за підрядком у назві або ЄДРПОУ.
    query = "" → всі.
    Повертає список dict-ів.
    """
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


# ===========================================================================
# === ОПЕРАЦІЇ І ПРОВОДКИ ===================================================
# ===========================================================================

def add_operation_with_entries(
    op_date: date,
    op_type: str,
    amount: float,
    description: str,
    counterparty_id: int | None,
    debit_account: str,
    credit_account: str,
) -> int:
    """Атомарно додає операцію і її проводку. Повертає id операції."""
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
    """Повертає операції у вигляді списку dict-ів з даними контрагента."""
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
    Повертає проводки з фільтрами. Використовується для звітів.
    account_code: фільтр по одному рахунку (у Дт АБО Кт).
    account_codes: фільтр по списку рахунків (у Дт АБО Кт).
                   Зручно для книги партнера: передаємо ["1100", "2000"].
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
        # Формуємо "... IN (?, ?, ?)" для обох колонок.
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


# ===========================================================================
# === ЗВІТИ =================================================================
# ===========================================================================

def account_balances(date_from: date = None, date_to: date = None) -> list:
    """Залишки по всіх рахунках. Див. логіку знаків у docstring-у функції."""
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
    """Сальдо одного рахунку. Зручний шорткат для Dashboard."""
    for b in account_balances(date_from, date_to):
        if b["code"] == account_code:
            return b["balance"]
    return 0.0


def profit_and_loss(date_from: date = None, date_to: date = None) -> dict:
    """P&L: доходи, витрати, net_profit."""
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
    Книга одного партнера: хронологія рухів і по дебіторці (1100), і по
    кредиторці (2000). Один контрагент може мати рухи і в тій, і в іншій ролі.

    Повертає:
        {
          "counterparty": {...},
          "rows": [...],              # хронологія (обидві ролі разом)
          "receivable_balance": ...,  # скільки винен нам (по 1100)
          "payable_balance": ...,     # скільки ми винні (по 2000)
        }

    rows кожен елемент:
        date, op_type, description, role ('receivable'|'payable'),
        debit, credit, running_balance_receivable, running_balance_payable
    """
    cp = get_counterparty(counterparty_id)
    if cp is None:
        return None

    # Беремо всі рухи по 1100 АБО 2000 для цього контрагента.
    entries = list_journal_entries(
        date_from=date_from,
        date_to=date_to,
        account_codes=["1100", "2000"],
        counterparty_id=counterparty_id,
    )

    rows = []
    running_ar = 0.0  # наростаюче по дебіторці
    running_ap = 0.0  # наростаюче по кредиторці

    for e in entries:
        # Визначаємо, по якому рахунку цей запис стосується партнера.
        touches_1100 = e["debit_account"] == "1100" or e["credit_account"] == "1100"
        touches_2000 = e["debit_account"] == "2000" or e["credit_account"] == "2000"

        # Оновлюємо running balance по тому рахунку, якого стосується операція.
        debit_amount = 0.0
        credit_amount = 0.0

        if touches_1100:
            role = "receivable"
            dr_on_1100 = e["amount"] if e["debit_account"] == "1100" else 0.0
            cr_on_1100 = e["amount"] if e["credit_account"] == "1100" else 0.0
            # 1100 — актив: +Дт, −Кт.
            running_ar += dr_on_1100 - cr_on_1100
            debit_amount = dr_on_1100
            credit_amount = cr_on_1100
        elif touches_2000:
            role = "payable"
            dr_on_2000 = e["amount"] if e["debit_account"] == "2000" else 0.0
            cr_on_2000 = e["amount"] if e["credit_account"] == "2000" else 0.0
            # 2000 — пасив: +Кт, −Дт.
            running_ap += cr_on_2000 - dr_on_2000
            debit_amount = dr_on_2000
            credit_amount = cr_on_2000
        else:
            # Не стосується ні 1100, ні 2000 — не додаємо в рядки книги.
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
    """
    Підсумок по всіх партнерах: для кожного — дебіторка і кредиторка.
    Використовується у верхній таблиці сторінки "Книга партнерів".
    """
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


# ===========================================================================
# === НАЛАШТУВАННЯ (простий key-value) ======================================
# ===========================================================================

def get_setting(key: str, default: str = None) -> str | None:
    """Повертає значення налаштування або default."""
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    """Зберігає налаштування (upsert)."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )