## ADDED Requirements

### Requirement: 实时行情按日期持久化存储
系统 MUST 在每次实时行情爬取成功后，将每条股票的行情数据保存到 StockDaily 表中，记录数据对应的日期 (date 字段)。

#### Scenario: 正常爬取后写入 StockDaily
- **WHEN** 实时行情爬取成功，save_realtime_quotes 被调用
- **THEN** 每条股票的 (code, price_date, open, high, low, close, volume, turnover, turnover_rate, change_percent, pe, pb, market_cap) MUST 写入 StockDaily 表
- **AND** 同一天同一股票的旧记录 MUST 被新数据覆盖 (INSERT OR REPLACE)

#### Scenario: 指定日期写入
- **WHEN** 用户在前端选择了数据日期（如 2026-07-01）并触发爬取
- **THEN** StockDaily 表中的 date 字段 MUST 为用户指定的日期，而非系统当前日期

### Requirement: StockDaily 表包含 PE/PB/市值字段
StockDaily 表 SHALL 包含 pe（市盈率）、pb（市净率）、market_cap（总市值）三个字段。

#### Scenario: PE/PB 数据写入
- **WHEN** 实时行情数据包含 pe 和 pb 字段
- **THEN** 这些值 MUST 被正确写入 StockDaily 表的 pe 和 pb 列

#### Scenario: 缺乏 PE/PB 数据的股票
- **WHEN** 某只股票的实时行情数据中 pe 或 pb 为空
- **THEN** StockDaily 表中对应的 pe 或 pb 列 SHALL 为 NULL

### Requirement: 前端按日期查询历史行情
股票列表页 SHALL 提供日期选择器，用户可切换查看任意有数据的日期。

#### Scenario: 默认显示最新数据
- **WHEN** 用户打开股票列表页，未选择日期
- **THEN** 页面 MUST 显示 Stock 表中最新行情数据（保持现有行为）

#### Scenario: 选择有数据的日期
- **WHEN** 用户通过日期选择器选择了一个有 StockDaily 记录的日期
- **THEN** 页面 MUST 展示该日期的历史行情数据
- **AND** 每条股票显示该日期对应的 price/open/high/low/close/change_percent/pe/pb 等字段

#### Scenario: 选择无数据的日期
- **WHEN** 用户选择的日期在 StockDaily 表中没有记录
- **THEN** 页面 SHALL 显示"暂无数据"提示

### Requirement: API 支持按日期查询
`GET /api/stocks` 接口 SHALL 支持可选的 `date` 查询参数。

#### Scenario: 不传 date 参数
- **WHEN** 请求 `GET /api/stocks` 不带 date 参数
- **THEN** 系统 MUST 返回 Stock 表最新行情数据（保持现有行为）

#### Scenario: 传 date 参数查询历史
- **WHEN** 请求 `GET /api/stocks?date=2026-07-01`
- **THEN** 系统 MUST 查询 StockDaily 表中 date=2026-07-01 的记录
- **AND** 返回结果 MUST 包含 code/name/date/open/high/low/close/volume/change_percent/pe/pb/market_cap
