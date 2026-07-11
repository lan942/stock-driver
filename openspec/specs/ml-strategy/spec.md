# ml-strategy Specification

## Purpose
TBD - created by archiving change add-xgboost-ml-strategy. Update Purpose after archive.
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

### Requirement: 基于模型预测概率评分
`score_stock(code)` SHALL 执行以下步骤：
1. 从数据库获取该股票最近 60 个交易日的 OHLCV 数据
2. 调用 `feature_engine.build_features()` 计算特征
3. 取最后一行（最新日期）的特征值
4. 调用 `model.predict_proba([features])[:, 1]` 获取上涨概率作为评分
5. 评分为 0~1 之间的小数，越高表示上涨概率越大

返回格式 SHALL 与现有策略一致：包含 `code`, `total_score`, `factor_scores`, `latest_close`, `latest_volume`, `latest_change_pct`。

#### Scenario: 正常评分
- **WHEN** 对一只数据充足的股票调用 `score_stock('000001')`
- **THEN** 返回包含 0~1 之间 `total_score` 的评分字典

#### Scenario: 数据不足时返回 None
- **WHEN** 股票交易数据不足 60 个交易日
- **THEN** 返回 `None`

### Requirement: 生成买入推荐
`generate_recommendations(available_slots, available_cash)` SHALL 遍历所有股票，调用 `score_stock()` 评分后按 `total_score` 降序排列，生成买入推荐清单。推荐逻辑 SHALL 与现有策略一致（仓位计算、止盈止损、资金检查）。

#### Scenario: 正常生成推荐
- **WHEN** `available_slots=3`, `available_cash=100000`
- **THEN** 返回最多 3 条推荐，按评分降序，包含 `suggested_buy_price`, `target_price`, `stop_price`

