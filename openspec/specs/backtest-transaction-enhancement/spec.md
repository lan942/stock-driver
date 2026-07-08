## Purpose
Enhance backtest transaction records with trading day prices and post-trade equity, and improve buy quantity calculation with A-share trading rules (100-share lots).

## Requirements

### Requirement: Backtest transaction records include trading day prices
The system SHALL record `open_price` and `close_price` for each backtest transaction to enable data verification.

#### Scenario: Record buy transaction with prices
- **WHEN** strategy backtest executes a buy transaction on T+1 trading day
- **THEN** system records `open_price` (used as buy price) and `close_price` (end-of-day price) for the trading day

#### Scenario: Record sell transaction with prices
- **WHEN** strategy backtest executes a sell transaction
- **THEN** system records `open_price` and `close_price` for the trading day

### Requirement: Backtest transaction records include post-trade equity
The system SHALL record `equity_after` (total equity after transaction) for each backtest transaction to enable profit tracking.

#### Scenario: Record equity after buy
- **WHEN** a buy transaction completes
- **THEN** system calculates equity_after = cash_balance + sum(holding_quantity * close_price) and stores it in the transaction record

#### Scenario: Record equity after sell
- **WHEN** a sell transaction completes
- **THEN** system calculates equity_after = cash_balance + sum(holding_quantity * close_price) and stores it in the transaction record

#### Scenario: Verify final equity consistency
- **WHEN** backtest completes
- **THEN** the last transaction's equity_after equals the final_equity reported in the backtest summary

### Requirement: Backtest transactions sorted by trade date ascending
The system SHALL return backtest transactions sorted by trade_date ascending, then by transaction ID ascending.

#### Scenario: Retrieve transactions in chronological order
- **WHEN** client requests `GET /api/backtest/transactions`
- **THEN** transactions are returned in chronological order (earliest first)

### Requirement: Dynamic buy quantity calculation
The system SHALL calculate buy quantity dynamically based on available capital and position ratio, ensuring quantity is a multiple of 100 (A-share minimum trading unit).

#### Scenario: Calculate buy quantity for available capital
- **WHEN** strategy backtest executes pending buys
- **THEN** system calculates quantity = floor(available_cash * position_ratio / buy_price) // 100 * 100
- AND quantity >= 100 (minimum lot)
- AND total_cost = quantity * buy_price <= available_cash

#### Scenario: Reduce quantity when total cost exceeds cash
- **WHEN** calculated quantity * buy_price > available_cash
- **THEN** system reduces quantity by 100 shares and re-checks

### Requirement: Lower historical data requirement for stock scoring
The system SHALL reduce the minimum historical data requirement for stock scoring from 60 trading days to 30 trading days.

#### Scenario: Score stocks with 30+ days of data
- **WHEN** strategy backtest generates recommendations
- **THEN** stocks with 30+ trading days of historical data are eligible for scoring

#### Scenario: Skip stocks with insufficient data
- **WHEN** stock has less than 30 trading days of data before the scoring date
- **THEN** stock is skipped from recommendation generation

### Requirement: Frontend displays extended transaction details
The system SHALL display `open_price`, `close_price`, and `equity_after` in the backtest management frontend transaction table.

#### Scenario: View transaction details with prices and equity
- **WHEN** user views backtest management page
- **THEN** transaction table shows columns for 开盘价、收盘价、交易后权益
