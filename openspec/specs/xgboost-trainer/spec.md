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
- `objective`: `binary:logistic`
- `eval_metric`: `auc`
- `random_state`: 42

#### Scenario: GPU 可用时使用 CUDA 训练
- **WHEN** 训练器启动且检测到 CUDA 设备
- **THEN** XGBClassifier 以 `device='cuda'` 初始化并开始训练，控制台输出 "🚀 启用 GPU 加速"

#### Scenario: GPU 不可用时降级到 CPU
- **WHEN** 训练器启动且未检测到 CUDA 设备
- **THEN** XGBClassifier 以 `device='cpu'` 初始化，控制台输出警告信息，训练正常进行

### Requirement: 时间序列数据集划分
训练器 SHALL 按时间序列顺序将数据切分为训练集（前 80%）和测试集（后 20%），严禁使用随机打乱。切分点 SHALL 基于 DataFrame 的行索引位置。

#### Scenario: 按时序切分
- **WHEN** 输入包含 1000 行按日期升序排列的数据
- **THEN** 训练集包含前 800 行，测试集包含后 200 行

### Requirement: 训练过程监控
训练器 SHALL 在训练时传入 `eval_set` 参数监控训练集和测试集的 AUC，每隔 100 轮 (`verbose=100`) 打印一次日志。训练完成后 SHALL 打印分类报告（precision, recall, f1-score）和特征重要性排名。

#### Scenario: 训练日志输出
- **WHEN** 训练器以 `verbose=100` 执行 500 轮训练
- **THEN** 控制台在每 100 轮输出一次 train/validation 的 AUC 值

### Requirement: 模型持久化
训练完成后，模型 SHALL 保存为 JSON 格式文件到 `data/xgboost_model.json`。SHALL 同时保存训练元信息（特征列列表、训练时间范围、lookahead 值）到同路径的 `data/xgboost_model_meta.json`。

#### Scenario: 保存模型
- **WHEN** 训练器完成训练和评估
- **THEN** 在 `data/xgboost_model.json` 和 `data/xgboost_model_meta.json` 生成对应文件

### Requirement: 全量数据处理
训练器 SHALL 从数据库中读取所有股票的 StockDaily 数据，合并后进行特征工程和标签生成。排除涨跌停日期（change_percent >= 9.9 或 <= -9.9）的数据行。

#### Scenario: 从数据库加载全量数据
- **WHEN** 调用训练器的主训练方法
- **THEN** 从 `stock_daily` 表读取所有数据，按 code 分组后调用 `build_features` 和 `generate_labels`，合并后训练

