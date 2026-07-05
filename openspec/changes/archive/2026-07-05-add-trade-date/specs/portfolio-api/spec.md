## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Database migration for trade_date column
The system SHALL provide a database migration to add the `trade_date` column (DATE type) to the existing `transactions` table.

#### Scenario: Add trade_date column
- **WHEN** the migration script runs
- **THEN** system executes `ALTER TABLE transactions ADD COLUMN trade_date DATE`

#### Scenario: Backfill existing rows
- **WHEN** the migration script runs after adding the column
- **THEN** system updates all rows where trade_date IS NULL to set trade_date to the date portion of created_at