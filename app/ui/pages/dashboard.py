import pandas as pd
import streamlit as st

from app import database as db


def render():
    """Render the Dashboard page."""
    st.title("📊 Панель")
    st.caption("Поточний стан за всіма записаними операціями.")

    balances = {b["code"]: b for b in db.account_balances()}
    pnl = db.profit_and_loss()

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
