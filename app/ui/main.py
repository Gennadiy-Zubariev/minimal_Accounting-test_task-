"""
============================================================================
main.py — ТОЧКА ВХОДУ ДОДАТКУ
============================================================================

ЩО ЦЕ ЗА ФАЙЛ:
    Streamlit запускає саме цей файл (див. CMD у Dockerfile).
    Він робить:
    1) Додає корінь проєкту в sys.path, щоб працювали імпорти `from app...`.
    2) Створює БД, якщо її ще нема.
    3) Застосовує CSS і фон.
    4) Показує меню зліва і викликає render() потрібної сторінки.
    5) СТАРТОВА СТОРІНКА: якщо БД порожня (жодної операції) —
       автоматично відкриває "Початкові залишки", щоб новий користувач
       не плутався з порожньою "Панеллю".

ДЕ ПРАВИТИ ЩО:
    • Хочу ДОДАТИ НОВУ СТОРІНКУ в меню
      → 1. Створити новий файл у app/ui/pages/ з функцією render().
      → 2. Імпортувати його тут і додати рядок у словник PAGES нижче.

    • Хочу ЗМІНИТИ СТАРТОВУ СТОРІНКУ за замовчуванням
      → блок "СТАРТОВА СТОРІНКА" нижче.

    • Хочу ЗМІНИТИ заголовок вкладки браузера або іконку
      → параметри page_title / page_icon у st.set_page_config().
============================================================================
"""

# --- Налаштування шляху --------------------------------------------------
# Цей файл живе в app/ui/main.py. Streamlit запускає його як скрипт,
# і Python за замовчуванням не бачить кореня проєкту як пакет.
# Додаємо корінь у sys.path, щоб працювали імпорти `from app...`.
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Імпорти (тільки після правки sys.path) ------------------------------
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


# --- 1. Налаштування сторінки (має бути першим викликом Streamlit!) ------
st.set_page_config(
    page_title="Мінімальний бухгалтерський облік",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- 2. Ініціалізація БД (один раз на процес) ----------------------------
# @st.cache_resource гарантує, що init_db() виконається лише раз,
# навіть якщо Streamlit перерендерить сторінку багато разів.
@st.cache_resource
def _init_db_once():
    db.init_db()
    return True


_init_db_once()


# --- 3. Застосовуємо фон (читаємо збережене налаштування) ---------------
_bg = db.get_setting("ui_background") or None
components.apply_background(_bg)


# --- 4. Меню і роутинг --------------------------------------------------
# Словник: назва в меню → функція, що рендерить сторінку.
# Додати нову сторінку — просто дописати сюди рядок.
PAGES = {
    "🏁 Початкові залишки":  opening_balances.render,
    "📊 Панель":             dashboard.render,
    "📝 Операції":            operations.render,
    "📈 P&L":                 profit_loss.render,
    "👥 Книга партнерів":    partners_ledger.render,
    "⚙️ Налаштування":       settings_page.render,
}


# ========== СТАРТОВА СТОРІНКА ==========
# Якщо БД порожня (новий користувач, ще нічого не вводив) — показуємо
# "Початкові залишки" за замовчуванням. Інакше — "Панель".
# Хочете змінити? — редагуйте цей блок.
#
# session_state потрібен, щоб "нав'язати" сторінку ТІЛЬКИ ОДИН РАЗ:
# якщо користувач вже сам вибрав щось у меню — не перемикати його назад.
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
        key="nav",  # зв'язаний з session_state['nav'] вище
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


# --- 5. Рендер обраної сторінки -----------------------------------------
# Просто викликаємо функцію зі словника.
PAGES[choice]()