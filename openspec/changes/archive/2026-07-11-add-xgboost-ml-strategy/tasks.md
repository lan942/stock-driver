## 1. 环境准备与模块骨架

- [x] 1.1 在 `requirements.txt` 中添加 `xgboost` 依赖
- [x] 1.2 创建 `backend/services/ml/` 目录及 `__init__.py` 模块入口
- [x] 1.3 创建 `data/` 目录（如不存在），作为模型文件存储路径

## 2. 特征工程模块 (`ml-feature-engine`)

- [x] 2.1 实现 `build_features(df)` 函数：输入包含 `open/high/low/close/volume` 的 DataFrame，计算 5 个特征列（ret_1d, ret_5d, volatility_10d, vol_change_1d, bias_20d）
- [x] 2.2 实现按股票代码分组的独立计算逻辑（`df.groupby('code').apply(build_features)` 模式），确保跨股票滚动窗口隔离
- [x] 2.3 支持 `extra_features` 可选参数，允许注入自定义特征函数
- [x] 2.4 处理边界情况：数据不足时返回空 DataFrame，skip NaN 行

## 3. 标签生成模块 (`ml-label-generator`)

- [x] 3.1 实现 `generate_labels(df, lookahead=5)` 函数：计算 future_ret = close.shift(-lookahead)/close - 1，生成 label = (future_ret > 0).astype(int)
- [x] 3.2 确保 `generate_labels` 在 `build_features` 之后调用，`.shift(-N)` 操作严格隔离未来信息
- [x] 3.3 边界处理：数据行数 <= lookahead 时返回空 DataFrame

## 4. XGBoost 训练器 (`xgboost-trainer`)

- [x] 4.1 实现 `train_model()` 主函数：从 StockDaily 表读取全量数据 → 按 code 分组调用 build_features → 调用 generate_labels → 合并全量特征表
- [x] 4.2 排除涨跌停日数据（change_percent >= 9.9 或 <= -9.9）
- [x] 4.3 实现时间序列切分：按行索引前 80% 训练、后 20% 测试，严禁随机打乱
- [x] 4.4 初始化 XGBClassifier（hist + cuda），自动检测 GPU 可用性，不可用时 fallback 到 CPU
- [x] 4.5 执行训练（eval_set 监控、verbose=100），完成后输出 classification_report 和特征重要性排名
- [x] 4.6 保存模型到 `data/xgboost_model.json`，保存元信息到 `data/xgboost_model_meta.json`（特征列列表、训练时间范围、lookahead）

## 5. ML 策略类 (`ml-strategy`)

- [x] 5.1 创建 `backend/services/strategies/ml_strategy.py`，实现 IStrategy 接口（`STRATEGY_NAME='xgboost'`）
- [x] 5.2 实现 `__init__()`：从 `data/xgboost_model.json` 加载模型，从 `data/xgboost_model_meta.json` 加载元信息，文件不存在时抛 FileNotFoundError
- [x] 5.3 实现 `score_stock(code)`：获取股票最近 60 日数据 → build_features → 取最新一行特征 → predict_proba 获取上涨概率作为评分
- [x] 5.4 实现 `generate_recommendations(available_slots, available_cash)`：遍历所有股票评分，按 total_score 降序排列，与现有策略推荐逻辑一致
- [x] 5.5 在 `backend/services/strategies/__init__.py` 中注册 `xgboost` 策略
- [x] 5.6 在 `backend/services/strategy_config.py` 的 DEFAULT_CONFIGS 中添加 `strategy_type: xgboost` 可选值

## 6. CLI 集成与管理命令

- [x] 6.1 在 `manage.py` 中添加 `train-xgboost` 子命令：调用 `xgboost_trainer.train_model()` 执行训练
- [x] 6.2 添加 `train-xgboost --lookahead N` 可选参数，支持自定义预测窗口（默认 5）
- [x] 6.3 训练命令输出训练进度和最终评估结果到控制台

## 7. 验证与测试

- [ ] 7.1 手动运行 `py manage.py train-xgboost` 验证全流程（需先 `pip install xgboost scikit-learn`）
- [ ] 7.2 验证模型文件 `data/xgboost_model.json` 和 `data/xgboost_model_meta.json` 生成正确
- [ ] 7.3 通过 API 调用验证 `strategy_type=xgboost` 时 `generate_recommendations` 返回合理数据
- [ ] 7.4 运行一次回测（小时间范围），对比 XGBoost 策略与现有策略的基础指标
