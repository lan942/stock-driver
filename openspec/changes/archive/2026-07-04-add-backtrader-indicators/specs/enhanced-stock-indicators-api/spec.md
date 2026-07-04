## ADDED Requirements

### Requirement: GET /api/stocks/<code>/indicators
The system SHALL provide a new API endpoint for querying technical indicators with flexible indicator selection.

Request parameters:
- `days` (int, optional, default 120): Number of trading days of data to use
- `indicators` (string, optional, default all): Comma-separated list of indicator names. If omitted, return all supported indicators.
- `params` (string, optional): URL-encoded JSON string of per-indicator parameters. E.g. `{"MA":{"period":50},"RSI":{"period":10}}`

Response format SHALL be:
```json
{
  "code": "000001",
  "name": "平安银行",
  "dates": ["2025-01-02", "2025-01-03", ...],
  "prices": {
    "open": [...],
    "high": [...],
    "low": [...],
    "close": [...],
    "volume": [...]
  },
  "indicators": {
    "ma": {"values": [...], "params": {"period": 20}},
    "rsi": {"values": [...], "params": {"period": 14}},
    "macd": {"macd": [...], "signal": [...], "histogram": [...]},
    ...
  }
}
```

#### Scenario: Request all default indicators
- **WHEN** GET `/api/stocks/000001/indicators?days=60`
- **THEN** response SHALL contain `dates`, `prices`, and all supported indicator types with default parameters

#### Scenario: Request specific indicators
- **WHEN** GET `/api/stocks/000001/indicators?indicators=MA,RSI`
- **THEN** response SHALL only contain `ma` and `rsi` in the `indicators` field

#### Scenario: Request with custom parameters
- **WHEN** GET `/api/stocks/000001/indicators?indicators=MA&params={"MA":{"period":50}}`
- **THEN** the `ma` values SHALL be computed with period=50

#### Scenario: Stock not found
- **WHEN** GET `/api/stocks/NONEXIST/indicators`
- **THEN** response SHALL be 404 with `{"error": "股票不存在"}`

#### Scenario: No data available
- **WHEN** GET `/api/stocks/000001/indicators` and stock has no daily data
- **THEN** response SHALL be 404 with `{"error": "没有找到数据"}`

### Requirement: GET /api/stocks/<code>/indicators/list
The system SHALL provide an API to list all available indicator types and their default parameters.

Response format SHALL be:
```json
{
  "indicators": [
    {"id": "MA", "name": "移动平均线", "default_params": {"period": 20}, "description": "简单移动平均线"},
    {"id": "EMA", "name": "指数移动平均线", "default_params": {"period": 20}, "description": "指数加权移动平均线"},
    {"id": "MACD", "name": "MACD", "default_params": {"period_me1": 12, "period_me2": 26, "period_signal": 9}, "description": "异同移动平均线"},
    {"id": "RSI", "name": "相对强弱指标", "default_params": {"period": 14}, "description": "相对强弱指数"},
    {"id": "BOLL", "name": "布林带", "default_params": {"period": 20, "devfactor": 2}, "description": "布林带通道"},
    {"id": "KDJ", "name": "KDJ指标", "default_params": {"period": 14, "period_d": 3}, "description": "随机指标"},
    {"id": "ATR", "name": "平均真实波幅", "default_params": {"period": 14}, "description": "平均真实波幅"},
    {"id": "ADX", "name": "平均趋向指数", "default_params": {"period": 14}, "description": "平均趋向指数"}
  ]
}
```

#### Scenario: List available indicators
- **WHEN** GET `/api/stocks/000001/indicators/list`
- **THEN** response SHALL contain an array of indicator objects with id, name, default_params, and description