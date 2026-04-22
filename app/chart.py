ACCOUNTS = {
    "1000": {"name": "Готівка",                           "type": "asset"},
    "1100": {"name": "Дебіторська заборгованість",        "type": "asset"},
    "2000": {"name": "Кредиторська заборгованість",       "type": "liability"},
    "3000": {"name": "Капітал / Нерозподілений прибуток", "type": "equity"},
    "4000": {"name": "Дохід",                             "type": "income"},
    "5000": {"name": "Витрати",                           "type": "expense"},
}

OPERATION_TYPES = {
    "sale_cash":          "Продаж за готівку",
    "sale_credit":        "Продаж у кредит (клієнт винен)",
    "customer_payment":   "Оплата від клієнта",
    "purchase_cash":      "Купівля за готівку",
    "purchase_credit":    "Купівля у кредит (ми винні)",
    "supplier_payment":   "Оплата постачальнику",
    "opening_balance":    "Початковий залишок",
}

POSTING_RULES = {
    "sale_cash":        {"dr": "1000", "cr": "4000", "needs_counterparty": False},
    "sale_credit":      {"dr": "1100", "cr": "4000", "needs_counterparty": True},
    "customer_payment": {"dr": "1000", "cr": "1100", "needs_counterparty": True},
    "purchase_cash":    {"dr": "5000", "cr": "1000", "needs_counterparty": False},
    "purchase_credit":  {"dr": "5000", "cr": "2000", "needs_counterparty": True},
    "supplier_payment": {"dr": "2000", "cr": "1000", "needs_counterparty": True},
    "opening_balance":  None,
}


def build_posting(op_type: str, opening_balance_account: str = None):
    """Return (debit_account, credit_account) for the given operation type."""
    if op_type == "opening_balance":
        if opening_balance_account is None:
            raise ValueError("Для opening_balance треба вказати opening_balance_account")
        acc_type = ACCOUNTS[opening_balance_account]["type"]
        # Assets go to debit; liabilities/equity go to credit. The other leg is always 3000.
        if acc_type in ("asset", "expense"):
            return (opening_balance_account, "3000")
        else:
            return ("3000", opening_balance_account)

    rule = POSTING_RULES.get(op_type)
    if rule is None:
        raise ValueError(f"Невідомий тип операції: {op_type}")
    return (rule["dr"], rule["cr"])


def needs_counterparty(op_type: str) -> bool:
    """Return True if this operation type requires a counterparty."""
    rule = POSTING_RULES.get(op_type)
    if rule is None:
        return False
    return rule["needs_counterparty"]
