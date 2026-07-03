## ADDED Requirements

### Requirement: 涨跌排行按日期查询
系统 SHALL 提供按指定交易日查询涨幅/跌幅排行榜的能力，数据来源于 `stock_daily` 表。

#### Scenario: 指定日期查询涨幅榜
- **WHEN** 客户端调用 `GET /api/stocks/top/gainers?date=2026-07-02&limit=20`
- **THEN** 系统返回 2026-07-02 当日 `change_percent` 降序排列的前 20 条记录，每条包含 code、name、price(close)、change_percent、price_date 字段

#### Scenario: 指定日期查询跌幅榜
- **WHEN** 客户端调用 `GET /api/stocks/top/losers?date=2026-07-02&limit=10`
- **THEN** 系统返回 2026-07-02 当日 `change_percent` 升序排列的前 10 条记录

#### Scenario: 查询日期无数据
- **WHEN** 客户端调用 `GET /api/stocks/top/gainers?date=2025-01-01`（该日期无爬取数据）
- **THEN** 系统返回空列表 `[]`，HTTP 状态码 200

### Requirement: 默认返回最新交易日
系统 SHALL 在未传入 `date` 参数时，自动使用 `stock_daily` 表中 `MAX(date)` 作为查询日期。

#### Scenario: 不传日期参数
- **WHEN** 客户端调用 `GET /api/stocks/top/gainers?limit=10`（未传 date）
- **THEN** 系统查询 `SELECT MAX(date) FROM stock_daily` 得到最新日期，返回该日期的涨幅榜，响应中 `price_date` 字段标明实际使用的日期

#### Scenario: stock_daily 表为空
- **WHEN** 客户端调用 `GET /api/stocks/top/gainers` 且 `stock_daily` 表无任何数据
- **THEN** 系统返回空列表 `[]`，HTTP 状态码 200

### Requirement: 日期格式校验
系统 SHALL 校验 `date` 参数格式为 `YYYY-MM-DD`，非法格式返回 400 错误。

#### Scenario: 非法日期格式
- **WHEN** 客户端调用 `GET /api/stocks/top/gainers?date=2026/07/02`
- **THEN** 系统返回 HTTP 400，响应体 `{"error": "日期格式错误，应为 YYYY-MM-DD"}`

#### Scenario: 合法日期格式
- **WHEN** 客户端调用 `GET /api/stocks/top/gainers?date=2026-07-02`
- **THEN** 系统正常处理请求，返回该日期排行数据

### Requirement: 响应包含数据日期标识
系统 SHALL 在排行接口响应中包含 `price_date` 字段，标明当前返回数据对应的交易日。

#### Scenario: 响应字段验证
- **WHEN** 客户端获取排行数据
- **THEN** 响应体为数组，每个元素包含字段：`code`(string)、`name`(string)、`price`(number, 即收盘价 close)、`change_percent`(number)、`price_date`(string, YYYY-MM-DD 格式)

### Requirement: 前端日期选择器交互
前端 TopStocks 页面 SHALL 提供日期选择器，支持切换历史日期查看排行，默认显示最新数据日期。

#### Scenario: 页面初次加载
- **WHEN** 用户打开 TopStocks 页面
- **THEN** 日期选择器默认填入 `stock_daily` 表最新日期，页面展示该日涨跌排行，顶部提示条显示"当前显示：{date} 的排行数据"

#### Scenario: 切换历史日期
- **WHEN** 用户在日期选择器选择 2026-06-30
- **THEN** 页面自动重新加载，展示 2026-06-30 的涨跌排行，提示条更新为"当前显示：2026-06-30 的排行数据"

#### Scenario: 清空日期回到最新
- **WHEN** 用户清空日期选择器
- **THEN** 页面自动重新加载最新交易日的排行数据，提示条显示最新日期

#### Scenario: 切换涨跌标签页
- **WHEN** 用户在"涨幅榜"和"跌幅榜"标签页之间切换
- **THEN** 保持当前选中的日期，仅切换榜单数据来源
