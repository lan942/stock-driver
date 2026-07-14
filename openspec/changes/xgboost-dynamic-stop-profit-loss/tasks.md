## 1. 策略模块扩展

- [x] 1.1 全市场批量评分 `_score_all_market_stocks()` 用于买入和卖出检测
- [x] 1.2 动态卖出评分阈值配置（percentile / decline_days / absolute / min_hold_days）

## 2. 回测引擎修改

- [x] 2.1 拆分 `_check_sell_for_day` 为 `_check_intraday_stop_loss`（日内止损）和 `_check_close_triggers`（收盘后评估）
- [x] 2.2 新增 `pending_sells` 队列，止盈/超时/动态评分收盘后评估、次日开盘价卖出
- [x] 2.3 买入去掉1%涨跌幅限制，T+1 开盘直接成交
- [x] 2.4 清仓阶段同步使用新的卖出逻辑
- [x] 2.5 移除 `force_close_method` 配置（统一使用次日开盘价）

## 3. 训练标签同步

- [x] 3.1 `compute_future_returns` 离场路径同步更新（止损=当日low卖，止盈/动态/超时=次日开盘卖）
- [x] 3.2 移除 `force_close_method` 参数，统一次日开盘价平仓
- [x] 3.3 `xgboost_trainer.py` 移除 `force_close_method` 调用

## 4. 配置更新

- [x] 4.1 `max_hold_days` 描述更新为"超过后次日开盘卖出"
- [x] 4.2 移除 `force_close_method` 默认配置

## 5. OpenSpec 文档同步

- [x] 5.1 更新 `stop-profit-loss-floor` spec
- [x] 5.2 更新 `xgboost-dynamic-score-sell` spec
- [x] 5.3 更新 `ml-label-generator` spec
- [x] 5.4 更新 `ml-strategy` spec
- [x] 5.5 更新 `design.md` 和 `proposal.md`

## 6. 测试验证

- [ ] 6.1 重新训练模型（标签逻辑已变）
- [ ] 6.2 运行回测验证新买卖逻辑
- [ ] 6.3 对比新旧回测结果差异
