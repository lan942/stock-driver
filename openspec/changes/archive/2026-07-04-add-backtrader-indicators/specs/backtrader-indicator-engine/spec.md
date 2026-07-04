## ADDED Requirements

### Requirement: Indicator Engine Service
The system SHALL provide an `IndicatorEngine` service class that wraps Backtrader Cerebro for on-demand indicator computation.

The engine SHALL:
- Accept a pandas DataFrame with columns: `date`, `open`, `high`, `low`, `close`, `volume`
- Accept a list of indicator descriptor objects, each containing `type` (indicator name) and optional `params` (dict of parameters)
- Create a Backtrader PandasData feed from the DataFrame
- Run a minimal Cerebro instance (no Broker, no cash) with a strategy that declares the requested indicators
- Return results as dict keyed by indicator name, each containing computed values per data row

The engine SHALL support at minimum these indicator types:
- `MA`: SimpleMovingAverage (param: `period`, default 20)
- `EMA`: ExponentialMovingAverage (param: `period`, default 20)
- `MACD`: MACD (params: `period_me1`=12, `period_me2`=26, `period_signal`=9)
- `RSI`: RelativeStrengthIndex (param: `period`, default 14)
- `BOLL`: BollingerBands (params: `period`=20, `devfactor`=2)
- `KDJ`: Stochastic + SMA combo (params: `period`=14, `period_d`=3)
- `ATR`: AverageTrueRange (param: `period`, default 14)
- `ADX`: AverageDirectionalIndex (param: `period`, default 14)

The engine SHALL NOT execute any buy/sell trades or configure a Broker.

#### Scenario: Compute default indicators
- **WHEN** `IndicatorEngine.compute(df, [{"type": "MA"}, {"type": "RSI"}])` is called
- **THEN** the result SHALL contain `ma` and `rsi` arrays computed with default parameters (period=20, period=14 respectively)

#### Scenario: Compute indicator with custom parameters
- **WHEN** `IndicatorEngine.compute(df, [{"type": "MA", "params": {"period": 50}}])` is called
- **THEN** the `ma` array SHALL be a 50-period SMA

#### Scenario: Compute multiple indicators simultaneously
- **WHEN** `IndicatorEngine.compute(df, [{"type": "MACD"}, {"type": "BOLL"}, {"type": "KDJ"}])` is called
- **THEN** the result SHALL contain `macd`, `boll`, and `kdj` keys computed in a single Cerebro run

#### Scenario: Invalid indicator name raises error
- **WHEN** `IndicatorEngine.compute(df, [{"type": "UNKNOWN"}])` is called
- **THEN** the engine SHALL raise `ValueError` with message listing supported indicator types

### Requirement: Result Caching
The engine SHALL cache computed results to avoid redundant calculations.

Caching rules:
- Cache key SHALL be: `f"{code}_{days}_{sorted_indicators_json}"`
- Cache TTL SHALL be 300 seconds (5 minutes)
- Cache SHALL be in-memory, LRU with max 100 entries
- Cache SHALL be invalidated when new daily data for that stock is inserted via `save_daily_batch`

#### Scenario: Cache hit returns cached data
- **WHEN** the same `code`, `days`, and indicators are requested within 5 minutes
- **THEN** the engine SHALL return cached data without recomputing

#### Scenario: Cache miss triggers computation
- **WHEN** a request has no matching cache entry
- **THEN** the engine SHALL compute indicators, cache the result, and return it

### Requirement: Data Feed Adapter
The system SHALL provide a function to convert `stock_daily` database records into Backtrader-compatible DataFrame.

The adapter SHALL:
- Accept `code`, optional `days` (default 120), optional `start_date`/`end_date`
- Query `StockDaily` table ordered by date ascending
- Return a DataFrame with columns: `open`, `high`, `low`, `close`, `volume`, `openinterest` (all 0)

#### Scenario: Successful data conversion
- **WHEN** stock_daily records exist for code "000001" with 60 days of data
- **THEN** the adapter SHALL return a DataFrame with 60 rows and 6 columns

#### Scenario: No data available
- **WHEN** no stock_daily records exist for the given code
- **THEN** the adapter SHALL return `None`