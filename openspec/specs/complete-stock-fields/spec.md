# complete-stock-fields Specification

## Purpose
定义股票数据模型的完整字段结构，Stock表存储股票基本信息，StockDaily表存储每日行情数据，确保爬取的数据完整保存，满足全市场分析需求。

## Requirements

### Requirement: Stock模型定义

Stock模型 SHALL 存储股票基本信息（代码、名称、行业、板块），不存储行情数据。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| code | String | 股票代码（唯一） |
| name | String | 股票名称 |
| industry | String | 所属行业 |
| sector | String | 所属板块 |

#### Scenario: Stock模型字段存在
- **WHEN** 创建Stock模型实例
- **THEN** 实例 SHALL 包含id、code、name、industry、sector字段
- **AND** industry和sector字段 SHALL 允许为NULL

#### Scenario: Stock模型持久化
- **WHEN** Stock记录保存到数据库
- **THEN** 数据库表 SHALL 包含id、code、name、industry、sector列

### Requirement: StockDaily模型定义

StockDaily模型 SHALL 存储每日行情数据，支持按日期回溯查询。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| code | String | 股票代码 |
| date | Date | 行情日期 |
| open | Float | 开盘价（元） |
| high | Float | 最高价（元） |
| low | Float | 最低价（元） |
| close | Float | 收盘价（元） |
| volume | Float | 成交量（股） |
| turnover | Float | 成交额（元） |
| turnover_rate | Float | 换手率（百分比） |
| change_percent | Float | 涨跌幅（百分比） |
| pe | Float | 市盈率（动态，允许NULL） |
| pb | Float | 市净率（允许NULL） |
| market_cap | Float | 总市值（元，允许NULL） |

#### Scenario: StockDaily模型字段存在
- **WHEN** 创建StockDaily模型实例
- **THEN** 实例 SHALL 包含以上所有字段
- **AND** code和date字段为非空，其他字段允许为NULL

#### Scenario: StockDaily唯一约束
- **WHEN** 尝试插入重复的(code, date)记录
- **THEN** 数据库 SHALL 拒绝插入（唯一约束生效）
- **AND** 系统 SHALL 执行更新操作（UPSERT语义）

### Requirement: 爬虫数据写入StockDaily

系统 SHALL 在实时行情爬取和日线数据爬取成功后，将数据写入StockDaily表。

#### Scenario: 实时行情数据写入StockDaily
- **WHEN** 实时行情爬取成功
- **THEN** 系统 SHALL 将每条股票的行情数据写入StockDaily表
- **AND** date字段设置为当前日期
- **AND** 若该(code, date)已存在，则更新现有记录

#### Scenario: 日线数据写入StockDaily
- **WHEN** 日线数据爬取成功（腾讯源）
- **THEN** 系统 SHALL 将多日行情数据写入StockDaily表
- **AND** 每条记录的date字段设置为对应交易日
- **AND** pe/pb/market_cap字段允许为NULL（腾讯源不提供）

#### Scenario: 字段值为NULL时跳过更新
- **WHEN** 爬虫返回的某字段值为NULL或缺失
- **THEN** 系统 SHALL 跳过该字段的更新，保持原有值（仅适用于已有记录的更新）

### Requirement: API返回所有字段

API在返回股票数据时，SHALL 包含所有关键字段。

#### Scenario: 股票列表API（GET /api/stocks）
- **WHEN** 调用GET /api/stocks
- **THEN** 返回数据 SHALL 包含code、name、price(close)、open、high、low、change_percent、volume、turnover、turnover_rate、pe、pb、market_cap、price_date字段

#### Scenario: 单个股票API（GET /api/stocks/{code}）
- **WHEN** 调用GET /api/stocks/{code}
- **THEN** 返回数据 SHALL 包含code、name、industry、sector及Stock表中所有字段

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    数据流向图                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                                          │
│  │ StockList    │                                          │
│  │ Crawler      │─── code/name ──► Stock模型 ──► stocks表   │
│  └──────────────┘                                          │
│                                                             │
│  ┌──────────────┐                                          │
│  │ Realtime     │                                          │
│  │ Crawler      │─── 当日行情 ──► StockDaily ──►stock_daily表│
│  │ (Eastmoney)  │                                          │
│  └──────────────┘                                          │
│                                                             │
│  ┌──────────────┐                                          │
│  │ Daily Crawler│─── 历史行情 ──► StockDaily ──►stock_daily表│
│  │  (Tencent)   │                                          │
│  └──────────────┘                                          │
│                                                             │
│  API (routes.py)                                            │
│  (GET /api/stocks, GET /api/stocks/{code},                 │
│   GET /api/stocks/{code}/daily, GET /api/stocks/top/*)     │
│      │                                                      │
│      ▼                                                      │
│  前端展示                                                    │
│  (股票列表、详情页、涨跌排行)                                   │
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

### Decision: StockDaily表为主行情数据源

**选择**: 所有行情数据（实时和历史）统一写入StockDaily表

**理由**:
- StockDaily表支持按日期回溯查询历史数据
- 避免Stock表和StockDaily表数据不一致
- 简化数据模型，Stock表专注于基本信息管理

**替代方案**:
- Stock表存储最新行情，StockDaily存储历史：容易出现数据不一致

### Decision: StockDaily的(code, date)唯一约束

**选择**: 在StockDaily表上添加(code, date)唯一约束

**理由**:
- 防止重复爬取导致数据重复
- 支持UPSERT语义（INSERT OR REPLACE）
- 提升查询性能（自动创建索引）

**替代方案**:
- 应用层去重：不如数据库约束可靠
