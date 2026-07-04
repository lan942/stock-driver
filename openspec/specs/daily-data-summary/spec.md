# daily-data-summary Specification

## Purpose
TBD - created by archiving change add-daily-data-summary. Update Purpose after archive.
## Requirements
### Requirement: Daily data summary API
The system SHALL provide a GET API endpoint `/stocks/daily_summary` that returns the count of StockDaily records grouped by date.

#### Scenario: Query daily summary without date range
- **WHEN** client sends GET request to `/stocks/daily_summary`
- **THEN** system returns data for the last 90 days by default
- **AND** each entry contains `date`, `count`, `total_stocks`, and `coverage_percent`

#### Scenario: Query daily summary with date range
- **WHEN** client sends GET request with `start_date=2025-01-01` and `end_date=2025-01-31`
- **THEN** system returns data only for dates within the specified range

#### Scenario: Invalid date format
- **WHEN** client sends GET request with invalid date format like `start_date=2025/01/01`
- **THEN** system returns HTTP 400 with error message

### Requirement: Daily data summary service method
The system SHALL provide a service method `get_daily_summary` in `stock_service.py` that performs the database query and calculates coverage.

#### Scenario: Calculate daily coverage
- **WHEN** `get_daily_summary` is called with date range
- **THEN** method queries StockDaily grouped by date
- **AND** calculates coverage as (daily_count / total_stocks) * 100
- **AND** returns list of dicts with date, count, total_stocks, coverage_percent

### Requirement: Frontend data summary page
The system SHALL provide a frontend page at `/data-summary` displaying daily data coverage.

#### Scenario: Page displays daily summary table
- **WHEN** user navigates to `/data-summary`
- **THEN** page displays a table with columns: Date, Count, Total Stocks, Coverage
- **AND** coverage is displayed with progress bar or color coding

#### Scenario: Date range filter
- **WHEN** user selects start and end dates in the date picker
- **THEN** table refreshes to show only data within the selected range

#### Scenario: Sort by date or coverage
- **WHEN** user clicks on table column header
- **THEN** table sorts by that column in ascending or descending order

### Requirement: Router configuration
The system SHALL add a route `/data-summary` mapping to the new DataSummary component.

#### Scenario: Route registered
- **WHEN** frontend application starts
- **THEN** route `/data-summary` is registered and accessible

