# 回测交易记录增强

## 问题描述
当前回测交易记录缺少关键信息，无法验证数据准确性：
1. 交易记录未记录当日开盘价和收盘价
2. 交易记录未记录交易后的总权益
3. 交易记录按创建时间倒序排列，不符合时间顺序阅读习惯
4. 买入数量固定为100股，未考虑资金规模和A股100股整数倍规则
5. 股票评分需要60天历史数据，导致大部分股票无法评分

## 解决方案
1. 在交易记录中添加 `open_price`、`close_price`、`equity_after` 字段
2. 修改交易记录排序为按交易日期正序
3. 动态计算买入数量（100股整数倍，不超过可用资金）
4. 将历史数据要求从60天降低到30天

## 涉及模块
- backend/models/backtest.py - 数据模型
- backend/services/backtest_service.py - 交易服务
- backend/services/strategy_backtest.py - 回测引擎
- backend/services/strategy_engine.py - 策略引擎
- frontend/src/views/Backtest.vue - 前端展示
