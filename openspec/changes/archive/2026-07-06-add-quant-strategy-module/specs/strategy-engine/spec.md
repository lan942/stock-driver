## ADDED Requirements

### Requirement: 多因子评分选股
策略引擎 SHALL 基于多个因子对所有股票进行综合评分，并输出 TOP N 推荐买入标的。每个因子 SHALL 独立计算 0~1 的归一化分数，加权求和得到总分。

因子列表 SHALL 包含：
- 趋势因子（均线乖离率）：基于 5 日和 20 日简单移动平均的乖离率
- 动量因子（RSI）：基于 14 日 RSI 值
- 成交量因子：当日成交量与 20 日均量的比值
- 反转因子：近 3 日累计涨跌幅
- 波动率因子（ATR）：基于 14 日 ATR 标准化

各因子权重 SHALL 从配置中读取，默认值为：趋势 0.30、动量 0.25、成交量 0.20、反转 0.15、波动率 0.10。

#### Scenario: 正常计算股票评分
- **WHEN** 系统对某只股票（代码 "000001"）进行评分，该股票有 120 个交易日的完整数据
- **THEN** 系统计算所有 5 个因子的得分并返回加权总分

#### Scenario: 数据不足时跳过评分
- **WHEN** 某只股票的交易数据少于 60 个交易日
- **THEN** 该股票 SHALL 被排除在评分候选之外

#### Scenario: 排除涨跌停股票
- **WHEN** 某只股票最近交易日涨幅 >= 9.9% 或跌幅 <= -9.9%
- **THEN** 该股票 SHALL 被排除在推荐候选之外

### Requirement: 每日推荐生成
策略引擎 SHALL 在每日收盘后生成 T+1 日的买入推荐清单。每条推荐 SHALL 包含：股票代码、股票名称、建议买入价、目标止盈价、止损价。

建议买入价 SHALL = 当前收盘价 × 1.01（允许 1% 溢价追入）。
目标止盈价 SHALL = 建议买入价 × (1 + stop_profit_pct)，其中 stop_profit_pct 从配置读取。
止损价 SHALL = 建议买入价 × (1 - stop_loss_pct)，其中 stop_loss_pct 从配置读取。

#### Scenario: 生成买入推荐
- **WHEN** 系统运行每日推荐，候选池有 50 只符合评分条件的股票
- **THEN** 系统返回按评分降序排列的 TOP N 推荐，N = 配置的最大持仓只数减去当前已持仓只数

#### Scenario: 持仓已满时不推荐
- **WHEN** 当前持仓只数已达到配置的最大持仓只数
- **THEN** 推荐列表 SHALL 为空

### Requirement: 策略配置管理
系统 SHALL 提供策略参数配置功能，支持以下参数：
- `initial_capital`：初始资金（元），默认 100,000
- `max_positions`：最大同时持仓只数，默认 5
- `position_ratio`：单只仓位占比，默认 0.2（即每只占可用资金的 20%）
- `stop_profit_pct`：止盈比例，默认 0.03（+3%）
- `stop_loss_pct`：止损比例，默认 0.05（-5%）
- `max_hold_days`：最大持有天数，默认 5
- `factor_weights`：各因子权重 JSON

配置 SHALL 可读可写，修改后即时生效。

#### Scenario: 读取默认配置
- **WHEN** 系统首次启动且无已保存配置
- **THEN** 返回默认配置值

#### Scenario: 更新配置并生效
- **WHEN** 用户通过 API 修改 `stop_profit_pct` 为 0.05
- **THEN** 下次生成推荐时 SHALL 使用新的止盈比例

### Requirement: 技术指标集成
策略引擎 SHALL 复用 `indicator_engine.py` 的 `IndicatorEngine.compute()` 方法获取所需技术指标值。每次请求应使用缓存机制避免重复计算。

#### Scenario: 获取指标值
- **WHEN** 策略引擎需要某股票的 MA5、MA20、RSI14、ATR14 指标
- **THEN** 调用 `IndicatorEngine.compute(code, configs)` 获取指标数组并取最新值
