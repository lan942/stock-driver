## ADDED Requirements

### Requirement: 持仓数据模型
系统 SHALL 使用 `strategy_positions` 表存储策略持仓记录，字段包含：
- `id`：主键
- `code`：股票代码
- `name`：股票名称
- `quantity`：持仓数量（股）
- `buy_price`：实际买入价
- `target_price`：目标止盈价
- `stop_price`：止损价
- `suggested_buy_price`：建议买入价（用于比对）
- `buy_date`：买入日期
- `status`：状态（holding=持仓中, sold=已卖出, timeout=超时平仓, cancelled=取消）
- `sell_price`：实际卖出价（平仓后填入）
- `sell_date`：卖出日期（平仓后填入）
- `profit_pct`：盈亏百分比（平仓后计算）
- `created_at` / `updated_at`：时间戳

#### Scenario: 记录开仓
- **WHEN** 系统确认以 10.50 元买入 1000 股 "000001"
- **THEN** 在 `strategy_positions` 表中创建一条 status=holding 的记录

#### Scenario: 记录平仓
- **WHEN** 持仓 "000001" 以 10.82 元卖出（价格触及目标止盈价）
- **THEN** 更新该记录：status=sold, sell_price=10.82, sell_date=卖出日期, profit_pct=3.05%

### Requirement: 交易记录存储
系统 SHALL 使用 `strategy_transactions` 表存储每笔交易流水，字段包含：
- `id`：主键
- `type`：交易类型（buy/sell）
- `code`：股票代码
- `quantity`：数量
- `price`：价格
- `amount`：成交金额
- `trade_date`：交易日期
- `created_at`：记录时间

#### Scenario: 记录买入交易
- **WHEN** 系统执行买入操作
- **THEN** 在 `strategy_transactions` 中创建一条 type=buy 的记录

### Requirement: 卖出条件检测
持仓管理器 SHALL 在每个交易日检查所有 holding 状态持仓是否满足卖出条件：

卖出条件（按优先级）：
1. **止盈**：当日收盘价 >= 目标止盈价 → 以收盘价卖出，标记 status=sold
2. **止损**：当日收盘价 <= 止损价 → 以收盘价卖出，标记 status=sold
3. **超时**：持有天数 > `max_hold_days` → 以当日收盘价强制平仓，标记 status=timeout
4. **T+1 保护**：`buy_date` == 当日 SHALL 跳过不检测（刚买入不可卖）

#### Scenario: 触发止盈
- **WHEN** 持仓 "000001" 买入价 10.50，目标价 10.82，当日收盘价 10.90
- **THEN** 系统以 10.90 卖出，生成 sell 交易记录，更新持仓状态为 sold

#### Scenario: 触发止损
- **WHEN** 持仓 "000001" 买入价 10.50，止损价 9.98，当日收盘价 9.85
- **THEN** 系统以 9.85 卖出，生成 sell 交易记录，更新持仓状态为 sold

#### Scenario: 触发超时平仓
- **WHEN** 持仓 "000001" 已持有 5 天未触发止盈止损，配置 max_hold_days=5
- **THEN** 系统以当日收盘价强制卖出，mark 状态为 timeout

#### Scenario: T+1 锁定不卖出
- **WHEN** 持仓 "000001" 的 buy_date 为 2025-01-06，当前检测日期为 2025-01-06
- **THEN** 跳过该持仓的卖出检测

### Requirement: 资金管理
系统 SHALL 使用 `strategy_cash` 表跟踪可用资金，额外添加 `initial_capital` 字段记录初始本金，字段包含：
- `id`：主键
- `balance`：当前可用资金
- `initial_capital`：初始本金（首次初始化后不变）
- `updated_at`：更新时间

开仓时 SHALL 扣除 `buy_price × quantity` 从 balance。
平仓时 SHALL 增加 `sell_price × quantity` 到 balance。
每只股票分配资金 SHALL = `balance × position_ratio`。

#### Scenario: 买入扣款
- **WHEN** 以 10.50 元买入 1000 股 "000001"，当前 balance=100,000
- **THEN** balance 更新为 89,500（100,000 - 10,500）

#### Scenario: 卖出回款
- **WHEN** 以 10.82 卖出 1000 股 "000001"，当前 balance=89,500
- **THEN** balance 更新为 100,320（89,500 + 10,820）

#### Scenario: 资金不足跳过推荐
- **WHEN** 推荐某只股票的买入金额 = 建议买入价 × 股数 > balance
- **THEN** 跳过该推荐，尝试下一个评分较低的推荐

### Requirement: 收益计算与跟踪
系统 SHALL 提供收益统计方法，计算以下指标：
- 已实现收益率 = Σ(已平仓交易盈亏) / initial_capital
- 浮动盈亏率 = Σ(持仓股 (latest_close - buy_price) × quantity) / initial_capital
- 总收益率 = 已实现收益率 + 浮动盈亏率
- 年化收益率 = 总收益率 / (max(交易日数, 1) / 252)
- 胜率 = 盈利平仓次数 / 总平仓次数

#### Scenario: 计算年化收益
- **WHEN** 策略运行 60 个交易日后，总收益率为 3%
- **THEN** 年化收益率 ≈ 3% / (60/252) = 12.6%

#### Scenario: 对比目标收益
- **WHEN** 用户设定 target_annual_return = 0.15，实际年化收益 = 0.126
- **THEN** 系统标记 on_track = false，实际收益落后于目标
