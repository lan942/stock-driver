# xgboost-trainer Specification

## Purpose
TBD - created by archiving change add-xgboost-ml-strategy. Update Purpose after archive.
## Requirements
### Requirement: GPU 加速模型训练
训练器 SHALL 使用 XGBoost 的 `hist` 树方法配合 `device='cuda'` 进行 GPU 加速训练。若 CUDA 不可用，SHALL 自动 fallback 到 `device='cpu'` 并打印警告。

训练参数默认值 SHALL 为：
- `n_estimators`: 500
- `max_depth`: 5
- `learning_rate`: 0.05
- `objective`: `rank:pairwise`（排序学习，与 Top-K 选股逻辑自洽）
- `eval_metric`: `['ndcg', 'auc']`
- `random_state`: 42

模型类 SHALL 为 `XGBRanker`（不是 `XGBClassifier`），因为实盘只关心每日股票相对排序，不关心绝对概率。

#### Scenario: GPU 可用时使用 CUDA 训练
- **WHEN** 训练器启动且检测到 CUDA 设备
- **THEN** XGBRanker 以 `device='cuda'` 初始化并开始训练，控制台输出 "🚀 初始化 XGBRanker（启用 GPU 加速，objective=rank:pairwise）..."

#### Scenario: GPU 不可用时降级到 CPU
- **WHEN** 训练器启动且未检测到 CUDA 设备
- **THEN** XGBRanker 以 `device='cpu'` 初始化，控制台输出警告信息，训练正常进行

### Requirement: 按交易日分组训练（Group）
训练器 SHALL 按交易日构造 `group` 数组传入 `XGBRanker.fit()`，每个 group 对应同一交易日的所有股票样本。group 内样本两两比较学习相对排序，group 之间不交叉比较。

构造 group 前 SHALL 确保训练集 / 测试集的 X、y、date 三者按日期升序对齐（同一日期样本连续），通过 stable argsort + reset_index 实现。

#### Scenario: group 数组正确构造
- **WHEN** 训练集包含 N 个交易日的样本
- **THEN** `train_groups` 数组长度为 N，每个元素等于该交易日样本数，且 `sum(train_groups) == len(X_train)`

### Requirement: 时间序列数据集划分
训练器 SHALL 按时间序列顺序将数据切分为训练集（前 80%）和测试集（后 20%），严禁使用随机打乱。切分点 SHALL 基于 DataFrame 的行索引位置。

#### Scenario: 按时序切分
- **WHEN** 输入包含 1000 行按日期升序排列的数据
- **THEN** 训练集包含前 800 行，测试集包含后 200 行

### Requirement: 训练过程监控
训练器 SHALL 在训练时传入 `eval_set` 和 `eval_group` 参数监控训练集和测试集的 NDCG 与 AUC，每隔 100 轮 (`verbose=100`) 打印一次日志。训练完成后 SHALL 打印排序评估报告（AUC、Top-K Precision、NDCG@K）和特征重要性排名。

#### Scenario: 训练日志输出
- **WHEN** 训练器以 `verbose=100` 执行 500 轮训练
- **THEN** 控制台在每 100 轮输出一次 train/validation 的 ndcg 与 auc 值

### Requirement: 模型持久化
训练完成后，模型 SHALL 保存为 JSON 格式文件到 `data/xgboost_model.json`。SHALL 同时保存训练元信息到同路径的 `data/xgboost_model_meta.json`，元信息 SHALL 至少包含以下字段：
- `model_type`: `'ranker'`（用于预测端选择 `predict` 而非 `predict_proba`）
- `objective`: `'rank:pairwise'`
- `feature_cols`: 特征列列表
- `lookahead`: 预测窗口
- `train_date_range` / `test_date_range`: 训练/测试日期范围
- `train_samples` / `test_samples` / `train_groups` / `test_groups`: 样本与 group 数量
- `auc` / `top_5_precision` / `top_10_precision` / `top_20_precision` / `ndcg_5` / `ndcg_10` / `ndcg_20`: 评估指标
- `label_positive_ratio` / `label_method`: 标签分布与方法
- `trained_at` / `gpu_used`: 训练时间与 GPU 使用情况
- `n_estimators` / `max_depth` / `learning_rate`: 模型超参数

#### Scenario: 保存模型
- **WHEN** 训练器完成训练和评估
- **THEN** 在 `data/xgboost_model.json` 和 `data/xgboost_model_meta.json` 生成对应文件，且 meta 中 `model_type == 'ranker'`

### Requirement: 全量数据处理
训练器 SHALL 从数据库中读取所有股票的 StockDaily 数据，合并后进行特征工程和标签生成。排除涨跌停日期（按板块差异化阈值：主板 9.9%、创业板/科创板 19.9%、北交所 29.9%）的数据行。

#### Scenario: 从数据库加载全量数据
- **WHEN** 调用训练器的主训练方法
- **THEN** 从 `stock_daily` 表读取所有数据，按 code 分组后调用 `build_features` 和 `compute_future_returns` + `assign_labels`，合并后训练

