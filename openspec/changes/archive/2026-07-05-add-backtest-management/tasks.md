## 1. Backend — Database Model

- [x] 1.1 Create [backend/models/backtest.py](file:///d:/stock-driver/backend/models/backtest.py) with `BacktestPortfolio`, `BacktestTransaction`, `BacktestCash` models, register in [backend/models/__init__.py](file:///d:/stock-driver/backend/models/__init__.py)
- [x] 1.2 Add `create_backtest_tables` migration step in [backend/utils/migrate_db.py](file:///d:/stock-driver/backend/utils/migrate_db.py) and call it from `migrate()` function

## 2. Backend — Service Layer

- [x] 2.1 Create [backend/services/backtest_service.py](file:///d:/stock-driver/backend/services/backtest_service.py) with `get_portfolio_overview()`, `get_holdings()`, `add_holding()`, `update_holding()`, `delete_holding()`, `get_transactions()`, `add_transaction()`, `clear_all_transactions()`, `update_cash()`, `get_cash_balance()` functions

## 3. Backend — API Routes

- [x] 3.1 Add `GET /api/backtest/overview` route in [backend/api/routes.py](file:///d:/stock-driver/backend/api/routes.py)
- [x] 3.2 Add `GET /api/backtest/holdings` route
- [x] 3.3 Add `POST /api/backtest/holdings` route
- [x] 3.4 Add `PUT /api/backtest/holdings/<id>` route
- [x] 3.5 Add `DELETE /api/backtest/holdings/<id>` route
- [x] 3.6 Add `GET /api/backtest/transactions` route
- [x] 3.7 Add `POST /api/backtest/transactions` route
- [x] 3.8 Add `DELETE /api/backtest/transactions` route
- [x] 3.9 Add `POST /api/backtest/cash` route

## 4. Frontend — Backtest Page

- [x] 4.1 Create [frontend/src/views/Backtest.vue](file:///d:/stock-driver/frontend/src/views/Backtest.vue) as exact copy of Portfolio.vue with backtest API calls
- [x] 4.2 Add route `/backtest` and import in [frontend/src/router/index.js](file:///d:/stock-driver/frontend/src/router/index.js)
- [x] 4.3 Add "回测管理" navigation link in [frontend/src/App.vue](file:///d:/stock-driver/frontend/src/App.vue)
- [x] 4.4 Add backtest API methods in [frontend/src/api/stock.js](file:///d:/stock-driver/frontend/src/api/stock.js)

## 5. Database Migration

- [x] 5.1 Run `python manage.py db migrate` to create the three backtest tables
- [x] 5.2 Verify tables exist (backtest_portfolio, backtest_transactions, backtest_cash)