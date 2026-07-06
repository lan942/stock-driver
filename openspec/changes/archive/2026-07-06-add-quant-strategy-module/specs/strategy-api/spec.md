## ADDED Requirements

### Requirement: 获取每日推荐
系统 SHALL 提供 API `GET /api/strategy/recommendations` 返回当日的买入推荐列表。

请求参数：
- `date`（可选）：指定日期，默认最新交易日

响应字段：
- `code`：股票代码
- `name`：股票名称
- `score`：综合评分
- `factor_scores`：各因子得分明细
- `suggested_buy_price`：建议买入价
- `target_price`：目标止盈价
- `stop_price`：止损价
- `current_close`：当前收盘价

#### Scenario: 获取当日推荐
- **WHEN** 客户端请求 `GET /api/strategy/recommendations`
- **THEN** 返回 JSON 数组，按 score 降序排列

#### Scenario: 无推荐时返回空列表
- **WHEN** 所有股票均不符合评分条件或持仓已满
- **THEN** 返回空数组 `[]`，HTTP 200

### Requirement: 获取当前持仓
系统 SHALL 提供 API `GET /api/strategy/positions` 返回当前所有持仓。

响应字段：
- `code`：股票代码
- `name`：股票名称
- `quantity`：持仓数量
- `buy_price`：实际买入价
- `target_price`：目标止盈价
- `stop_price`：止损价
- `buy_date`：买入日期
- `hold_days`：已持有天数
- `status`：持仓状态
- `unrealized_pl`：浮动盈亏（基于最新收盘价）
- `unrealized_pl_pct`：浮动盈亏百分比

#### Scenario: 获取所有持仓
- **WHEN** 客户端请求 `GET /api/strategy/positions?status=holding`
- **THEN** 返回所有 holding 状态的持仓列表，含浮动盈亏

### Requirement: 获取交易记录
系统 SHALL 提供 API `GET /api/strategy/transactions` 返回历史交易记录。

请求参数：
- `page`：页码，默认 1
- `page_size`：每页条数，默认 20
- `code`（可选）：按股票代码筛选

响应含分页信息（total, page, page_size）。

#### Scenario: 分页查询交易记录
- **WHEN** 客户端请求 `GET /api/strategy/transactions?page=1&page_size=20`
- **THEN** 返回第一页数据，包含 total 总条数

### Requirement: 获取收益统计
系统 SHALL 提供 API `GET /api/strategy/stats` 返回策略绩效统计。

响应字段：
- `total_trades`：总交易次数（已平仓）
- `win_trades`：盈利次数
- `lose_trades`：亏损次数
- `win_rate`：胜率（盈利次数/总次数）
- `avg_profit_pct`：平均盈利百分比
- `avg_loss_pct`：平均亏损百分比
- `realized_return`：已实现累计收益率
- `unrealized_return`：当前浮动盈亏率
- `total_return`：总收益率（已实现 + 浮动）
- `annualized_return`：年化收益率 = total_return / (运行天数 / 365)
- `target_annual_return`：用户设定的目标年化收益率
- `expected_annual_return`：基于当前配置的预期年化收益（数学期望）
- `available_cash`：当前可用资金
- `total_equity`：总权益（可用资金 + 持仓市值）
- `positions_count`：当前持仓只数

#### Scenario: 获取绩效统计
- **WHEN** 客户端请求 `GET /api/strategy/stats`
- **THEN** 返回包含年化收益、目标收益对比等统计数据的 JSON

#### Scenario: 实际收益低于目标时标记
- **WHEN** annualized_return < target_annual_return
- **THEN** 响应中 `on_track` 字段为 false，前端用红色警示

### Requirement: 触发策略执行
系统 SHALL 提供 API `POST /api/strategy/run` 手动触发策略执行（选股 + 持仓检测）。

执行流程 SHALL：
1. 检测所有 holding 持仓是否满足卖出条件
2. 更新持仓状态和资金
3. 计算可用仓位 = max_positions - 当前持仓数
4. 若可用仓位 > 0，运行选股引擎生成推荐
5. 返回本次执行结果摘要

#### Scenario: 手动触发策略
- **WHEN** 客户端请求 `POST /api/strategy/run`
- **THEN** 系统执行卖出检测 + 选股，返回 `{"sold_count": 1, "recommendations_count": 3, "run_date": "2025-01-06"}`

### Requirement: 前端策略看板
系统 SHALL 提供前端页面 `/strategy` 展示策略相关数据和操作，包含：
- 配置面板：可编辑所有策略参数（target_annual_return, max_positions, stop_profit_pct, stop_loss_pct, max_hold_days 等）
- **预期收益预览**：修改止盈止损比例时，实时显示预期年化收益（基于 E = win_rate × profit_pct - (1-win_rate) × loss_pct）
- **目标 vs 实际收益对比**：用进度条展示实际年化收益与目标收益的差距，绿色达标/红色未达标
- 每日推荐列表：展示股票代码、名称、评分、建议买卖价
- 当前持仓列表：展示持仓股、买入价、浮动盈亏、持有天数
- 交易记录表格：分页展示历史买卖记录
- 绩效统计卡片：年化收益率、目标收益率、胜率、累计收益、总权益、盈亏比

#### Scenario: 查看策略看板
- **WHEN** 用户访问前端 `/strategy` 路由
- **THEN** 页面展示配置面板、推荐列表、持仓列表、交易记录和绩效统计

#### Scenario: 修改配置并重新生成
- **WHEN** 用户在配置面板修改 max_positions 并点击保存
- **THEN** 配置更新成功，用户可点击"运行策略"按钮触发生成新的推荐
