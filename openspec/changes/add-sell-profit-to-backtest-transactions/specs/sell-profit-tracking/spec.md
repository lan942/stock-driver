## ADDED Requirements

### Requirement: Sell transactions store profit percentage
The system SHALL record `profit_pct` (profit/loss percentage) for each backtest sell transaction.

#### Scenario: Sell transaction stores profit_pct during backtest
- **WHEN** the backtest engine executes a sell transaction
- **THEN** the system calculates `profit_pct = (sell_price - cost_price) / cost_price * 100` and stores it in the `BacktestTransaction` record
- AND `profit_pct` is rounded to 2 decimal places

#### Scenario: Buy transactions have null profit_pct
- **WHEN** a buy transaction is recorded
- **THEN** `profit_pct` SHALL be NULL (not applicable for buys)

### Requirement: Transaction API returns profit_pct
The system SHALL include `profit_pct` in the response of backtest transaction list endpoints.

#### Scenario: Get all transactions includes profit_pct
- **WHEN** client requests `GET /api/backtest/transactions`
- **THEN** each transaction object includes `profit_pct` field
- AND `profit_pct` is non-null for sell transactions
- AND `profit_pct` is null for buy transactions

#### Scenario: Get transactions by code includes profit_pct
- **WHEN** client requests `GET /api/stocks/{code}/transactions`
- **THEN** each backtest transaction in the response includes `profit_pct` field

### Requirement: Frontend displays sell profit in transaction table
The system SHALL display the `profit_pct` as a "收益率" column in the backtest transaction table.

#### Scenario: Display profit for sell transactions
- **WHEN** user views the backtest transaction table
- **THEN** the "收益率" column displays the profit_pct value with "%" suffix for sell rows
- AND positive profit SHALL be shown in green
- AND negative profit SHALL be shown in red

#### Scenario: Display placeholder for buy transactions
- **WHEN** a transaction row is a buy
- **THEN** the "收益率" column displays "-" (not applicable)
