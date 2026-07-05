## MODIFIED Requirements

### Requirement: Portfolio model tracks stock holdings
The system SHALL maintain a Portfolio model that tracks user's stock holdings, including stock code, quantity, average cost price, and available quantity (T+1 rule).

#### Scenario: Create new portfolio entry
- **WHEN** user adds a new stock holding with code, quantity (must be multiple of 100), and cost price
- **THEN** system validates quantity % 100 === 0, creates a new Portfolio record with 0 available quantity on the same day

#### Scenario: Update portfolio entry
- **WHEN** user modifies an existing portfolio entry's quantity or cost price
- **THEN** system updates the Portfolio record with the new values

#### Scenario: Delete portfolio entry
- **WHEN** user removes a portfolio entry
- **THEN** system deletes the corresponding Portfolio record

#### Scenario: Get holdings with available quantity
- **WHEN** system retrieves portfolio holdings
- **THEN** system returns available_quantity = total_quantity - today_buy_quantity for each holding, where today_buy_quantity is the sum of buy transactions with trade_date = today