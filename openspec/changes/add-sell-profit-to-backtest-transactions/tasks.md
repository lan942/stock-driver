## 1. 数据模型变更

- [ ] 1.1 `BacktestTransaction` 模型新增 `profit_pct` 字段（Float, nullable）— [backend/models/backtest.py](file:///d:/stock-driver/backend/models/backtest.py)
- [ ] 1.2 执行数据库迁移，为 `backtest_transactions` 表添加 `profit_pct` 列

## 2. 后端服务层改造

- [ ] 2.1 `add_transaction()` 新增 `profit_pct` 可选参数，卖出入库时存储 — [backend/services/backtest_service.py](file:///d:/stock-driver/backend/services/backtest_service.py)
- [ ] 2.2 `get_transactions()` 返回数据中新增 `profit_pct` 字段
- [ ] 2.3 `get_transactions_by_code()` 返回数据中新增 `profit_pct` 字段

## 3. 回测引擎传参

- [ ] 3.1 主循环卖出：在 `add_transaction()` 调用时传入已计算的 `profit_pct` — [backend/services/strategy_backtest.py](file:///d:/stock-driver/backend/services/strategy_backtest.py) (line ~485)
- [ ] 3.2 清仓阶段卖出：同上 (line ~573)
- [ ] 3.3 强制清仓卖出：同上 (line ~632)
- [ ] 3.4 将三处 `profit_pct` 写入 `sell_log` 的逻辑保持在现有位置之后，仅增加对 `add_transaction()` 的传参

## 4. 前端展示

- [ ] 4.1 交易表格新增「收益率」列，卖出行显示 `profit_pct`（绿涨红跌），买出行显示 `-` — [frontend/src/views/Backtest.vue](file:///d:/stock-driver/frontend/src/views/Backtest.vue)

## 5. 验证

- [ ] 5.1 启动后端服务，验证 API 返回的卖出记录包含 `profit_pct`
- [ ] 5.2 启动前端，验证回测管理页面交易记录表格正确显示收益率
- [ ] 5.3 运行一次回测，验证新生成的卖出记录带有正确的 `profit_pct` 值
