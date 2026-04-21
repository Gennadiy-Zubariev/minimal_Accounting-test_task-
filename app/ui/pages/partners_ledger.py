"""
============================================================================
pages/partners_ledger.py — СТОРІНКА "КНИГА ПАРТНЕРІВ"
============================================================================

ЩО ЦЕ ЗА ФАЙЛ:
    Дві частини:
    1) Загальна таблиця ВСІХ контрагентів, з двома колонками сальдо:
       "Винні нам" (по 1100) і "Ми винні" (по 2000).
       Один контрагент може мати ненульові значення в обох колонках,
       якщо він одночасно наш клієнт і наш постачальник.
    2) Деталізована книга обраного партнера: хронологія рухів і по 1100,
       і по 2000 разом, з двома running-сальдо.

ДЕ ПРАВИТИ ЩО:
    • Хочу ЗМІНИТИ ЛОГІКУ running balance
      → функція partner_ledger() у app/database.py.

    • Хочу ПРИХОВАТИ ряди з нульовим сальдо (наприклад, тільки "активних")
      → фільтрувати summary перед побудовою DataFrame нижче.
============================================================================
"""

import pandas as pd
import streamlit as st

from app import database as db
from app.chart import OPERATION_TYPES


def render():
    """Викликається з main.py коли обрано '👥 Книга партнерів'."""
    st.title("👥 Книга партнерів")
    st.caption(
        "Загальний список контрагентів з дебіторкою і кредиторкою. "
        "Один контрагент може одночасно бути нам винен і ми йому — "
        "вони показуються окремими колонками."
    )

    summary = db.partners_summary()

    if not summary:
        st.info(
            "Ще немає контрагентів. Додайте першого на сторінці "
            "«Операції» або «Початкові залишки»."
        )
        return

    # --- 1. Загальна таблиця з підсумками ---
    df = pd.DataFrame([
        {
            "ID": s["id"],
            "Назва": s["name"],
            "ЄДРПОУ": s["edrpou"],
            "Винні нам (1100)": s["receivable_balance"],
            "Ми винні (2000)": s["payable_balance"],
        }
        for s in summary
    ])
    st.subheader("Підсумкове сальдо по всіх контрагентах")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- 2. Загальні підсумки знизу таблиці ---
    total_receivable = sum(s["receivable_balance"] for s in summary)
    total_payable = sum(s["payable_balance"] for s in summary)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Всього дебіторка", f"{total_receivable:,.2f}")
    with c2:
        st.metric("Всього кредиторка", f"{total_payable:,.2f}")

    st.divider()

    # --- 3. Деталізована книга обраного партнера ---
    st.subheader("Деталізована книга партнера")

    options = [s["id"] for s in summary]
    labels = {s["id"]: f"{s['name']}  (ЄДРПОУ {s['edrpou']})" for s in summary}

    selected_id = st.selectbox(
        "Партнер",
        options=options,
        format_func=lambda x: labels.get(x, str(x)),
        key="pl_select",
    )

    if selected_id is None:
        return

    ledger = db.partner_ledger(selected_id)
    if ledger is None or not ledger["rows"]:
        st.info("За цим партнером ще немає рухів.")
        return

    # Таблиця хронології — з розділенням по ролях.
    df_rows = pd.DataFrame([
        {
            "Дата": r["date"],
            "Тип операції": OPERATION_TYPES.get(r["op_type"], r["op_type"]),
            "Роль": "Клієнт (1100)" if r["role"] == "receivable" else "Постачальник (2000)",
            "Опис": r["description"],
            "Дебет": r["debit"],
            "Кредит": r["credit"],
            "Сальдо дебіторки": r["running_receivable"],
            "Сальдо кредиторки": r["running_payable"],
        }
        for r in ledger["rows"]
    ])
    st.dataframe(df_rows, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            "Партнер винен нам (дебіторка)",
            f"{ledger['receivable_balance']:,.2f}",
        )
    with c2:
        st.metric(
            "Ми винні партнеру (кредиторка)",
            f"{ledger['payable_balance']:,.2f}",
        )