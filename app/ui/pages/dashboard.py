"""
============================================================================
pages/dashboard.py — СТОРІНКА "ПАНЕЛЬ"
============================================================================

ЩО ЦЕ ЗА ФАЙЛ:
    Головна сторінка-огляд. Показує:
    - ключові залишки (готівка, дебіторка, кредиторка);
    - чистий результат (доходи − витрати);
    - повну таблицю залишків за планом рахунків.

ДЕ ПРАВИТИ ЩО:
    • Хочу ЗМІНИТИ, які метрики показуються зверху
      → у функції render() блок з st.metric.

    • Хочу ДОДАТИ ГРАФІК (напр. динаміка продажів)
      → у кінці функції render() додайте st.line_chart / st.bar_chart.
============================================================================
"""

import pandas as pd
import streamlit as st

from app import database as db


def render():
    """Викликається з main.py коли обрано "📊 Панель"."""
    st.title("📊 Панель")
    st.caption("Поточний стан за всіма записаними операціями.")

    # Беремо всі залишки з database.py.
    balances = {b["code"]: b for b in db.account_balances()}
    pnl = db.profit_and_loss()

    # Чотири великі метрики у ряд.
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("💵 Готівка (1000)", f"{balances['1000']['balance']:,.2f}")
    with c2:
        st.metric("📥 Дебіторка (1100)", f"{balances['1100']['balance']:,.2f}",
                  help="Скільки клієнти винні нам")
    with c3:
        st.metric("📤 Кредиторка (2000)", f"{balances['2000']['balance']:,.2f}",
                  help="Скільки ми винні постачальникам")
    with c4:
        st.metric("💰 Чистий результат", f"{pnl['net_profit']:,.2f}",
                  delta=f"Д: {pnl['income']:,.2f} / В: {pnl['expense']:,.2f}")

    st.divider()

    # Повна таблиця залишків по всіх рахунках.
    st.subheader("Залишки за планом рахунків")
    df = pd.DataFrame([
        {
            "Код": b["code"],
            "Назва": b["name"],
            "Обороти Дт": b["debit_total"],
            "Обороти Кт": b["credit_total"],
            "Сальдо": b["balance"],
        }
        for b in db.account_balances()
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)