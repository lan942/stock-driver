## ADDED Requirements

### Requirement: 策略配置模型
系统 SHALL 使用 `strategy_config` 表存储策略配置参数，字段包含：
- `id`：主键
- `key`：配置键名
- `value`：配置值（JSON 字符串）
- `description`：配置说明
- `updated_at`：更新时间

支持的配置键 SHALL 包含：
- `target_annual_return`：期望年化收益率（默认 0.15，即 15%）
- `initial_capital`：初始资金（默认 100000）
- `max_positions`：最大持仓只数（默认 5）
- `position_ratio`：单只仓位占比（默认 0.2）
- `stop_profit_pct`：止盈比例（默认 0.06，即 +6%，基于 2:1 盈亏比）
- `stop_loss_pct`：止损比例（默认 0.03，即 -3%）
- `max_hold_days`：最大持有天数（默认 5）
- `factor_weights`：因子权重 JSON（默认 {"trend":0.30,"momentum":0.25,"volume":0.20,"reversal":0.15,"volatility":0.10}）

系统 SHALL 在配置变更时自动计算并展示预期年化收益：
- 预期每笔收益 E = win_rate_estimate × stop_profit_pct - (1-win_rate_estimate) × stop_loss_pct
- 默认估计胜率 win_rate_estimate = 0.45

#### Scenario: 读取单个配置
- **WHEN** 用户查询 `max_positions` 配置
- **THEN** 返回当前值和默认值

#### Scenario: 更新配置
- **WHEN** 用户修改 `stop_loss_pct` 为 0.07
- **THEN** 数据库中的值 SHALL 更新，下次策略执行时生效

### Requirement: 配置初始化
系统首次启动时 SHALL 自动创建默认配置记录。若已有配置则跳过。

#### Scenario: 首次初始化
- **WHEN** `strategy_config` 表为空且系统调用配置读取
- **THEN** 系统自动插入所有默认配置项

### Requirement: 配置接口
系统 SHALL 通过 API 提供全局配置的读取和更新：
- `GET /api/strategy/config`：返回所有配置项
- `PUT /api/strategy/config`：批量更新配置项

#### Scenario: 获取全部配置
- **WHEN** 前端请求策略配置
- **THEN** 返回所有配置键值对的 JSON 对象

#### Scenario: 批量更新配置
- **WHEN** 前端提交 `{"max_positions": 3, "stop_profit_pct": 0.05}`
- **THEN** 系统更新两项配置并返回成功
