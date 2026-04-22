import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app import database as db
from app.ui import components
from app.ui.pages import (
    dashboard,
    opening_balances,
    operations,
    partners_ledger,
    profit_loss,
    settings as settings_page,
)


st.set_page_config(
    page_title="Мінімальний бухгалтерський облік",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded",
)


# @st.cache_resource ensures init_db() runs only once per process.
@st.cache_resource
def _init_db_once():
    db.init_db()
    return True


_init_db_once()

_bg = db.get_setting("ui_background") or None
components.apply_background(_bg)

PAGES = {
    "🏁 Початкові залишки":  opening_balances.render,
    "📊 Панель":             dashboard.render,
    "📝 Операції":            operations.render,
    "📈 P&L":                 profit_loss.render,
    "👥 Книга партнерів":    partners_ledger.render,
    "⚙️ Налаштування":       settings_page.render,
}

# On first load, direct new users to Opening Balances; returning users see the Dashboard.
if "nav" not in st.session_state:
    if db.is_database_empty():
        st.session_state["nav"] = "🏁 Початкові залишки"
    else:
        st.session_state["nav"] = "📊 Панель"


st.markdown(
    "<style>[data-testid='stSidebarNav']{display:none}</style>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## 📒 Облік")
    st.caption("Мінімальний бухгалтерський додаток")

    choice = st.radio(
        "Розділ",
        options=list(PAGES.keys()),
        key="nav",
        label_visibility="collapsed",
    )

    st.divider()
    st.caption(
        "План рахунків:\n\n"
        "• 1000 Готівка\n"
        "• 1100 Дебіторка\n"
        "• 2000 Кредиторка\n"
        "• 3000 Капітал\n"
        "• 4000 Дохід\n"
        "• 5000 Витрати"
    )

PAGES[choice]()
