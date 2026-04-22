from datetime import date

import streamlit as st

from app import database as db
from app import services
from app.ui.components import counterparty_picker


def render():
    """Render the Opening Balances page."""
    st.title("🏁 Початкові залишки")
    st.caption(
        "Введіть стан на момент старту ведення обліку. "
        "Кожен залишок зберігається як операція типу 'Початковий залишок' "
        "у кореспонденції з рахунком **3000 Капітал** — так дотримується подвійний запис."
    )

    if db.is_database_empty():
        st.info(
            "👋 Схоже, ви тут вперше. Почніть з введення початкових залишків: "
            "готівки, дебіторки (хто винен вам), кредиторки (кому винні ви). "
            "Після цього переходьте до щоденних операцій."
        )

    opening_date = st.date_input(
        "Дата, на яку вводимо залишки",
        value=date.today(),
        max_value=date.today(),
        key="opening_date",
        help="Не може бути в майбутньому.",
    )

    _render_summary()
    st.divider()

    tab_cash, tab_ar, tab_ap = st.tabs([
        "💵 Готівка",
        "📥 Дебіторська заборгованість",
        "📤 Кредиторська заборгованість",
    ])

    with tab_cash:
        _opening_cash(opening_date)
    with tab_ar:
        _opening_receivable(opening_date)
    with tab_ap:
        _opening_payable(opening_date)


def _render_summary():
    """Render top metrics showing already-entered balances."""
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("💵 Готівка", f"{db.get_balance('1000'):,.2f}")
    with c2:
        st.metric("📥 Дебіторка", f"{db.get_balance('1100'):,.2f}")
    with c3:
        st.metric("📤 Кредиторка", f"{db.get_balance('2000'):,.2f}")


def _opening_cash(opening_date):
    """Render the cash opening-balance form."""
    st.subheader("Залишок готівки на момент старту")

    amount = st.number_input(
        "Сума готівки",
        min_value=0.0, step=100.0, format="%.2f",
        value=0.0,
        key="opening_cash_amount",
    )
    description = st.text_input(
        "Опис (необов'язково)",
        placeholder="Напр. 'Каса на 01.01'",
        value="",
        key="opening_cash_desc",
    )

    if st.button("💾 Зберегти залишок готівки", key="opening_cash_submit"):
        try:
            services.register_operation(
                op_date=opening_date,
                op_type="opening_balance",
                amount=amount,
                description=description or "Початковий залишок готівки",
                counterparty_id=None,
                opening_balance_account="1000",
            )
            st.success(f"Залишок готівки {amount:,.2f} записано.")
            _clear_keys(["opening_cash_amount", "opening_cash_desc"])
            st.rerun()
        except services.AppError as e:
            st.error(str(e))


def _opening_receivable(opening_date):
    """Render the accounts-receivable opening-balance form."""
    st.subheader("Контрагент винен нам")
    st.caption("Один рядок = один контрагент. Для кількох — повторюйте збереження.")

    cp_id = counterparty_picker(
        key="opening_ar",
        label="Контрагент",
    )

    cp_key_suffix = cp_id if cp_id is not None else "none"

    amount = st.number_input(
        "Сума, яку контрагент нам винен",
        min_value=0.0, step=100.0, format="%.2f",
        value=0.0,
        key=f"opening_ar_amount_{cp_key_suffix}",
    )
    description = st.text_input(
        "Опис (необов'язково)",
        placeholder="Напр. 'Залишок по накладній № 12'",
        value="",
        key=f"opening_ar_desc_{cp_key_suffix}",
    )

    if st.button("💾 Зберегти залишок дебіторки", key="opening_ar_submit"):
        if cp_id is None:
            st.error("Спочатку оберіть контрагента (або додайте нового кнопкою ➕).")
        else:
            try:
                services.register_operation(
                    op_date=opening_date,
                    op_type="opening_balance",
                    amount=amount,
                    description=description or "Початковий залишок дебіторки",
                    counterparty_id=cp_id,
                    opening_balance_account="1100",
                )
                st.success(f"Залишок дебіторки збережено: {amount:,.2f}")
                _clear_keys([
                    f"opening_ar_amount_{cp_key_suffix}",
                    f"opening_ar_desc_{cp_key_suffix}",
                ])
                st.rerun()
            except services.AppError as e:
                st.error(str(e))


def _opening_payable(opening_date):
    """Render the accounts-payable opening-balance form."""
    st.subheader("Ми винні контрагенту")
    st.caption("Один рядок = один контрагент. Для кількох — повторюйте.")

    cp_id = counterparty_picker(
        key="opening_ap",
        label="Контрагент",
    )

    cp_key_suffix = cp_id if cp_id is not None else "none"

    amount = st.number_input(
        "Сума, яку ми винні контрагенту",
        min_value=0.0, step=100.0, format="%.2f",
        value=0.0,
        key=f"opening_ap_amount_{cp_key_suffix}",
    )
    description = st.text_input(
        "Опис (необов'язково)",
        placeholder="Напр. 'Залишок по акту № 7'",
        value="",
        key=f"opening_ap_desc_{cp_key_suffix}",
    )

    if st.button("💾 Зберегти залишок кредиторки", key="opening_ap_submit"):
        if cp_id is None:
            st.error("Спочатку оберіть контрагента (або додайте нового кнопкою ➕).")
        else:
            try:
                services.register_operation(
                    op_date=opening_date,
                    op_type="opening_balance",
                    amount=amount,
                    description=description or "Початковий залишок кредиторки",
                    counterparty_id=cp_id,
                    opening_balance_account="2000",
                )
                st.success(f"Залишок кредиторки збережено: {amount:,.2f}")
                _clear_keys([
                    f"opening_ap_amount_{cp_key_suffix}",
                    f"opening_ap_desc_{cp_key_suffix}",
                ])
                st.rerun()
            except services.AppError as e:
                st.error(str(e))


def _clear_keys(keys: list):
    """Remove keys from session_state so fields reset after rerun."""
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]
