"""
============================================================================
pages/profit_loss.py — СТОРІНКА "P&L" (ПРИБУТКИ ТА ЗБИТКИ)
============================================================================

ЩО ЦЕ ЗА ФАЙЛ:
    Спрощений звіт: доходи мінус витрати за обраний період.
    Відповідає Меті 2 з ТЗ.

ДЕ ПРАВИТИ ЩО:
    • Хочу ЗМІНИТИ ПЕРІОД ЗА ЗАМОВЧУВАННЯМ
      → змінна default_from (зараз — початок поточного року).

    • Хочу ДОДАТИ ГРУПУВАННЯ по місяцях
      → розширити таблицю rows нижче.
============================================================================
"""

from datetime import date

import pandas as pd
import streamlit as st

from app import database as db


def render():
    """Викликається з main.py коли обрано "📈 P&L"."""
    st.title("📈 Звіт про прибутки та збитки")
    st.caption("Доходи мінус витрати за період.")

    today = date.today()
    default_from = today.replace(month=1, day=1)  # з початку року

    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("З дати", value=default_from, key="pnl_from")
    with col2:
        date_to = st.date_input("По дату", value=today, key="pnl_to")

    pnl = db.profit_and_loss(date_from=date_from, date_to=date_to)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Доходи", f"{pnl['income']:,.2f}")
    with c2:
        st.metric("Витрати", f"{pnl['expense']:,.2f}")
    with c3:
        label = "Чистий прибуток" if pnl["net_profit"] >= 0 else "Чистий збиток"
        st.metric(label, f"{pnl['net_profit']:,.2f}")

    st.divider()

    # Детальна таблиця: доходи, їх сума, витрати, їх сума, підсумок.
    rows = []
    for acc in pnl["income_rows"]:
        rows.append({"Розділ": "Дохід", "Рахунок": f"{acc['code']} · {acc['name']}",
                     "Сума": acc["balance"]})
    rows.append({"Розділ": "", "Рахунок": "— Разом доходи —", "Сума": pnl["income"]})

    for acc in pnl["expense_rows"]:
        rows.append({"Розділ": "Витрати", "Рахунок": f"{acc['code']} · {acc['name']}",
                     "Сума": acc["balance"]})
    rows.append({"Розділ": "", "Рахунок": "— Разом витрати —", "Сума": pnl["expense"]})

    rows.append({"Розділ": "", "Рахунок": "ЧИСТИЙ РЕЗУЛЬТАТ", "Сума": pnl["net_profit"]})

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)