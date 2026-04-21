"""
============================================================================
components.py — UI-КОМПОНЕНТИ БАГАТОРАЗОВОГО ВИКОРИСТАННЯ
============================================================================

ЩО ЦЕ ЗА ФАЙЛ:
    Тут дві речі:
    1) counterparty_picker() — пошук контрагента + кнопка Додати.
    2) apply_background() — CSS для фону + список доступних картинок.

ЯК ПРАЦЮЄ ПІКЕР:
    • Зліва — searchable selectbox. Клікаєш, друкуєш назву/ЄДРПОУ,
      вибираєш потрібного контрагента.
    • Справа — кнопка "➕ Додати". При натисканні — під пікером
      з'являється форма додавання нового.
    • Контрагенти показуються УСІ (без розділу на клієнтів/постачальників),
      бо один контрагент може бути і тим, і іншим — роль визначається
      типом операції, в якій він бере участь.

ДЕ ПРАВИТИ ЩО:
    • Хочу ЗМІНИТИ НАПИС на кнопці додавання
      → рядок st.button(...) у counterparty_picker().

    • Хочу ЗМІНИТИ співвідношення ширини поля і кнопки
      → параметр columns у st.columns([5, 1]) (зараз 5:1).

    • Хочу ЗМІНИТИ ЗАГАЛЬНУ КОЛЬОРОВУ СХЕМУ ДОДАТКУ
      → змінна BASE_CSS нижче.

    • Хочу додати СВІЙ ФОН
      → просто скопіюйте картинку .png/.jpg у папку static/backgrounds/.
============================================================================
"""

import base64
from pathlib import Path

import streamlit as st

from app import database as db
from app import services


BACKGROUNDS_DIR = Path(__file__).resolve().parents[2] / "static" / "backgrounds"
SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".webp"}


# ===========================================================================
# 1. ПІКЕР КОНТРАГЕНТА
# ===========================================================================
def counterparty_picker(
    key: str,
    label: str = "Контрагент",
) -> int | None:
    """
    Показує searchable selectbox + кнопку "Додати". Повертає id обраного
    контрагента або None.

    ВАЖЛИВО: не можна розміщувати всередині st.form() — пікер сам містить
    st.form для додавання нового (вкладені форми Streamlit забороняє).
    """
    # Стан "форма додавання відкрита чи ні" — у session_state.
    open_key = f"{key}_add_open"
    if open_key not in st.session_state:
        st.session_state[open_key] = False

    # Список усіх контрагентів.
    candidates = db.list_counterparties()
    options: list = [None] + [c["id"] for c in candidates]

    def _format(opt):
        if opt is None:
            return "— не обрано —"
        for c in candidates:
            if c["id"] == opt:
                return f"🧾 {c['name']}  •  ЄДРПОУ {c['edrpou']}"
        return f"#{opt}"

    # Ряд: [пошук/вибір]   [кнопка]
    col_pick, col_btn = st.columns([5, 1], vertical_alignment="bottom")

    with col_pick:
        selected = st.selectbox(
            label,
            options=options,
            format_func=_format,
            key=f"{key}_select",
            help="Клікніть і почніть вводити назву або ЄДРПОУ для пошуку.",
        )

    with col_btn:
        btn_label = "✖ Сховати" if st.session_state[open_key] else "➕ Додати"
        if st.button(btn_label, key=f"{key}_toggle_add", use_container_width=True):
            st.session_state[open_key] = not st.session_state[open_key]
            st.rerun()

    # Форма додавання — тільки якщо відкрита.
    if st.session_state[open_key]:
        _render_new_counterparty_form(
            key_prefix=f"{key}_new",
            open_state_key=open_key,
        )

    return selected


def _render_new_counterparty_form(key_prefix, open_state_key):
    """Форма 'Додати контрагента'. Після успіху закриває себе і робить rerun."""

    with st.container(border=True):
        st.markdown("**➕ Новий контрагент**")

        with st.form(key=f"{key_prefix}_form", clear_on_submit=True):
            col_name, col_edrpou = st.columns([2, 1])

            with col_name:
                new_name = st.text_input(
                    "Назва *",
                    placeholder='Напр. ТОВ "Ромашка"',
                    key=f"{key_prefix}_name",
                )
            with col_edrpou:
                new_edrpou = st.text_input(
                    "ЄДРПОУ *",
                    placeholder="12345678",
                    help="8 цифр для юросіб, 10 — для ФОП",
                    max_chars=10,
                    key=f"{key_prefix}_edrpou",
                )

            submitted = st.form_submit_button("💾 Зберегти контрагента")

            if submitted:
                try:
                    services.create_counterparty(
                        name=new_name, edrpou=new_edrpou
                    )
                    st.success(
                        f"Додано: {new_name} (ЄДРПОУ {new_edrpou}). "
                        "Оберіть його у списку вище."
                    )
                    st.session_state[open_state_key] = False
                    st.rerun()
                except services.AppError as e:
                    st.error(str(e))


# ===========================================================================
# 2. ФОН І СТИЛІ
# ===========================================================================

BASE_CSS = """
.stApp { background-color: #f5f7fa; }
h1, h2, h3 { color: #1f2937; }
.block-container {
    background-color: rgba(255, 255, 255, 0.88);
    padding: 2rem 2.5rem;
    border-radius: 12px;
}
div[data-testid="stMetric"] {
    background-color: rgba(255, 255, 255, 0.95);
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
}
"""


def list_backgrounds() -> list:
    """Список імен файлів у папці static/backgrounds/."""
    if not BACKGROUNDS_DIR.exists():
        return []
    return sorted(
        f.name for f in BACKGROUNDS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXT
    )


def apply_background(background_filename: str | None) -> None:
    """Базовий CSS + (опційно) фонова картинка."""
    css = BASE_CSS

    if background_filename:
        bg_path = BACKGROUNDS_DIR / background_filename
        if bg_path.exists():
            data = base64.b64encode(bg_path.read_bytes()).decode("utf-8")
            ext = bg_path.suffix.lower().lstrip(".")
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
            css += f"""
            .stApp {{
                background-image: url("data:{mime};base64,{data}");
                background-size: cover;
                background-attachment: fixed;
                background-position: center;
            }}
            """

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)