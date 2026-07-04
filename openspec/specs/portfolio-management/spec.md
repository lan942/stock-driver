## Purpose
Manage portfolio data including stock holdings, transactions, and cash balance with real-time profit calculation.

## Requirements

### Requirement: Portfolio model tracks stock holdings
The system SHALL maintain a Portfolio model that tracks user's stock holdings, including stock code, quantity, and average cost price.

#### Scenario: Create new portfolio entry
- **WHEN** user adds a new stock holding with code, quantity, and cost price
- **THEN** system creates a new Portfolio record with the provided information

#### Scenario: Update portfolio entry
- **WHEN** user modifies an existing portfolio entry's quantity or cost price
- **THEN** system updates the Portfolio record with the new values

#### Scenario: Delete portfolio entry
- **WHEN** user removes a portfolio entry
- **THEN** system deletes the corresponding Portfolio record

### Requirement: Transaction model tracks buy/sell operations
The system SHALL maintain a Transaction model that records all stock buy and sell operations, including transaction type, stock code, quantity, price, and timestamp.

#### Scenario: Record buy transaction
- **WHEN** user buys stock and records the transaction
- **THEN** system creates a Transaction record with type 'buy', stock code, quantity, price, and current timestamp

#### Scenario: Record sell transaction
- **WHEN** user sells stock and records the transaction
- **THEN** system creates a Transaction record with type 'sell', stock code, quantity, price, and current timestamp

### Requirement: Cash balance management
The system SHALL track the user's cash balance, allowing updates when money is deposited or withdrawn.

#### Scenario: Update cash balance
- **WHEN** user deposits or withdraws cash
- **THEN** system updates the cash balance accordingly

### Requirement: Real-time profit calculation
The system SHALL calculate the current profit and profit rate for each portfolio entry based on the latest market price.

#### Scenario: Calculate profit for a stock holding
- **WHEN** system retrieves portfolio data
- **THEN** system calculates profit = (current_price - cost_price) * quantity and profit_rate = (current_price - cost_price) / cost_price * 100

### Requirement: Total portfolio value calculation
The system SHALL calculate the total portfolio value as the sum of cash balance and the market value of all stock holdings.

#### Scenario: Calculate total portfolio value
- **WHEN** system retrieves portfolio overview
- **THEN** system sums cash balance and (current_price * quantity) for all holdings