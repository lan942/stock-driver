## Context

回测引擎（`strategy_backtest.py`）在执行卖出时已经计算了 `profit_pct`（收益率），但该值仅存入临时的 `sell_log` 数组用于回测摘要展示，未持久化到 `BacktestTransaction` 表中。用户在回测管理页面的交易记录中无法看到每次卖出的盈亏情况。

此前 `backtest-transaction-enhancement` 已为交易记录添加了开盘价、收盘价、交易后权益等字段，本次变更是同一方向的延续。

## Goals / Non-Goals

**Goals:**
- `BacktestTransaction` 模型新增 `profit_pct` 字段（Float, nullable）
- 回测引擎在记录卖出交易时，将已计算的 `profit_pct` 传入 `add_transaction()`
- `add_transaction()` 接受并存储 `profit_pct`，仅卖出入库
- `get_transactions()` 和 `get_transactions_by_code()` 返回 `profit_pct`
- 前端 `Backtest.vue` 交易表格新增「收益率」列，仅卖出行显示

**Non-Goals:**
- 不修改回测摘要/StrategyBoard 的现有展示逻辑
- 不计算买入交易的收益率
- 不自动为历史数据回填收益率（历史卖出记录的 profit_pct 保持 NULL）

## Decisions

1. **字段类型：`Float, nullable`**
   - 原因：仅卖出有收益率，买入的 `profit_pct` 为 NULL，前端据此判断是否显示
   - 备选：`Float, default=0` — 但 0 会混淆「零收益」和「不适用」，NULL 语义更清晰

2. **`add_transaction()` 新增可选参数 `profit_pct: Optional[float] = None`**
   - 原因：保持向后兼容，手动添加交易（前端表单）不传该参数，只有回测引擎传入
   - 备选：新增独立更新方法 — 增加复杂度，不必要

3. **`strategy_backtest.py` 三处卖出点的改造策略**
   - 主循环卖出（line ~485）：在 `add_transaction()` 调用时直接传入 `profit_pct`
   - 清仓阶段卖出（line ~573）：同上
   - 强制清仓（line ~632）：同上
   - 原因：三处都已计算 `profit_pct`（`sell_log` 中），改造成本最低

4. **前端「收益率」列仅对卖出显示**
   - 绿色正收益、红色负收益，与持仓表格风格一致
   - 买单行显示 `-`

## Risks / Trade-offs

- **已有卖出记录无收益率**：历史数据的 `profit_pct` 为 NULL，前端显示为 `-`，不影响使用
- **手动添加卖出记录不支持收益率**：前端交易表单不提供收益率输入，手动添加的卖出的 `profit_pct` 为 NULL
- **数据库迁移**：新增 nullable 列，SQLite 支持 `ALTER TABLE ADD COLUMN`，无需复杂迁移
