## Purpose
Provide a user-friendly interface for managing stock portfolio, including holdings tracking, transaction recording, and portfolio overview.

## Requirements

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
The portfolio page SHALL display a table showing all stock holdings with columns for stock code, name, quantity, cost price, current price, market value, profit, and profit rate. Columns SHALL have different widths to fit content and fill the parent container.

#### Scenario: Display holdings table
- **WHEN** user visits the portfolio page
- **THEN** system shows a table with all holdings and their details

### Requirement: Stock code search with autocomplete
The stock code field in the add holding dialog SHALL support autocomplete search with debounce.

#### Scenario: Search stock by code or name
- **WHEN** user types in the stock code field
- **THEN** system waits 300ms (debounce) before sending a search request to the backend

#### Scenario: Display search results
- **WHEN** the backend returns results
- **THEN** system displays a dropdown list matching stock codes or names from the StockBasic table

#### Scenario: No search query
- **WHEN** the search query is empty
- **THEN** system clears the dropdown list without making a request

### Requirement: Quantity validation (100 multiples)
The quantity field SHALL enforce A-share trading rules: quantity must be a multiple of 100.

#### Scenario: Validate quantity on input
- **WHEN** user inputs quantity
- **THEN** the input control SHALL use step=100 and min=100 to enforce the rule

#### Scenario: Validate quantity on submit
- **WHEN** user submits the form
- **THEN** system validates that quantity % 100 === 0, otherwise shows an error message

### Requirement: Add holding dialog
The portfolio page SHALL provide a button to open a dialog for adding new stock holdings.

#### Scenario: Open add holding dialog
- **WHEN** user clicks "添加持仓" button
- **THEN** system opens a dialog with fields for stock code (autocomplete), quantity (step=100), and cost price

#### Scenario: Add new holding successfully
- **WHEN** user fills in stock code, quantity (100 multiples), cost price and clicks "确认"
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

### Requirement: Clear all transactions
The portfolio page SHALL provide a button to clear all transaction records.

#### Scenario: Clear all transactions
- **WHEN** user clicks "清除记录" button and confirms the action
- **THEN** system deletes all transaction records and refreshes the data

### Requirement: Add transaction dialog
The portfolio page SHALL provide a button to open a dialog for recording new transactions.

#### Scenario: Add buy transaction
- **WHEN** user selects type 'buy', searches and selects stock code via autocomplete, fills in quantity (100 multiples) and price
- **THEN** system records the transaction and updates the transaction history

#### Scenario: Add sell transaction
- **WHEN** user selects type 'sell', selects a stock from the holdings list (dropdown), fills in quantity (100 multiples, ≤ holding quantity) and price
- **THEN** system records the transaction and updates the transaction history

#### Scenario: Sell stock selection from holdings
- **WHEN** user switches transaction type to 'sell'
- **THEN** the stock code selector SHALL show only stocks currently held in the portfolio

#### Scenario: Sell quantity upper limit
- **WHEN** user selects a holding for selling
- **THEN** the quantity input SHALL show a max bound equal to the current holding quantity

### Requirement: Cash balance update functionality
The portfolio page SHALL provide a button to open a dialog for updating cash balance.

#### Scenario: Update cash balance
- **WHEN** user enters an amount and clicks "确认"
- **THEN** system updates the cash balance and refreshes the overview