"""
============================================================================
services.py — БІЗНЕС-ЛОГІКА І ВАЛІДАЦІЯ
============================================================================

ЩО ЦЕ ЗА ФАЙЛ:
    Проміжний шар між UI (сторінками) і БД. Тут:
    1) Перевіряємо, чи коректні дані, що прийшли з форми.
    2) Звертаємось до chart.py, щоб дізнатись Дт/Кт.
    3) Кажемо database.py — "запиши".

ДЕ ПРАВИТИ ЩО:
    • Хочу щоб ДАТА ОПЕРАЦІЇ НЕ БУЛА > СЬОГОДНІ
      → функція register_operation(), блок "ПЕРЕВІРКА ДАТИ".

    • Хочу ЗМІНИТИ ФОРМАТ ЄДРПОУ (наприклад, 12 цифр)
      → функція create_counterparty(), блок "ПЕРЕВІРКА ЄДРПОУ".

    • Хочу ЗАБОРОНИТИ СУМИ більше 1 000 000
      → функція register_operation(), блок "ПЕРЕВІРКА СУМИ".

    • Хочу додати ЩЕ ЯКУСЬ ПЕРЕВІРКУ перед записом
      → сюди ж, у register_operation() або create_counterparty().
============================================================================
"""

from datetime import date

from app.chart import build_posting, needs_counterparty
from app import database as db


class AppError(Exception):
    """Помилка валідації або бізнес-правила. Показується користувачу як текст."""


# ---------------------------------------------------------------------------
# СТВОРЕННЯ КОНТРАГЕНТА
# ---------------------------------------------------------------------------
def create_counterparty(name: str, edrpou: str) -> int:
    """
    Валідує дані і додає контрагента в БД. Повертає id.

    Контрагент НЕ має типу (клієнт/постачальник). Одна й та сама фірма
    може бути і клієнтом, і постачальником — залежно від операції.
    """
    name = (name or "").strip()
    edrpou = (edrpou or "").strip()

    # --- ПЕРЕВІРКА НАЗВИ ---
    if not name:
        raise AppError("Назва контрагента не може бути порожньою.")

    # --- ПЕРЕВІРКА ЄДРПОУ ---
    # Для ЮО — 8 цифр, для ФОП — 10 цифр (ІПН).
    if not edrpou:
        raise AppError("Код ЄДРПОУ не може бути порожнім.")
    if not edrpou.isdigit() or len(edrpou) not in (8, 10):
        raise AppError("Код ЄДРПОУ має містити лише цифри (8 або 10 знаків).")

    # --- ПЕРЕВІРКА ДУБЛЮВАННЯ ---
    if db.get_counterparty_by_edrpou(edrpou) is not None:
        raise AppError(f"Контрагент з ЄДРПОУ {edrpou} вже існує.")

    return db.add_counterparty(name=name, edrpou=edrpou)


# ---------------------------------------------------------------------------
# РЕЄСТРАЦІЯ ОПЕРАЦІЇ
# ---------------------------------------------------------------------------
def register_operation(
    op_date: date,
    op_type: str,
    amount: float,
    description: str = "",
    counterparty_id: int | None = None,
    opening_balance_account: str | None = None,
) -> int:
    """
    Записує операцію і її проводку.
    Послідовність: валідація → chart.build_posting() → database.add_operation_with_entries().
    """

    # ========== ПЕРЕВІРКА СУМИ ==========
    if amount is None or amount <= 0:
        raise AppError("Сума має бути більшою за нуль.")

    # ========== ПЕРЕВІРКА ДАТИ ==========
    if op_date is None:
        raise AppError("Вкажіть дату операції.")
    if op_date > date.today():
        raise AppError("Дата операції не може бути в майбутньому.")

    # ========== ПЕРЕВІРКА ТИПУ І КОНТРАГЕНТА ==========
    if op_type == "opening_balance":
        if opening_balance_account in ("1100", "2000") and counterparty_id is None:
            raise AppError(
                "Для залишку по дебіторській/кредиторській заборгованості "
                "треба вказати контрагента."
            )
    else:
        if needs_counterparty(op_type) and counterparty_id is None:
            raise AppError("Для цього типу операції треба обрати контрагента.")

    # ========== ВИЗНАЧЕННЯ Дт/Кт ==========
    debit_account, credit_account = build_posting(
        op_type=op_type,
        opening_balance_account=opening_balance_account,
    )

    # ========== ЗАПИС У БД ==========
    description = (description or "").strip()
    return db.add_operation_with_entries(
        op_date=op_date,
        op_type=op_type,
        amount=float(amount),
        description=description,
        counterparty_id=counterparty_id,
        debit_account=debit_account,
        credit_account=credit_account,
    )