## Context

当前项目已有完整的策略系统：`IStrategy` 接口定义 `score_stock()` 和 `generate_recommendations()`，三个规则策略（trend_following/mean_reversion/breakout）通过加权因子评分选股。`StrategyEngine` 作为统一调度器，`StrategyBacktest` 实现时间序列回测。

但现有策略全部依赖人工设定的阈值和固定因子权重，缺乏从历史数据中自动学习的能力。用户拥有 RTX 4060 Ti GPU，希望利用硬件算力训练一个 ML baseline 模型——用同样的 OHLCV 数据做二分类预测（未来 N 日涨/跌），形成可量化对比的基准。

## Goals / Non-Goals

**Goals:**
- 实现高度组件化的 ML pipeline：特征工程 → 标签生成 → 时序切分 → GPU 训练 → 评估
- 新建 `ml-strategy` 实现 `IStrategy` 接口，加载训练好的 XGBoost 模型进行选股评分
- 支持通过 CLI 命令 `manage.py train-xgboost` 触发全量模型训练
- 严格避免数据穿越：标签用 `.shift(-N)`，训练/测试按时序切分而非随机打乱
- 特征设计采用平稳化处理（对数收益率、乖离率），不直接输入绝对价格

**Non-Goals:**
- 不修改现有三个规则策略的逻辑
- 不新增前端页面（ML 策略复用现有 StrategyBoard 展示）
- 不做自动化定时训练（每次手动触发，后续可扩展）
- 不做多股票联合训练（各股票独立建模，先用全市场数据训练一个通用模型）
- 不引入深度学习框架（仅使用 XGBoost）

## Decisions

### D1: 模型选型 — XGBoost
选择 XGBoost 而非 LightGBM / CatBoost / 神经网络，理由：
- **GPU 原生支持**：`tree_method='hist'` + `device='cuda'` 直接调用 RTX 4060 Ti
- **特征重要性天然输出**：无需额外的 SHAP/LIME 分析，`feature_importances_` 直接指导因子有效性
- **对表格数据表现极佳**：树模型天然处理不同量纲特征，无需标准化
- **训练速度快**：500 棵树、5 层深度，在全市场数年日线数据上通常 < 1 分钟
- 备选：LightGBM 对 GPU 支持不如 XGBoost 成熟；神经网络需要归一化且对表格数据未必更优

### D2: 组件化架构 — 四个独立模块
```
backend/services/ml/          # 新建 ML 模块包
├── __init__.py
├── feature_engine.py         # 特征工程：OHLCV → 特征 DataFrame
├── label_generator.py        # 标签生成：未来 N 日涨跌 → 0/1
├── xgboost_trainer.py        # 模型训练：特征+标签 → 模型文件 + 评估报告
backend/services/strategies/
└── ml_strategy.py            # 策略实现：加载模型 → IStrategy 接口
```

每个模块职责单一，可独立调试和验证。`xgboost_trainer` 依赖 `feature_engine` 和 `label_generator` 的输出，`ml_strategy` 依赖训练好的模型文件。

### D3: 模型持久化 — XGBoost 原生 JSON 格式
使用 `model.save_model(f'data/xgboost_model.json')` 保存，`xgb.XGBClassifier()` 后 `load_model()` 加载。
- 不需要 pickle/joblib（受限于 XGBoost 内部 C++ 实现的序列化机制）
- JSON 格式可读性好，方便后续大模型 API 阅读模型结构
- 存储路径：`data/xgboost_model.json`

### D4: 策略评分方式 — predict_proba 作为评分
`ml_strategy.score_stock()` 调用 `model.predict_proba(features)[:, 1]`（上涨概率）作为 0~1 的评分，天然对齐现有 IStrategy 的 `total_score` 语义。现有策略引擎和回测引擎无需任何修改即可兼容。

### D5: 训练数据范围 — 全市场所有股票合并
将数据库中所有股票的 StockDaily 数据合并为一张大表训练，学习的是"在所有股票上通用的涨跌规律"而非单只股票的独立模式。好处：数据量大、泛化能力强；代价：无法捕捉个股特异性。

## Risks / Trade-offs

- **[数据穿越风险]** 特征和标签的时序对齐极易出错 → **缓解**：`feature_engine` 用 `shift()` 严格使用历史数据；`label_generator` 用 `shift(-lookahead)`；单元测试验证"训练集最晚日期 < 测试集最早日期"
- **[GPU 可用性]** 用户机器若无 CUDA 环境会导致 `device='cuda'` 失败 → **缓解**：训练器启动时检测 GPU，自动 fallback 到 `device='cpu'`
- **[模型过拟合]** 特征维度低（5 个），股票数量大，过拟合风险可控；但若训练集/测试集时间范围相近可能高估表现 → **缓解**：回测时严格按时间序列切分，评估报告包含测试集 accuracy 和 AUC
- **[概念漂移]** 市场规律随时间变化，训练好的模型会失效 → **缓解**：标注训练数据的时间范围，建议定期重新训练
- **[现有回测引擎兼容]** `strategy_backtest._score_stock_for_date()` 用 hasattr 动态调用因子方法，ML 策略无需暴露因子方法 → **缓解**：直接在 `ml_strategy` 中实现独立的 `score_stock()`，回测引擎通过 `_get_stock_data_before_date` 获取数据后传给 `self.strategy.score_stock(code)`（当前即如此），无需 hasattr 链

## Open Questions

- 是否需要支持按行业/市值分组训练多个子模型？（初版不做，后续迭代）
- 模型文件是否需要版本管理？（初版单文件覆盖，后续可考虑加时间戳命名）
- 训练频率建议？（建议用户每周或每月手动执行一次，后续可加入 scheduler）
