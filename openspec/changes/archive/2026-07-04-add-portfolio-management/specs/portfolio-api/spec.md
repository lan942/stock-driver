## ADDED Requirements

### Requirement: Get portfolio overview API
The system SHALL provide a GET API endpoint `/api/portfolio/overview` that returns the portfolio summary including total value, cash balance, total profit, and total profit rate.

#### Scenario: Retrieve portfolio overview
- **WHEN** client sends GET request to `/api/portfolio/overview`
- **THEN** system returns JSON with total_value, cash_balance, total_profit, total_profit_rate, and holdings count

### Requirement: Get portfolio holdings API
The system SHALL provide a GET API endpoint `/api/portfolio/holdings` that returns the list of all stock holdings with detailed information.

#### Scenario: Retrieve all holdings
- **WHEN** client sends GET request to `/api/portfolio/holdings`
- **THEN** system returns JSON array of holdings with code, name, quantity, cost_price, current_price, market_value, profit, and profit_rate

### Requirement: Add portfolio holding API
The system SHALL provide a POST API endpoint `/api/portfolio/holdings` to add a new stock holding.

#### Scenario: Add new holding
- **WHEN** client sends POST request to `/api/portfolio/holdings` with code, quantity, cost_price
- **THEN** system creates a new holding and returns the created record

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

### Requirement: Get transactions API
The system SHALL provide a GET API endpoint `/api/portfolio/transactions` to retrieve transaction history.

#### Scenario: Retrieve transactions
- **WHEN** client sends GET request to `/api/portfolio/transactions`
- **THEN** system returns JSON array of transactions with id, type, code, name, quantity, price, amount, and timestamp

### Requirement: Add transaction API
The system SHALL provide a POST API endpoint `/api/portfolio/transactions` to record a new transaction.

#### Scenario: Add buy transaction
- **WHEN** client sends POST request to `/api/portfolio/transactions` with type 'buy', code, quantity, price
- **THEN** system creates the transaction and returns the created record

#### Scenario: Add sell transaction
- **WHEN** client sends POST request to `/api/portfolio/transactions` with type 'sell', code, quantity, price
- **THEN** system creates the transaction and returns the created record

### Requirement: Update cash balance API
The system SHALL provide a POST API endpoint `/api/portfolio/cash` to update the cash balance.

#### Scenario: Deposit cash
- **WHEN** client sends POST request to `/api/portfolio/cash` with amount (positive)
- **THEN** system increases cash balance by the amount and returns the new balance

#### Scenario: Withdraw cash
- **WHEN** client sends POST request to `/api/portfolio/cash` with amount (negative)
- **THEN** system decreases cash balance by the amount and returns the new balance