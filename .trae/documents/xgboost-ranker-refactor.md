# XGBoost 从二分类改造为排序学习（rank:pairwise）

## Context

当前 [xgboost_trainer.py](file:///d:/stock-driver/backend/services/ml/xgboost_trainer.py) 使用 `XGBClassifier` + `objective='binary:logistic'` 训练二分类模型，目标是让预测概率贴近 0/1 标签。但实盘策略真正关心的是 Top-K Precision（每天选概率最高的 5/10/20 只股票），并不关心绝对概率值。

这种错配带来两个问题：
1. 模型浪费容量去拟合绝对概率，而非相对排序
2. 二分类阈值（0.5）与 Top-K 选股逻辑无关，模型目标与评估目标不一致

将目标函数改为 `rank:pairwise`，按交易日作为 group 喂给模型，让模型学习"同一天内 A 股票预期表现优于 B 股票"，与 Top-K 选股逻辑完全自洽。标签仍沿用现有的截面去中心化 0/1 标签（[assign_labels](file:///d:/stock-driver/backend/services/ml/label_generator.py)），改动最小。

## 改造范围

| 文件 | 改动 |
|---|---|
| [backend/services/ml/xgboost_trainer.py](file:///d:/stock-driver/backend/services/ml/xgboost_trainer.py) | 核心改造：XGBClassifier → XGBRanker，group 参数，评估指标 |
| [manage.py](file:///d:/stock-driver/manage.py) (L363-L369) | CLI 输出指标调整 |
| [openspec/specs/xgboost-trainer/spec.md](file:///d:/stock-driver/openspec/specs/xgboost-trainer/spec.md) | 规格同步：objective、模型类、评估指标 |
| [openspec/specs/ml-strategy/spec.md](file:///d:/stock-driver/openspec/specs/ml-strategy/spec.md) (L28-L34) | 评分接口：predict_proba → predict |
| [backend/services/strategies/ml_strategy.py](file:///d:/stock-driver/backend/services/strategies/ml_strategy.py) | 存根 docstring 调整（无实现） |

## 详细设计

### 1. xgboost_trainer.py

**A. 模型初始化（L255-L264）**

```python
model = xgb.XGBRanker(
    n_estimators=500,
    max_depth=5,
    learning_rate=0.05,
    tree_method='hist',
    device=device,
    objective='rank:pairwise',
    eval_metric=['ndcg', 'auc'],  # ndcg 对齐 ranking 目标；auc 保留便于与历史 binary 模型对比
    random_state=42,
)
```

**B. Group 参数构造（在 L231 dropna 之后新增）**

XGBRanker.fit() 要求 `group` 数组（每个 group 的样本数），group = 日期。必须保证 X/y/group 顺序严格对齐：同一日期样本连续。

```python
# 训练集：按 date 排序，统计每日样本数
train_dates = full.loc[X_train.index, 'date']
order = train_dates.values.argsort(kind='stable')
X_train = X_train.iloc[order].reset_index(drop=True)
y_train = y_train.iloc[order].reset_index(drop=True)
train_dates = train_dates.iloc[order]
train_groups = train_dates.groupby(train_dates.values).size().values

# 测试集同理
test_dates = full.loc[X_test.index, 'date']
order = test_dates.values.argsort(kind='stable')
X_test = X_test.iloc[order].reset_index(drop=True)
y_test = y_test.iloc[order].reset_index(drop=True)
test_dates = test_dates.iloc[order]
test_groups = test_dates.groupby(test_dates.values).size().values
```

**C. 训练调用（L267-L272）**

```python
model.fit(
    X_train, y_train,
    group=train_groups,
    eval_set=[(X_train, y_train), (X_test, y_test)],
    eval_group=[train_groups, test_groups],
    verbose=100,
)
```

**D. 评估调整（L274-L307）**

- 移除：`model.predict()`、`accuracy_score`、`classification_report`、`precision_score`
- 改：`proba = model.predict_proba(X_test)[:, 1]` → `scores = model.predict(X_test)`
- AUC 仍计算（ranker 输出 raw score，AUC 本质是 pairwise 排序能力指标）：`auc = roc_auc_score(y_test, scores)`
- Top-K Precision：`proba` → `scores`，逻辑不变
- 新增 NDCG@K 计算函数（模块级私有函数）：

```python
def _ndcg_at_k(labels_sorted_by_score: np.ndarray, k: int) -> float:
    """单日 NDCG@K（labels 已按预测 score 降序排列，0/1 相关性）"""
    dcg_labels = labels_sorted_by_score[:k]
    dcg = (dcg_labels / np.log2(np.arange(2, len(dcg_labels) + 2))).sum()
    ideal = np.sort(labels_sorted_by_score)[::-1][:k]
    idcg = (ideal / np.log2(np.arange(2, len(ideal) + 2))).sum()
    return float(dcg / idcg) if idcg > 0 else 0.0
```

调用：按日 groupby，对每天 `sort_values('score', ascending=False)['label'].values` 后传入。

**E. 元信息与返回值（L319-L373）**

新增字段：`model_type: 'ranker'`、`objective: 'rank:pairwise'`、`ndcg_5`、`ndcg_10`、`ndcg_20`
移除字段：`train_accuracy`、`precision`
保留字段：`auc`、`top_*_precision`、`label_*`、`trained_at`、`gpu_used`、超参数

**F. 控制台输出（L301-L307）**

- 移除：`classification_report`、`Precision` 行
- 新增：`NDCG@5/10/20` 三行
- 保留：AUC、Top-K Precision、特征重要性

### 2. manage.py (L363-L369)

```python
print(blue("📊 核心评估指标:"))
print(gray(f"  AUC:              {result['auc']}"))
print(gray(f"  Top-5 Precision:  {result['top_5_precision']}"))
print(gray(f"  Top-10 Precision: {result['top_10_precision']}"))
print(gray(f"  Top-20 Precision: {result['top_20_precision']}"))
print(gray(f"  NDCG@5:           {result['ndcg_5']}"))
print(gray(f"  NDCG@10:          {result['ndcg_10']}"))
print(gray(f"  NDCG@20:          {result['ndcg_20']}"))
```

移除原 `Precision` 和 `Accuracy (参考)` 两行。

### 3. openspec/specs/xgboost-trainer/spec.md

- 默认参数 Requirement：`objective: rank:pairwise`、`eval_metric: ['ndcg', 'auc']`，模型类改为 `XGBRanker`
- GPU Scenario：`XGBClassifier` → `XGBRanker`
- 训练监控 Requirement：删除"分类报告（precision/recall/f1）"措辞，改为"排序评估报告（Top-K Precision、NDCG@K、AUC）"
- 新增 Requirement: 按日期分组训练 - 训练器 SHALL 按交易日构造 group 数组传入 XGBRanker.fit()，每个 group 对应同一交易日的所有股票样本，group 内样本两两比较学习相对排序

### 4. openspec/specs/ml-strategy/spec.md (L28-L34)

- L33：`model.predict_proba([features])[:, 1]` → `model.predict([features])`
- L34："0~1 之间的小数，越高表示上涨概率越大" → "raw score，越高表示预期相对表现越好（无概率含义，仅用于排序）"
- L40 Scenario：评分范围描述同步调整

### 5. backend/services/strategies/ml_strategy.py

存根文件仅 4 行 docstring，把 `predict_proba 获取上涨概率` 改为 `predict 获取排序分数（raw score）`。无实现代码可改。

## 风险与注意事项

1. **X/y/group 顺序严格对齐**：同一天的所有样本必须连续。L154 已 `sort_values('date')`，dropna 后通过 argsort 重新对齐并 reset_index。
2. **单日样本数过少**：NDCG@K 与 Top-K Precision 已有 `len(group) < k` 跳过逻辑，不影响。
3. **GPU 兼容性**：XGBRanker 与 XGBClassifier 同样支持 `device='cuda'`，`_detect_gpu()` 无需改动。
4. **未来预测端需用 predict 而非 predict_proba**：meta 中 `model_type='ranker'` 作为标识，ml_strategy 实现时据此选择 API。
5. **AUC 保留理由**：AUC 本质是 pairwise 排序能力指标，与 rank:pairwise 完美契合，且便于与历史 binary 模型对比改进效果（用户未勾选保留，但建议保留；如不需要可移除）。

## 验证方式

```bash
# 1. 训练新 ranker 模型（用 py -3.12 因依赖装在此环境）
py -3.12 manage.py train-xgboost

# 2. 检查控制台输出：
#    - 初始化提示 XGBRanker（不再是 XGBClassifier）
#    - 训练日志显示 ndcg + auc 两个 eval_metric
#    - 评估报告输出 AUC、Top-5/10/20 Precision、NDCG@5/10/20
#    - 不应再有 Precision、Accuracy、classification_report

# 3. 检查 data/xgboost_model_meta.json：
#    - "model_type": "ranker"
#    - "objective": "rank:pairwise"
#    - "ndcg_5" / "ndcg_10" / "ndcg_20" 字段
#    - 不应再有 "train_accuracy" / "precision"

# 4. 与上一次 binary 模型的 AUC 对比（应大致相当或更优，
#    Top-K Precision 应有提升，因为训练目标与评估目标已对齐）
```
