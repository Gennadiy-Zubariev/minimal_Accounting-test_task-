"""
============================================================================
pages/operations.py — СТОРІНКА "ОПЕРАЦІЇ"
============================================================================

ЩО ЦЕ ЗА ФАЙЛ:
    Дві вкладки:
      1. ➕ Нова операція — форма реєстрації (продаж, купівля, оплата, ...).
      2. 📋 Журнал — перегляд операцій за період.

    Контрагент обирається з загального списку (без розподілу на клієнтів/
    постачальників). Роль контрагента визначається типом операції.

ВАЖЛИВО про збереження:
    Записується тільки при кліку по кнопці "Записати операцію".
    Enter у полях не викликає сабміт.

ДЕ ПРАВИТИ ЩО:
    • Хочу ДОДАТИ новий тип операції
      → app/chart.py (OPERATION_TYPES + POSTING_RULES).

    • Хочу ЗМІНИТИ ПЕРІОД ЗА ЗАМОВЧУВАННЯМ у журналі
      → default_from у _operations_list() (зараз: останні 30 днів).

    • Хочу ДОДАТИ КОЛОНКУ у таблицю журналу
      → pd.DataFrame у _operations_list().
============================================================================
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app import database as db
from app import services
from app.chart import OPERATION_TYPES, POSTING_RULES
from app.ui.components import counterparty_picker


def render():
    """Викликається з main.py коли обрано '📝 Операції'."""
    st.title("📝 Операції")
    st.caption("Повсякденні події: продажі, купівлі, оплати.")

    tab_new, tab_list = st.tabs(["➕ Нова операція", "📋 Журнал"])
    with tab_new:
        _operation_form()
    with tab_list:
        _operations_list()


def _operation_form():
    """Форма реєстрації нової операції (без st.form — збереження по кнопці)."""
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

    # Якщо тип операції вимагає контрагента — показуємо пікер.
    # Без фільтра по типу: один контрагент може бути і клієнтом, і постачальником.
    counterparty_id = None
    if rule and rule["needs_counterparty"]:
        counterparty_id = counterparty_picker(
            key="new_op_cp", label="Контрагент",
        )

    col_date, col_amount = st.columns([1, 1])
    with col_date:
        op_date = st.date_input(
            "Дата",
            value=date.today(),
            max_value=date.today(),
            key="new_op_date",
        )
    with col_amount:
        amount = st.number_input(
            "Сума", min_value=0.0, step=100.0, format="%.2f",
            value=0.0,
            key="new_op_amount",
        )
    description = st.text_input(
        "Опис",
        placeholder="Напр. 'Продаж партії товару'",
        value="",
        key="new_op_desc",
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
            for k in ("new_op_amount", "new_op_desc"):
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
        except services.AppError as e:
            st.error(str(e))


def _operations_list():
    """Журнал операцій з фільтром по даті."""
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