# 期望年化收益率动态调整策略

## Context

当前策略配置中的 `target_annual_return`（期望年化收益率15%）只是一个展示值，没有参与策略决策。用户希望让它真正生效——根据收益进度动态调整选股门槛和仓位，核心诉求是"稳定赚钱"：收益落后时精选+减仓控制风险，达标后恢复正常交易。

## 分档设计

**进度定义**：`progress = 当前CAGR年化收益率 / target_annual_return`

| 档位 | 触发条件 | 选股门槛 | 仓位比例 | 策略 |
|------|---------|---------|---------|------|
| 严重落后 | progress < 0.5 | 0.65 | 10% | 精选+减仓，宁可少做 |
| 接近目标 | 0.5 ≤ progress < 1.0 | 0.50 | 15% | 适度放宽 |
| 已达标 | progress ≥ 1.0 | 0.35 | 20% | 正常仓位，仅过滤极弱 |

**预热期**：前20个交易日不调整（CAGR噪声太大），使用达标档参数。

**年化公式**：CAGR = `(1 + 总收益率)^(252/已运行交易日) - 1`

## 改动文件

### 1. backend/services/strategy_config.py — 新增7个配置项

在 `DEFAULT_CONFIGS` 中新增：
- `adaptive_score_threshold_behind` = 0.65
- `adaptive_score_threshold_near` = 0.50
- `adaptive_score_threshold_met` = 0.35
- `adaptive_position_ratio_behind` = 0.10
- `adaptive_position_ratio_near` = 0.15
- `adaptive_position_ratio_met` = 0.20
- `adaptive_min_days` = 20

在 `get()` 的类型转换中加入对应 float/int 转换。

### 2. backend/services/strategy_backtest.py — 核心改动

**`__init__`**：读取上述配置，初始化 `self._adaptive_score_threshold` 和 `self._adaptive_position_ratio`（默认=达标档）。

**新增 `_compute_progress()`**：
- 从 `self.daily_records` 取最新权益
- 计算 CAGR 年化收益率
- 返回 `(progress, annualized, days)`

**新增 `_update_adaptive_params()`**：
- 调 `_compute_progress()`
- 预热期（days < 20）强制用达标档
- 否则按 progress 三档选择门槛/仓位
- 写入 `self._adaptive_score_threshold` 和 `self._adaptive_position_ratio`

**修改 `run()` 主循环**：
- 每个交易日开始时调 `_update_adaptive_params()`
- `daily_records` 新增字段：`tier`、`progress`、`annualized`（纯追加，不破坏现有字段）

**修改 `_generate_recommendations()`**：
- 评分排序后，用 `self._adaptive_score_threshold` 过滤低分股票（降序，遇到低于门槛的 break）
- 仓位用 `self._adaptive_position_ratio` 替代 `self.position_ratio`
- rec 字典新增 `position_ratio` 字段，供次日执行时复用（保证T日生成/T+1执行一致性）

**修改 `_execute_pending_buys()`**：
- 仓位用 `rec.get('position_ratio', self.position_ratio)`（用生成日的比例）

**修改 `_build_summary()`**：
- 年化改为 CAGR 公式（与动态调整口径一致）
- 新增 `max_drawdown`（遍历权益曲线求最大回撤）
- 新增 `target_annual_return`、`final_progress`、`final_tier`

### 3. backend/services/strategies/breakout_strategy.py — 可选

实盘 `generate_recommendations()` 加静态门槛（0.35），过滤极弱推荐。实盘无 daily_records，不做动态调整。

## 验证方法

1. **回测对比**：用相同参数（6月1日-30日，breakout策略）分别跑改前/改后，对比：
   - 年化收益率（应不低于13%）
   - 最大回撤（应明显下降——稳定赚钱的核心指标）
   - 胜率（门槛提高后应上升）
   - 交易次数（应减少，弱信号被过滤）
2. **档位检查**：查看 `daily_records` 的 `tier` 字段，确认切换合理不抖动
3. **回归保证**：把新配置默认值设为等价现状（门槛=0、三档仓位都=0.20、预热期=999天），结果应与改动前完全一致
