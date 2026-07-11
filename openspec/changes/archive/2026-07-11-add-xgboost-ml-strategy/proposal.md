## Why

当前项目中的三个策略（trend_following / mean_reversion / breakout）均为规则驱动型策略，依赖人工设定的阈值和因子权重，缺乏数据驱动的统计学习能力。这种手工调参的方式存在两个核心问题：(1) 因子权重无法从历史数据中自动优化；(2) 规则型策略难以捕捉非线性、多维度的价格特征交互。引入基于 XGBoost 的机器学习基线模型，可以利用 GPU（RTX 4060 Ti）算力，在同样的 OHLCV 数据上自动学习特征组合，形成可量化对比的 ML baseline。

## What Changes

- **新增** `ml-feature-engine` 模块：实现特征工程流水线，将原始 OHLCV 数据转化为平稳的量化特征（对数收益率、波动率、量价偏离度等）
- **新增** `ml-label-generator` 模块：基于未来 N 日涨跌生成二分类标签，严格使用时间序列 shift 防止数据穿越
- **新增** `xgboost-trainer` 模块：GPU 加速的 XGBoost 模型训练器，支持时间序列切分、训练验证集监控、特征重要性输出
- **新增** `ml-strategy` 策略类：实现 IStrategy 接口，加载训练好的模型进行股票评分和推荐生成
- **新增** 模型持久化能力：训练完成后保存模型文件，策略加载时复用已训练模型
- **扩展** CLI 管理命令：`manage.py train-xgboost` 支持从命令行触发模型训练
- **扩展** `requirements.txt`：新增 `xgboost` 依赖

## Capabilities

### New Capabilities
- `ml-feature-engine`: 从 StockDaily 数据中计算平稳化量化特征（对数收益率、波动率、成交量变化率、均线偏离度），输出特征 DataFrame
- `ml-label-generator`: 基于未来 N 日涨幅生成二分类标签（涨=1/跌=0），通过 shift 操作严格避免未来函数泄露
- `xgboost-trainer`: GPU 加速 XGBoost 模型训练，按时间序列顺序切分训练/测试集，输出分类报告和特征重要性排名
- `ml-strategy`: 实现 IStrategy 接口的机器学习策略，加载预训练 XGBoost 模型进行股票评分，生成买入推荐

### Modified Capabilities
<!-- No existing specs require modification. The ML strategy is purely additive and implements the existing IStrategy interface. -->

## Impact

- **新增依赖**: `xgboost`（支持 CUDA 的 GPU 版本）
- **新增文件**:
  - `backend/services/ml/` — 机器学习模块包
    - `feature_engine.py` — 特征工程
    - `label_generator.py` — 标签生成
    - `xgboost_trainer.py` — 模型训练
  - `backend/services/strategies/ml_strategy.py` — ML 策略类
- **修改文件**:
  - `backend/services/strategies/__init__.py` — 注册 `xgboost` 策略
  - `backend/services/strategy_config.py` — 新增 `strategy_type: xgboost` 默认选项
  - `requirements.txt` — 新增 `xgboost` 依赖
  - `manage.py` — 新增 `train-xgboost` 命令
- **兼容性**: 纯增量变更，不影响现有三个策略的运行和回测
