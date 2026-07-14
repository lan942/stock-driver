# ml-strategy Specification

## Purpose
XGBoost ML 策略：使用 XGBoost Ranker（rank:pairwise）对全市场股票进行排序学习，每日收盘后评分选股，T+1 开盘买入，持仓期间通过日内止损 + 收盘后评估机制管理卖出。

## Requirements
### Requirement: 实现 IStrategy 接口
ML 策略类 `XGBoostStrategy` SHALL 实现 `IStrategy` 接口，提供 `score_stock()` 和 `generate_recommendations()` 方法。

`STRATEGY_NAME` SHALL 为 `"xgboost"`，`STRATEGY_DESCRIPTION` SHALL 为 `"XGBoost ML策略：基于GPU训练的机器学习模型选股"`。

#### Scenario: 策略注册
- **WHEN** `get_strategy('xgboost')` 被调用
- **THEN** 返回 `XGBoostStrategy` 实例

### Requirement: 模型加载
策略初始化时 SHALL 从 `data/xgboost_model.json` 加载预训练模型，并从 `data/xgboost_model_meta.json` 加载元信息（特征列列表等）。若模型文件不存在，SHALL 抛出明确异常 `FileNotFoundError`。

策略 SHALL 缓存加载的模型和特征列列表，避免每次评分重复加载。

#### Scenario: 模型文件存在时正常加载
- **WHEN** `data/xgboost_model.json` 和 `data/xgboost_model_meta.json` 存在且有效
- **THEN** 策略实例成功初始化，模型和元信息加载到内存

#### Scenario: 模型文件不存在时抛出异常
- **WHEN** `data/xgboost_model.json` 不存在
- **THEN** 抛出 `FileNotFoundError` 并提示用户先运行 `manage.py train-xgboost`

### Requirement: 基于模型排序分数评分
`score_stock(code)` SHALL 执行以下步骤：
1. 从数据库获取该股票最近 60 个交易日的 OHLCV 数据
2. 调用 `feature_engine.build_features()` 计算特征
3. 取最后一行（最新日期）的特征值
4. 调用 `model.predict([features])` 获取 raw score 作为评分（ranker 输出，非概率）
5. 评分为浮点数，越高表示预期相对表现越好（无概率含义，仅用于排序选股）

返回格式 SHALL 与现有策略一致：包含 `code`, `total_score`, `factor_scores`, `latest_close`, `latest_volume`, `latest_change_pct`。

策略初始化时 SHALL 检查 `data/xgboost_model_meta.json` 的 `model_type` 字段，若为 `'ranker'` 则使用 `predict`，若为 `'binary'` 则使用 `predict_proba`（向后兼容旧模型）。

#### Scenario: 正常评分
- **WHEN** 对一只数据充足的股票调用 `score_stock('000001')`
- **THEN** 返回包含 `total_score`（浮点 raw score）的评分字典

#### Scenario: 数据不足时返回 None
- **WHEN** 股票交易数据不足 60 个交易日
- **THEN** 返回 `None`

### Requirement: 买入规则（T日评分，T+1 开盘买入）
回测引擎 SHALL 在每个交易日收盘后执行全市场评分，按评分降序选出得分 >= 自适应门槛的股票，次日以开盘价买入。不设涨跌幅限制——无论 T+1 开盘相比 T 日收盘高开多少，均以 T+1 开盘价成交。

#### Scenario: T+1 开盘买入
- **WHEN** T 日收盘评分选出股票 A
- **THEN** T+1 日以开盘价买入 A，不限涨跌幅

### Requirement: 卖出规则（日内止损 + 收盘后评估）
卖出执行 SHALL 分为两类：

**日内止损**（唯一日内操作）：
- 挂单 min(ATR 止损, 百分比止损)，当日 low 触及即成交
- `_check_intraday_stop_loss` 方法实现

**收盘后评估**（止盈/超时/动态评分）：
- 收盘后评估，触发后加入 `pending_sells` 队列
- 次交易日以开盘价卖出
- `_check_close_triggers` 方法实现

#### Scenario: 日内止损卖出
- **WHEN** 持仓股票当日 low 触及止损线
- **THEN** 当日以止损价卖出，原因类型为 `stop_loss` 或 `atr_loss`

#### Scenario: 收盘后止盈评估
- **WHEN** 持仓股票收盘价 >= 止盈线
- **THEN** 次交易日以开盘价卖出，原因类型为 `take_profit` 或 `atr_profit`

#### Scenario: 超时卖出
- **WHEN** 持仓交易日数达到 max_hold_days
- **THEN** 次交易日以开盘价卖出，原因类型为 `timeout`

#### Scenario: 动态评分卖出
- **WHEN** 收盘后评分恶化（百分位/连续下降/绝对阈值）
- **THEN** 次交易日以开盘价卖出，原因类型为 `dynamic_score_low` 或 `dynamic_score_decline`

### Requirement: 实盘可操作设计
本策略的买卖规则设计为实盘可操作：
- 买入：T 日收盘后模型评分，T+1 日集合竞价挂单买入——不需要盯盘
- 日内操作：只挂一笔止损条件单——券商支持
- 其余卖出：收盘后评估，次日集合竞价挂单——不需要盯盘
