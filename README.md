#ENG________________________________________________________________
# Minimal Accounting

A web application for simple double-entry bookkeeping for small businesses, built on Streamlit + SQLite.

## Features

- **Double-entry bookkeeping** — every transaction automatically generates two journal entries (debit/credit)
- **Opening balances** — set starting balances for cash, accounts receivable, and accounts payable
- **Operations** — sales (cash/credit), purchases, payments to/from counterparties
- **Dashboard** — cash balance, receivables, payables, net profit
- **P&L Report** — income and expenses for any selected period
- **Partners Ledger** — settlements with each counterparty individually
- **Counterparty directory** — search and add with EDRPOU code validation

## Tech Stack

| Component | Technology |
|-----------|------------|
| UI | [Streamlit](https://streamlit.io/) ≥ 1.35 |
| Data | Python `sqlite3` (built-in) |
| Table processing | Pandas ≥ 2.0 |
| Containerization | Docker + Docker Compose |

## Quick Start

### Local (Python)

```bash
# 1. Clone the repository
git clone <repo-url>
cd test_task

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
streamlit run app/ui/main.py
```

The app will open at `http://localhost:8501`.

### Docker

```bash
docker-compose up --build
```

The database is stored in `./data/accounting.db` (mounted volume).

## Project Structure

```
test_task/
├── app/
│   ├── chart.py          # Chart of accounts and operation types
│   ├── database.py       # SQLite: initialization, CRUD, reports
│   ├── services.py       # Business logic and validation
│   └── ui/
│       ├── main.py       # Streamlit entry point
│       ├── components.py # Reusable UI components
│       └── pages/        # Application pages
├── data/                 # Database (excluded from git)
├── static/backgrounds/   # Background images
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Chart of Accounts

| Account | Name | Type |
|---------|------|------|
| 1000 | Cash | Asset |
| 1100 | Accounts Receivable | Asset |
| 2000 | Accounts Payable | Liability |
| 3000 | Equity / Retained Earnings | Equity |
| 4000 | Income | Income |
| 5000 | Expenses | Expense |

## Operation Types

| Type | Debit | Credit | Description |
|------|-------|--------|-------------|
| Sale (cash) | 1000 | 4000 | Cash sale |
| Sale (credit) | 1100 | 4000 | Sale with deferred payment |
| Payment from customer | 1000 | 1100 | Receivable settlement |
| Purchase (cash) | 5000 | 1000 | Cash purchase |
| Purchase (credit) | 5000 | 2000 | Purchase with deferred payment |
| Payment to supplier | 2000 | 1000 | Payable settlement |

## Requirements

- Python 3.11+
- or Docker

## License

MIT

_____________________________________________________________________
#UKR
# Мінімальний бухгалтерський облік

Веб-застосунок для простого подвійного бухгалтерського обліку малого бізнесу, побудований на Streamlit + SQLite.

## Можливості

- **Подвійний запис** — кожна операція автоматично формує два записи (дебет/кредит)
- **Початкові залишки** — введення стартових залишків каси, дебіторської та кредиторської заборгованості
- **Операції** — продажі (готівкові/кредитні), закупівлі, платежі від/до контрагентів
- **Панель показників** — залишок каси, дебіторка, кредиторка, чистий прибуток
- **Звіт P&L** — доходи та витрати за довільний період
- **Книга партнерів** — взаєморозрахунки з кожним контрагентом окремо
- **Довідник контрагентів** — пошук та додавання з валідацією коду ЄДРПОУ

## Стек технологій

| Компонент | Технологія |
|-----------|------------|
| UI | [Streamlit](https://streamlit.io/) ≥ 1.35 |
| Дані | Python `sqlite3` (вбудований) |
| Обробка таблиць | Pandas ≥ 2.0 |
| Контейнеризація | Docker + Docker Compose |

## Швидкий старт

### Локально (Python)

```bash
# 1. Клонувати репозиторій
git clone <repo-url>
cd test_task

# 2. Встановити залежності
pip install -r requirements.txt

# 3. Запустити
streamlit run app/ui/main.py
```

Застосунок відкриється за адресою `http://localhost:8501`.

### Docker

```bash
docker-compose up --build
```

База даних зберігається у `./data/accounting.db` (змонтований volume).

## Структура проєкту

```
test_task/
├── app/
│   ├── chart.py          # План рахунків і типи операцій
│   ├── database.py       # SQLite: ініціалізація, CRUD, звіти
│   ├── services.py       # Бізнес-логіка та валідація
│   └── ui/
│       ├── main.py       # Точка входу Streamlit
│       ├── components.py # Перевикористовувані компоненти
│       └── pages/        # Сторінки застосунку
├── data/                 # База даних (виключена з git)
├── static/backgrounds/   # Фонові зображення
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## План рахунків

| Рахунок | Назва | Тип |
|---------|-------|-----|
| 1000 | Готівка | Актив |
| 1100 | Дебіторська заборгованість | Актив |
| 2000 | Кредиторська заборгованість | Пасив |
| 3000 | Капітал / Нерозподілений прибуток | Капітал |
| 4000 | Дохід | Дохід |
| 5000 | Витрати | Витрати |

## Типи операцій

| Тип | Дебет | Кредит | Опис |
|-----|-------|--------|------|
| Продаж (готівка) | 1000 | 4000 | Готівковий продаж |
| Продаж (кредит) | 1100 | 4000 | Продаж з відстрочкою |
| Оплата від покупця | 1000 | 1100 | Погашення дебіторки |
| Закупівля (готівка) | 5000 | 1000 | Готівкова закупівля |
| Закупівля (кредит) | 5000 | 2000 | Закупівля з відстрочкою |
| Оплата постачальнику | 2000 | 1000 | Погашення кредиторки |

## Вимоги

- Python 3.11+
- або Docker

## Ліцензія

MIT

