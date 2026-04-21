"""
============================================================================
pages/settings.py — СТОРІНКА "НАЛАШТУВАННЯ"
============================================================================

ЩО ЦЕ ЗА ФАЙЛ:
    Поки що єдина опція — вибір фону інтерфейсу.
    Картинки підкладаються у папку static/backgrounds/ (volume у Docker).

ДЕ ПРАВИТИ ЩО:
    • Хочу ДОДАТИ нове налаштування (напр. "валюта")
      → додайте новий st.selectbox/st.text_input.
      → використовуйте db.get_setting / db.set_setting (key-value в БД).
============================================================================
"""

import streamlit as st

from app import database as db
from app.ui.components import BACKGROUNDS_DIR, list_backgrounds


def render():
    """Викликається з main.py коли обрано "⚙️ Налаштування"."""
    st.title("⚙️ Налаштування")

    st.subheader("Фон інтерфейсу")
    st.write(
        f"Додайте картинки у папку `{BACKGROUNDS_DIR}` (підтримуються "
        "`.png`, `.jpg`, `.jpeg`, `.webp`) — і вони з'являться у списку."
    )

    available = list_backgrounds()
    current = db.get_setting("ui_background") or None
    options = [None] + available

    # Безпечний вибір індексу (якщо файл раптом прибрали).
    try:
        current_index = options.index(current)
    except ValueError:
        current_index = 0

    chosen = st.selectbox(
        "Оберіть фон",
        options=options,
        index=current_index,
        format_func=lambda x: "— без фону —" if x is None else x,
        key="bg_select",
    )

    if st.button("Зберегти", key="bg_save"):
        # None кодуємо як "" — так простіше зберігати в текстовій колонці.
        db.set_setting("ui_background", chosen or "")
        st.success("Збережено. Фон застосується на наступному рендері.")
        st.rerun()

    if not available:
        st.info(
            "Папка поки порожня. Покладіть туди будь-які картинки — "
            "вони автоматично з'являться у списку."
        )