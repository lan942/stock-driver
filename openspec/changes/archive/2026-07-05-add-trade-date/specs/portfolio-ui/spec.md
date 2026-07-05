## MODIFIED Requirements

### Requirement: Add transaction dialog
The portfolio page SHALL provide a button to open a dialog for recording new transactions, which SHALL include a date picker for selecting the transaction date (defaulting to today).

#### Scenario: Add buy transaction with date selection
- **WHEN** user selects type 'buy', fills in transaction date (defaults to today), searches and selects stock code via autocomplete, fills in quantity (100 multiples) and price
- **THEN** system records the transaction with the selected date and updates the transaction history

#### Scenario: Add sell transaction with date selection
- **WHEN** user selects type 'sell', fills in transaction date (defaults to today), selects a stock from the holdings list (dropdown), fills in quantity (100 multiples, ≤ holding quantity) and price
- **THEN** system records the transaction with the selected date and updates the transaction history

### Requirement: Transaction history section
The portfolio page SHALL display a section showing recent transactions with type, stock, quantity, price, amount, trade_date, and timestamp.

#### Scenario: Display transaction history with trade_date
- **WHEN** user visits the portfolio page
- **THEN** system shows a table of recent transactions sorted by time, including a "交易日期" column showing trade_date

## ADDED Requirements

### Requirement: Transaction date picker in add dialog
The add transaction dialog SHALL include a date picker field (el-date-picker, type="date") labeled "交易日期", defaulting to the current date.

#### Scenario: Default transaction date is today
- **WHEN** user opens the add transaction dialog
- **THEN** the transaction date field SHALL be pre-filled with today's date

#### Scenario: User can select a past date
- **WHEN** user clicks on the transaction date picker
- **THEN** system shows a calendar allowing selection of any past date