# 回测交易记录增强 - 设计文档

## 数据模型变更

### BacktestTransaction 模型扩展
在 `backtest_transactions` 表中新增字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| open_price | Float | 交易当日开盘价 |
| close_price | Float | 交易当日收盘价 |
| equity_after | Float | 交易完成后的总权益（现金+持仓市值） |

## 服务层变更

### backtest_service.add_transaction
新增参数：
- open_price: Optional[float]
- close_price: Optional[float]
- equity_after: Optional[float]

返回值中新增对应字段。

### backtest_service.get_transactions
排序方式从 `created_at desc` 改为 `trade_date asc, id asc`，按交易时间正序排列。

### strategy_backtest._calc_equity
新增静态方法，计算当前总权益：
```
equity = cash_balance + sum(holding_quantity * close_price)
```

### strategy_backtest._execute_pending_buys
修改买入数量计算逻辑：
```
alloc = available_cash * position_ratio
quantity = floor(alloc / buy_price) // 100 * 100
if quantity < 100: skip
if quantity * buy_price > available_cash: quantity -= 100
```

每笔买入后记录 open_price、close_price、equity_after。

### strategy_backtest.run (卖出逻辑)
每笔卖出后记录 open_price、close_price、equity_after。

### strategy_backtest._get_stock_data_before_date
默认参数从 `days=60` 改为 `days=30`。

### strategy_engine._get_stock_daily_data
默认参数从 `days=60` 改为 `days=30`。

## 前端变更

### Backtest.vue
交易记录表格新增三列：
- 开盘价
- 收盘价
- 交易后权益

## 数据库迁移

SQLite ALTER TABLE 语句：
```sql
ALTER TABLE backtest_transactions ADD COLUMN open_price FLOAT;
ALTER TABLE backtest_transactions ADD COLUMN close_price FLOAT;
ALTER TABLE backtest_transactions ADD COLUMN equity_after FLOAT;
```
