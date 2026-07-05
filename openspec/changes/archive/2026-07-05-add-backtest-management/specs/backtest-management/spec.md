# backtest-management Specification

## Purpose
Provide backtest portfolio management capabilities, mirroring the real portfolio management system with independent tables for backtesting data.

## ADDED Requirements

### Requirement: Backtest data models
The system SHALL maintain three backtest models mirroring the real portfolio system:

**BacktestPortfolio** (`backtest_portfolio` table):

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key, auto-increment |
| code | String | Stock code (unique) |
| quantity | Integer | Holding quantity |
| cost_price | Float | Average cost price |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

**BacktestTransaction** (`backtest_transactions` table):

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key, auto-increment |
| type | String | Transaction type (buy/sell) |
| code | String | Stock code |
| quantity | Integer | Transaction quantity |
| price | Float | Transaction price |
| amount | Float | Total amount |
| trade_date | Date | Trading date |
| created_at | DateTime | Creation timestamp |

**BacktestCash** (`backtest_cash` table):

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key, auto-increment |
| balance | Float | Cash balance |
| updated_at | DateTime | Last update timestamp |

### Requirement: Backtest portfolio management API
The system SHALL provide the following API endpoints for backtest portfolio management:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/backtest/overview` | Get portfolio overview (total value, cash, market value, profit) |
| GET | `/api/backtest/holdings` | Get holding list with current prices |
| POST | `/api/backtest/holdings` | Add a new holding |
| PUT | `/api/backtest/holdings/<id>` | Update holding quantity/cost |
| DELETE | `/api/backtest/holdings/<id>` | Delete a holding |
| GET | `/api/backtest/transactions` | Get transaction list |
| POST | `/api/backtest/transactions` | Add a transaction |
| DELETE | `/api/backtest/transactions` | Clear all transactions |
| POST | `/api/backtest/cash` | Update cash balance |

#### Scenario: Add holding
- **WHEN** client sends POST to `/api/backtest/holdings` with code, quantity, cost_price
- **THEN** system creates holding and updates portfolio overview
- **AND** returns the created holding with current price info

#### Scenario: Add transaction (buy)
- **WHEN** client sends POST to `/api/backtest/transactions` with type=buy, code, quantity, price
- **THEN** system creates transaction and updates or creates the corresponding holding with weighted average cost

#### Scenario: Add transaction (sell)
- **WHEN** client sends POST to `/api/backtest/transactions` with type=sell, code, quantity, price
- **THEN** system creates transaction and reduces the holding quantity
- **AND** if quantity reaches 0, deletes the holding

#### Scenario: Update cash balance
- **WHEN** client sends POST to `/api/backtest/cash` with amount
- **THEN** system adds amount to existing cash balance (positive for deposit, negative for withdrawal)

### Requirement: Backtest management frontend page
The frontend SHALL provide a backtest management page at `/backtest` route that is an exact copy of the Portfolio management page.

#### Scenario: Page displays overview cards
- **WHEN** user navigates to `/backtest`
- **THEN** system shows 4 cards: total assets, cash balance, market value, total profit

#### Scenario: Page displays holding table
- **WHEN** user navigates to `/backtest`
- **THEN** system shows a table with columns: code, name, quantity, available_quantity, cost_price, current_price, market_value, profit, profit_rate, actions

#### Scenario: Page displays transaction table
- **WHEN** user navigates to `/backtest`
- **THEN** system shows a table with columns: type, code, name, quantity, price, amount, trade_date, created_at

#### Scenario: Navigation bar includes backtest link
- **WHEN** application loads
- **THEN** navigation bar shows "回测管理" link that routes to `/backtest`

### Requirement: Database migration for backtest tables
The system SHALL provide migration logic to create the three backtest tables.

#### Scenario: Migration creates tables
- **WHEN** migration script runs
- **THEN** system creates `backtest_portfolio`, `backtest_transactions`, and `backtest_cash` tables with all specified columns