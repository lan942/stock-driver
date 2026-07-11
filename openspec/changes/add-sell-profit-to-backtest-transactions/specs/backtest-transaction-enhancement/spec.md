## ADDED Requirements

### Requirement: BacktestTransaction model includes profit_pct field
The `BacktestTransaction` model SHALL include a `profit_pct` column (Float, nullable) to store the profit/loss percentage for sell transactions.

#### Scenario: Model includes profit_pct column
- **WHEN** database schema is migrated
- **THEN** `backtest_transactions` table has a `profit_pct` column of type Float
- AND the column is nullable (NULL for buy transactions and existing records)

### Requirement: Backtest transaction service handles profit_pct
The `add_transaction()`, `get_transactions()`, and `get_transactions_by_code()` functions SHALL accept and return the `profit_pct` field.

#### Scenario: add_transaction accepts profit_pct
- **WHEN** `add_transaction()` is called with `profit_pct` parameter
- **THEN** the `profit_pct` value SHALL be stored in the transaction record

#### Scenario: add_transaction defaults profit_pct to None
- **WHEN** `add_transaction()` is called without `profit_pct` parameter (manual entry)
- **THEN** `profit_pct` SHALL be stored as NULL

#### Scenario: get_transactions returns profit_pct
- **WHEN** transaction records are queried
- **THEN** the returned data includes `profit_pct` for each record
- AND `profit_pct` is `None` for buy transactions and non-null for sell transactions from the backtest engine

### Requirement: Frontend transaction table includes profit column
The `Backtest.vue` transaction table SHALL include a "收益率" column that displays `profit_pct` for sell rows.

#### Scenario: Sell row shows profit percentage
- **WHEN** user views the transaction table and a sell row has `profit_pct`
- **THEN** the "收益率" column displays the value with "%" suffix
- AND positive values are colored green, negative values colored red

#### Scenario: Buy row shows dash
- **WHEN** user views the transaction table and a row is a buy
- **THEN** the "收益率" column displays "-"

#### Scenario: Legacy sell rows with null profit show dash
- **WHEN** user views a sell transaction that was created before this feature
- **THEN** the "收益率" column displays "-" (no historical data backfill)
