## Context

当前持仓接口 `get_holdings()` 返回 `quantity`（总持仓数量），但 A 股 T+1 规则下，当天买入的股票当天不可卖出。用户需要一个 `available_quantity` 字段来区分可用和不可用的持仓数量。

Transaction 模型已有 `trade_date` 字段（Date 类型），记录了每笔交易的交易日期。可以通过查询当天（今日）买入的记录来计算不可用数量。

## Goals / Non-Goals

**Goals:**
- `get_holdings()` 返回结果新增 `available_quantity` 字段
- 计算规则：`available_quantity = quantity - 当天买入数量`
- 前端持仓表格新增"可用数量"列

**Non-Goals:**
- 不修改 Transaction 数据模型
- 不修改持仓（Portfolio）数据模型
- 不影响卖出逻辑的持仓验证（保持现有逻辑不变，只是展示信息）

## Decisions

### 1. 计算方式：后端实时计算 vs 数据库冗余字段
- **选择**：后端实时计算
- **理由**：每次查询时，通过 `Transaction` 表按 `code` 和 `trade_date` 分组统计当天的买入数量即可。不需要在 Portfolio 模型中增加冗余字段，避免数据不一致问题
- **备选方案**：在 Portfolio 表中增加 `available_quantity` 字段 — 被否决，因为需要额外维护同步逻辑

### 2. 当天日期的判定
- **选择**：使用 Python `date.today()` 与 `Transaction.trade_date` 比较
- **理由**：`trade_date` 是 Date 类型，直接比较即可。前端显示的也是当天日期，保持一致
- **SQL 查询**：`SELECT code, SUM(quantity) FROM transactions WHERE type='buy' AND trade_date = :today GROUP BY code`

### 3. 前端展示
- **选择**：在"持仓数量"列之后插入"可用数量"列，使用红色高亮显示不可用数量
- **理由**：用户需要一眼看出哪些股票有不可用数量，红色提示"T+1"状态更直观

## Risks / Trade-offs

- **查询性能**：每次查询持仓都需要额外执行一次聚合查询。当前数据量较小，影响可忽略。如果未来数据量增大，可考虑在 Portfolio 模型增加缓存字段
- **日期边界**：如果在午夜附近操作，`date.today()` 可能产生预期外的结果。A 股交易时间在白天，影响不大