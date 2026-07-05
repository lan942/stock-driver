## Purpose
Provide RESTful APIs for portfolio management, including holdings CRUD, transaction recording, stock search, and cash balance management.

## Requirements

### Requirement: Get portfolio overview API
The system SHALL provide a GET API endpoint `/api/portfolio/overview` that returns the portfolio summary including total value, cash balance, total profit, and total profit rate.

#### Scenario: Retrieve portfolio overview
- **WHEN** client sends GET request to `/api/portfolio/overview`
- **THEN** system returns JSON with total_value, cash_balance, total_profit, total_profit_rate, and holdings count

### Requirement: Get portfolio holdings API
The system SHALL provide a GET API endpoint `/api/portfolio/holdings` that returns the list of all stock holdings with detailed information.

#### Scenario: Retrieve all holdings
- **WHEN** client sends GET request to `/api/portfolio/holdings`
- **THEN** system returns JSON array of holdings with code, name, quantity, available_quantity, cost_price, current_price, market_value, profit, and profit_rate

### Requirement: Add portfolio holding API
The system SHALL provide a POST API endpoint `/api/portfolio/holdings` to add a new stock holding.

#### Scenario: Add new holding
- **WHEN** client sends POST request to `/api/portfolio/holdings` with code, quantity (multiple of 100), cost_price
- **THEN** system validates quantity % 100 === 0, creates a new holding and returns the created record

#### Scenario: Add holding with invalid quantity
- **WHEN** client sends POST request with quantity that is not a multiple of 100
- **THEN** system rejects with error message "数量必须是100的整数倍"

### Requirement: Update portfolio holding API
The system SHALL provide a PUT API endpoint `/api/portfolio/holdings/<id>` to update an existing holding.

#### Scenario: Update holding
- **WHEN** client sends PUT request to `/api/portfolio/holdings/<id>` with updated quantity or cost_price
- **THEN** system updates the holding and returns the updated record

### Requirement: Delete portfolio holding API
The system SHALL provide a DELETE API endpoint `/api/portfolio/holdings/<id>` to remove a holding.

#### Scenario: Delete holding
- **WHEN** client sends DELETE request to `/api/portfolio/holdings/<id>`
- **THEN** system deletes the holding and returns success status

### Requirement: Stock search API
The system SHALL provide a GET API endpoint `/api/portfolio/search_stocks?q=<keyword>` to search stocks from the StockBasic table.

#### Scenario: Search stocks by keyword
- **WHEN** client sends GET request to `/api/portfolio/search_stocks?q=600519`
- **THEN** system queries StockBasic table matching code or name, returns unique results with code and name

#### Scenario: Search with empty query
- **WHEN** client sends GET request to `/api/portfolio/search_stocks?q=`
- **THEN** system returns an empty array

### Requirement: Get transactions API
The system SHALL provide a GET API endpoint `/api/portfolio/transactions` to retrieve transaction history, which SHALL include the `trade_date` field in the response.

#### Scenario: Retrieve transactions with trade_date
- **WHEN** client sends GET request to `/api/portfolio/transactions`
- **THEN** system returns JSON array of transactions with id, type, code, name, quantity, price, amount, trade_date, and created_at

### Requirement: Add transaction API
The system SHALL provide a POST API endpoint `/api/portfolio/transactions` to record a new transaction, supporting an optional `trade_date` parameter (format: YYYY-MM-DD).

#### Scenario: Add buy transaction with trade_date
- **WHEN** client sends POST request to `/api/portfolio/transactions` with type 'buy', code, quantity (multiple of 100), price, and trade_date
- **THEN** system validates quantity % 100 === 0, creates the transaction with the specified trade_date and returns the created record with trade_date

#### Scenario: Add sell transaction with trade_date
- **WHEN** client sends POST request to `/api/portfolio/transactions` with type 'sell', code, quantity (multiple of 100, ≤ holding quantity), price, and trade_date
- **THEN** system validates quantity % 100 === 0 and quantity ≤ holding quantity, creates the transaction with the specified trade_date and updates the holding

#### Scenario: Add transaction without trade_date (defaults to today)
- **WHEN** client sends POST request to `/api/portfolio/transactions` without trade_date
- **THEN** system defaults trade_date to the current date and creates the transaction

#### Scenario: Sell more than held
- **WHEN** client attempts to sell more shares than currently held
- **THEN** system rejects with error message

### Requirement: Database migration for trade_date column
The system SHALL provide a database migration to add the `trade_date` column (DATE type) to the existing `transactions` table.

#### Scenario: Add trade_date column
- **WHEN** the migration script runs
- **THEN** system executes `ALTER TABLE transactions ADD COLUMN trade_date DATE`

#### Scenario: Backfill existing rows
- **WHEN** the migration script runs after adding the column
- **THEN** system updates all rows where trade_date IS NULL to set trade_date to the date portion of created_at

### Requirement: Clear all transactions API
The system SHALL provide a DELETE API endpoint `/api/portfolio/transactions` to clear all transaction records.

#### Scenario: Clear all transactions
- **WHEN** client sends DELETE request to `/api/portfolio/transactions`
- **THEN** system deletes all transaction records and returns success status with deleted count

### Requirement: Update cash balance API
The system SHALL provide a POST API endpoint `/api/portfolio/cash` to update the cash balance.

#### Scenario: Deposit cash
- **WHEN** client sends POST request to `/api/portfolio/cash` with amount (positive)
- **THEN** system increases cash balance by the amount and returns the new balance

#### Scenario: Withdraw cash
- **WHEN** client sends POST request to `/api/portfolio/cash` with amount (negative)
- **THEN** system decreases cash balance by the amount and returns the new balance