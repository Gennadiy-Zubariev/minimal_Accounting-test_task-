from datetime import date

from app.chart import build_posting, needs_counterparty
from app import database as db


class AppError(Exception):
    """Validation or business-rule error shown to the user as a message."""


def create_counterparty(name: str, edrpou: str) -> int:
    """Validate and insert a new counterparty. Return its id."""
    name = (name or "").strip()
    edrpou = (edrpou or "").strip()

    if not name:
        raise AppError("Назва контрагента не може бути порожньою.")

    if not edrpou:
        raise AppError("Код ЄДРПОУ не може бути порожнім.")
    if not edrpou.isdigit() or len(edrpou) not in (8, 10):
        raise AppError("Код ЄДРПОУ має містити лише цифри (8 або 10 знаків).")

    if db.get_counterparty_by_edrpou(edrpou) is not None:
        raise AppError(f"Контрагент з ЄДРПОУ {edrpou} вже існує.")

    return db.add_counterparty(name=name, edrpou=edrpou)


def register_operation(
    op_date: date,
    op_type: str,
    amount: float,
    description: str = "",
    counterparty_id: int | None = None,
    opening_balance_account: str | None = None,
) -> int:
    """Validate and record an operation with its journal entry. Return the operation id."""
    if amount is None or amount <= 0:
        raise AppError("Сума має бути більшою за нуль.")

    if op_date is None:
        raise AppError("Вкажіть дату операції.")
    if op_date > date.today():
        raise AppError("Дата операції не може бути в майбутньому.")

    if op_type == "opening_balance":
        if opening_balance_account in ("1100", "2000") and counterparty_id is None:
            raise AppError(
                "Для залишку по дебіторській/кредиторській заборгованості "
                "треба вказати контрагента."
            )
    else:
        if needs_counterparty(op_type) and counterparty_id is None:
            raise AppError("Для цього типу операції треба обрати контрагента.")

    debit_account, credit_account = build_posting(
        op_type=op_type,
        opening_balance_account=opening_balance_account,
    )

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
