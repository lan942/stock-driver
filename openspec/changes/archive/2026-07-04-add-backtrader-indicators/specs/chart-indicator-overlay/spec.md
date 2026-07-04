## ADDED Requirements

### Requirement: K-line Chart with Indicator Overlay
The stock detail page SHALL display an enhanced candlestick chart with selectable technical indicator overlays.

The chart SHALL:
- Display the candlestick chart as currently implemented
- Provide a control panel above or beside the chart for selecting overlay indicators
- Support overlay of MA series (MA5, MA10, MA20, MA60) as line series on the chart
- Support overlay of Bollinger Bands (upper, middle, lower) as line series on the chart
- Allow users to toggle each overlay on/off via checkbox or switch controls

#### Scenario: Load chart with default overlays
- **WHEN** the stock detail page loads
- **THEN** the chart SHALL display candlestick data and MA5/MA10/MA20/MA60 as overlay lines by default

#### Scenario: Toggle overlay on
- **WHEN** user checks "布林带" in the overlay controls
- **THEN** Bollinger Bands (three lines: upper, middle, lower) SHALL appear on the chart

#### Scenario: Toggle overlay off
- **WHEN** user unchecks "MA60" in the overlay controls
- **THEN** the MA60 line SHALL be removed from the chart

#### Scenario: Change overlay parameters
- **WHEN** user changes MA period from 20 to 50 in the overlay settings
- **THEN** the chart SHALL refresh with MA50 line instead of MA20

### Requirement: Expanded Indicator Table
The stock detail page SHALL display an expanded technical indicators table below the chart.

The table SHALL include these columns:
- `date`: Trading date
- `close`: Closing price
- MA columns: `ma5`, `ma10`, `ma20`, `ma60`
- `macd`, `signal`, `histogram`: MACD triplet
- `rsi`: RSI value
- `boll_upper`, `boll_mid`, `boll_lower`: Bollinger Bands values
- `kdj_k`, `kdj_d`, `kdj_j`: KDJ triplet
- `atr`: ATR value
- `adx`: ADX value

The table SHALL be horizontally scrollable if columns exceed visible width.

Data SHALL be fetched from the new `/api/stocks/<code>/indicators` endpoint.

#### Scenario: Table displays all indicator columns
- **WHEN** stock detail page loads and indicator data is returned
- **THEN** the table SHALL render all non-null indicator columns with formatted numeric values

#### Scenario: Table scrolls horizontally
- **WHEN** the indicator columns exceed the container width
- **THEN** the table SHALL have a horizontal scrollbar

### Requirement: Indicator Selection Panel
The stock detail page SHALL include a panel for selecting which indicators to display.

The panel SHALL:
- List all available indicator types (fetched from `/api/stocks/<code>/indicators/list`)
- Provide checkboxes to toggle each indicator on/off in the table
- Provide parameter inputs (e.g., period number) for adjustable indicators
- Show a "刷新" button to recompute with current selections

#### Scenario: Panel loads available indicators
- **WHEN** stock detail page loads
- **THEN** the indicator panel SHALL fetch and display all indicator types from `/api/stocks/<code>/indicators/list`

#### Scenario: User selects indicators and refreshes
- **WHEN** user checks "ATR", sets period to 10, and clicks "刷新"
- **THEN** the page SHALL call `/api/stocks/<code>/indicators?indicators=ATR&params={"ATR":{"period":10}}` and update the table