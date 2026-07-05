## 1. Backend — Data Model & Migration

- [x] 1.1 Add `trade_date` column (Date type) to the Transaction model in [portfolio.py](file:///d:/stock-driver/backend/models/portfolio.py)
- [x] 1.2 Update database migration script [migrate_db.py](file:///d:/stock-driver/backend/utils/migrate_db.py) to add `trade_date` column and backfill existing rows

## 2. Backend — Service Layer

- [x] 2.1 Update `add_transaction()` in [portfolio_service.py](file:///d:/stock-driver/backend/services/portfolio_service.py) to accept optional `trade_date` parameter (default to today)
- [x] 2.2 Update `get_transactions()` to include `trade_date` in response (formatted as YYYY-MM-DD)

## 3. Backend — API Layer

- [x] 3.1 Update `POST /api/portfolio/transactions` route in [routes.py](file:///d:/stock-driver/backend/api/routes.py) to accept optional `trade_date` parameter and pass it to service

## 4. Frontend — Add Transaction Dialog

- [x] 4.1 Add `trade_date` field to `addTransactionForm` in [Portfolio.vue](file:///d:/stock-driver/frontend/src/views/Portfolio.vue), defaulting to today's date
- [x] 4.2 Add `<el-date-picker>` component to the add transaction dialog template
- [x] 4.3 Update `submitAddTransaction()` to include `trade_date` in the API request
- [x] 4.4 Reset `trade_date` to today when opening the dialog (`openAddTransactionDialog`)

## 5. Frontend — Transaction Table

- [x] 5.1 Add "交易日期" column to the transactions table showing `trade_date`
- [x] 5.2 Ensure proper formatting of `trade_date` in the table display