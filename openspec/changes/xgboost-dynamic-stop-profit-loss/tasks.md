## 1. 策略模块扩展

- [ ] 1.1 在 `ml_strategy.py` 中添加 `score_stock_for_sell(code, buy_date)` 方法，基于买入日期之后的最新数据重新评分
- [ ] 1.2 在 `strategy_config.py` 中添加 `dynamic_sell_score_threshold` 配置项（默认0.5）

## 2. 回测引擎修改

- [ ] 2.1 修改 `strategy_backtest.py` 的 `_check_sell_for_day()` 方法，添加动态评分卖出判断逻辑
- [ ] 2.2 更新卖出原因类型：`sold` 拆分为 `take_profit` 和 `stop_loss`，新增 `dynamic_score`
- [ ] 2.3 实现卖出优先级：止损 > 止盈 > 动态评分

## 3. 数据模型更新

- [ ] 3.1 在 `BacktestTransaction` 模型中添加 `sell_reason` 字段（支持 take_profit/stop_loss/dynamic_score）
- [ ] 3.2 数据库迁移：添加 sell_reason 列

## 4. 前端展示

- [ ] 4.1 更新 `StrategyBoard.vue`，在交易记录中展示卖出原因
- [ ] 4.2 更新回测结果页面，展示不同卖出原因的统计

## 5. 测试验证

- [ ] 5.1 运行回测验证动态评分卖出功能正常工作
- [ ] 5.2 验证止盈止损底线保护机制生效
- [ ] 5.3 验证卖出原因正确记录
