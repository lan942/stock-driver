# 回测交易记录增强 - 任务列表

## 已完成任务

### 1. 修改数据模型
- **文件**: backend/models/backtest.py
- **变更**: BacktestTransaction 模型新增 open_price、close_price、equity_after 字段

### 2. 数据库迁移
- **操作**: SQLite ALTER TABLE 添加三列

### 3. 修改交易服务
- **文件**: backend/services/backtest_service.py
- **变更**: 
  - add_transaction 新增 open_price、close_price、equity_after 参数
  - get_transactions 排序改为 trade_date asc, id asc
  - 返回值新增 open_price、close_price、equity_after 字段

### 4. 修改回测引擎 - 权益计算
- **文件**: backend/services/strategy_backtest.py
- **变更**: 新增 _calc_equity() 静态方法

### 5. 修改回测引擎 - 买入逻辑
- **文件**: backend/services/strategy_backtest.py
- **变更**: 
  - _execute_pending_buys 动态计算买入数量（100股整数倍）
  - 记录 open_price、close_price、equity_after

### 6. 修改回测引擎 - 卖出逻辑
- **文件**: backend/services/strategy_backtest.py
- **变更**: 卖出时记录 open_price、close_price、equity_after

### 7. 降低历史数据要求
- **文件**: backend/services/strategy_backtest.py
- **变更**: _get_stock_data_before_date 默认 days=30

### 8. 降低策略引擎历史数据要求
- **文件**: backend/services/strategy_engine.py
- **变更**: _get_stock_daily_data 默认 days=30

### 9. 修改前端展示
- **文件**: frontend/src/views/Backtest.vue
- **变更**: 交易记录表格新增开盘价、收盘价、交易后权益三列

### 10. 验证测试
- **操作**: 运行6月1日-10日回测，验证数据正确性
- **结果**: 交易后权益与回测汇总一致 ✓
