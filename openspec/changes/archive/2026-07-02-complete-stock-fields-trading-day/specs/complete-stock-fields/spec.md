# complete-stock-fields Specification

## Purpose
补全Stock和StockDaily模型的关键字段，确保爬取的数据完整保存，满足全市场分析需求。

## ADDED Requirements

### Requirement: Stock模型增加关键字段

Stock模型 SHALL 包含以下关键字段，用于存储股票的实时行情数据：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| open | Float | 开盘价 |
| high | Float | 最高价 |
| low | Float | 最低价 |
| turnover_rate | Float | 换手率（百分比） |
| pe | Float | 市盈率（动态） |
| pb | Float | 市净率 |
| market_cap | Float | 总市值（元） |

#### Scenario: 字段存在
- **WHEN** 创建Stock模型实例
- **THEN** 实例 SHALL 包含open、high、low、turnover_rate、pe、pb、market_cap字段
- **AND** 这些字段 SHALL 允许为NULL（初始状态或数据未更新时）

#### Scenario: 字段持久化
- **WHEN** Stock记录保存到数据库
- **THEN** 数据库表 SHALL 包含open、high、low、turnover_rate、pe、pb、market_cap列

### Requirement: StockDaily模型增加换手率字段

StockDaily模型 SHALL 包含turnover_rate字段，用于存储每日换手率数据。

#### Scenario: 字段存在
- **WHEN** 创建StockDaily模型实例
- **THEN** 实例 SHALL 包含turnover_rate字段
- **AND** 字段 SHALL 允许为NULL

#### Scenario: 字段持久化
- **WHEN** StockDaily记录保存到数据库
- **THEN** 数据库表 SHALL 包含turnover_rate列

### Requirement: 调度器保存所有字段

调度器在爬取实时行情成功后，SHALL 更新Stock记录的所有字段。

#### Scenario: 更新所有字段
- **WHEN** 实时行情爬取成功
- **THEN** 调度器 SHALL 更新Stock记录的以下字段：
  - price（收盘价）
  - open（开盘价）
  - high（最高价）
  - low（最低价）
  - volume（成交量）
  - turnover（成交额）
  - turnover_rate（换手率）
  - change_percent（涨跌幅）
  - pe（市盈率）
  - pb（市净率）
  - market_cap（总市值）
  - price_date（价格日期）

#### Scenario: 字段值为NULL时跳过
- **WHEN** 爬虫返回的某字段值为NULL或缺失
- **THEN** 调度器 SHALL 跳过该字段的更新，保持原有值

### Requirement: API返回所有字段

API在返回股票数据时，SHALL 包含所有关键字段。

#### Scenario: 股票列表API
- **WHEN** 调用GET /api/stocks
- **THEN** 返回数据 SHALL 包含open、high、low、turnover_rate、pe、pb、market_cap字段

#### Scenario: 单个股票API
- **WHEN** 调用GET /api/stocks/{code}
- **THEN** 返回数据 SHALL 包含open、high、low、turnover_rate、pe、pb、market_cap字段

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    数据流向图                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  东方财富API                                                 │
│      │                                                      │
│      ▼                                                      │
│  StockRealtimeCrawler                                       │
│  (stock_zh_a_spot_em)                                       │
│      │                                                      │
│      ▼                                                      │
│  normalizer.py                                              │
│  (字段标准化: 今开→open, 最高→high,                          │
│   最低→low, 换手率→turnover_rate)                            │
│      │                                                      │
│      ▼                                                      │
│  scheduler.py                                               │
│  (save_realtime_quotes: 更新Stock所有字段)                   │
│      │                                                      │
│      ▼                                                      │
│  Stock模型                                                  │
│  (open, high, low, turnover_rate, price,                    │
│   volume, turnover, change_percent, price_date)             │
│      │                                                      │
│      ▼                                                      │
│  SQLite数据库                                                │
│  (stocks表)                                                  │
│      │                                                      │
│      ▼                                                      │
│  API (routes.py)                                            │
│  (GET /api/stocks, GET /api/stocks/{code})                  │
│      │                                                      │
│      ▼                                                      │
│  前端展示                                                    │
│  (股票列表、详情页)                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Design Decisions

### Decision: 使用Float类型存储价格和比率

**选择**: 所有价格字段和比率字段使用SQLAlchemy的Float类型

**理由**:
- 股票价格可能有小数（如12.34元）
- 换手率是百分比（如2.35%）
- Float类型能够准确存储这些数据
- SQLite对Float类型支持良好

**替代方案**:
- 使用Decimal类型：精度更高，但在Python中处理稍复杂

### Decision: 字段允许为NULL

**选择**: 所有新增字段允许为NULL

**理由**:
- 初始状态下数据可能为空
- 爬虫可能无法获取某些字段（API变更）
- 向后兼容，不影响现有数据

**替代方案**:
- 使用默认值：可能掩盖数据缺失问题

### Decision: 调度器更新所有字段

**选择**: 在调度器中统一更新所有字段

**理由**:
- 确保数据一致性
- 减少代码重复
- 便于维护和扩展

**替代方案**:
- 在多个地方更新字段：容易遗漏，数据不一致

## Implementation Notes

- 需要创建数据库迁移脚本，为stocks表和stock_daily表增加新列
- 需要更新Stock模型和StockDaily模型的定义
- 需要更新scheduler.py中的save_realtime_quotes函数
- 需要更新routes.py中的API返回数据
- 需要更新前端以显示新字段