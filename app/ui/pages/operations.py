from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app import database as db
from app import services
from app.chart import OPERATION_TYPES, POSTING_RULES
from app.ui.components import counterparty_picker


def render():
    """Render the Operations page."""
    st.title("📝 Операції")
    st.caption("Повсякденні події: продажі, купівлі, оплати.")

    tab_new, tab_list = st.tabs(["➕ Нова операція", "📋 Журнал"])
    with tab_new:
        _operation_form()
    with tab_list:
        _operations_list()


def _operation_form():
    """Render the new-operation form (button-based submit, no st.form wrapper)."""
    selectable_types = {
        code: label for code, label in OPERATION_TYPES.items()
        if code != "opening_balance"
    }

    op_type_code = st.selectbox(
        "Тип операції",
        options=list(selectable_types.keys()),
        format_func=lambda c: selectable_types[c],
        key="new_op_type",
    )

    rule = POSTING_RULES.get(op_type_code)
    if rule:
        st.info(f"Проводка: **Дт {rule['dr']}  •  Кт {rule['cr']}**")

    counterparty_id = None
    if rule and rule["needs_counterparty"]:
        counterparty_id = counterparty_picker(
            key="new_op_cp", label="Контрагент",
        )

    cp_suffix = counterparty_id if counterparty_id is not None else "none"
    form_key_suffix = f"{op_type_code}_{cp_suffix}"

    col_date, col_amount = st.columns([1, 1])
    with col_date:
        op_date = st.date_input(
            "Дата",
            value=date.today(),
            max_value=date.today(),
            key=f"new_op_date",
        )
    with col_amount:
        amount = st.number_input(
            "Сума", min_value=0.0, step=100.0, format="%.2f",
            value=0.0,
            key=f"new_op_amount_{form_key_suffix}",
        )
    description = st.text_input(
        "Опис",
        placeholder="Напр. 'Продаж партії товару'",
        value="",
        key=f"new_op_desc_{form_key_suffix}",
    )

    if st.button("💾 Записати операцію", key="new_op_submit"):
        try:
            op_id = services.register_operation(
                op_date=op_date,
                op_type=op_type_code,
                amount=amount,
                description=description,
                counterparty_id=counterparty_id,
            )
            st.success(
                f"Операцію #{op_id} ({OPERATION_TYPES[op_type_code]}) "
                f"на суму {amount:,.2f} збережено."
            )
            for k in (
                f"new_op_amount_{form_key_suffix}",
                f"new_op_desc_{form_key_suffix}",
            ):
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
        except services.AppError as e:
            st.error(str(e))


def _operations_list():
    """Render the operations journal with a date-range filter."""
    default_from = date.today() - timedelta(days=30)

    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("З дати", value=default_from, key="ops_from")
    with col2:
        date_to = st.date_input("По дату", value=date.today(), key="ops_to")

    ops = db.list_operations(date_from=date_from, date_to=date_to)
    if not ops:
        st.info("За обраний період операцій немає.")
        return

    df = pd.DataFrame([
        {
            "ID": o["id"],
            "Дата": o["op_date"],
            "Тип": OPERATION_TYPES.get(o["op_type"], o["op_type"]),
            "Сума": o["amount"],
            "Контрагент": o.get("counterparty_name") or "—",
            "ЄДРПОУ": o.get("counterparty_edrpou") or "—",
            "Опис": o["description"],
        }
        for o in ops
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"Всього записів: {len(df)}")
