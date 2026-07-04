## ADDED Requirements

### Requirement: Portfolio management tab in navigation
The frontend SHALL add a "持仓管理" tab in the main navigation bar that links to the portfolio page.

#### Scenario: Navigate to portfolio page
- **WHEN** user clicks "持仓管理" in the navigation bar
- **THEN** system navigates to the portfolio management page

### Requirement: Portfolio overview section
The portfolio page SHALL display an overview section with cards showing total portfolio value, cash balance, total profit, and total profit rate.

#### Scenario: Display portfolio overview
- **WHEN** user visits the portfolio page
- **THEN** system shows cards with total_value, cash_balance, total_profit, total_profit_rate

### Requirement: Holdings table with detailed information
The portfolio page SHALL display a table showing all stock holdings with columns for stock code, name, quantity, cost price, current price, market value, profit, and profit rate.

#### Scenario: Display holdings table
- **WHEN** user visits the portfolio page
- **THEN** system shows a table with all holdings and their details

### Requirement: Add holding dialog
The portfolio page SHALL provide a button to open a dialog for adding new stock holdings.

#### Scenario: Open add holding dialog
- **WHEN** user clicks "添加持仓" button
- **THEN** system opens a dialog with fields for stock code, quantity, and cost price

#### Scenario: Add new holding successfully
- **WHEN** user fills in stock code, quantity, cost price and clicks "确认"
- **THEN** system adds the holding and refreshes the holdings table

### Requirement: Edit holding functionality
The portfolio page SHALL allow editing existing holdings through a dialog.

#### Scenario: Edit holding
- **WHEN** user clicks "编辑" on a holding row
- **THEN** system opens a dialog pre-filled with current holding information

### Requirement: Delete holding functionality
The portfolio page SHALL allow deleting holdings with a confirmation prompt.

#### Scenario: Delete holding
- **WHEN** user clicks "删除" on a holding row and confirms
- **THEN** system removes the holding and refreshes the table

### Requirement: Transaction history section
The portfolio page SHALL display a section showing recent transactions with type, stock, quantity, price, amount, and timestamp.

#### Scenario: Display transaction history
- **WHEN** user visits the portfolio page
- **THEN** system shows a table of recent transactions sorted by time

### Requirement: Add transaction dialog
The portfolio page SHALL provide a button to open a dialog for recording new transactions.

#### Scenario: Add buy transaction
- **WHEN** user selects type 'buy', fills in stock code, quantity, price and clicks "确认"
- **THEN** system records the transaction and updates the transaction history

#### Scenario: Add sell transaction
- **WHEN** user selects type 'sell', fills in stock code, quantity, price and clicks "确认"
- **THEN** system records the transaction and updates the transaction history

### Requirement: Cash balance update functionality
The portfolio page SHALL provide a button to open a dialog for updating cash balance.

#### Scenario: Update cash balance
- **WHEN** user enters an amount and clicks "确认"
- **THEN** system updates the cash balance and refreshes the overview