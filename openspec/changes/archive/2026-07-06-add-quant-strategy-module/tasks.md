## 1. 数据模型与数据库

- [x] 1.1 创建 `backend/models/strategy.py`：定义 StrategyPosition、StrategyTransaction、StrategyCash、StrategyConfig 四个 SQLAlchemy 模型
- [x] 1.2 创建 `backend/utils/migrate_strategy.py`：数据库迁移脚本，创建对应的四张表
- [x] 1.3 在 `backend/models/__init__.py` 中注册新模型

## 2. 策略配置模块

- [x] 2.1 创建 `backend/services/strategy_config.py`：实现 StrategyConfigService 类，提供 get/set/get_all/init_defaults 方法
- [x] 2.2 实现配置预期收益预览：根据当前 stop_profit_pct、stop_loss_pct 和 45% 估计胜率，自动计算预期年化收益
- [x] 2.3 实现 `GET /api/strategy/config` 和 `PUT /api/strategy/config` 两个配置接口

## 3. 策略引擎核心

- [x] 3.1 创建 `backend/services/strategy_engine.py`：实现多因子评分引擎
  - 数据准备：从 StockDaily 获取所有股票最近 N 日数据（N >= 60）
  - 排除涨跌停股票（change_percent >= 9.9% 或 <= -9.9%）
  - 调用 IndicatorEngine 批量获取 MA5/MA20/RSI14/ATR14 指标
  - 实现各因子的归一化评分函数（0~1 得分）
  - 计算加权总分并按降序排序
- [x] 3.2 实现推荐生成逻辑
  - 根据可用仓位数取 TOP N
  - 计算建议买入价（close × 1.01）、目标止盈价（buy_price × (1+stop_profit_pct)）、止损价（buy_price × (1-stop_loss_pct)）
  - 跳过资金不足的推荐
- [x] 3.3 实现 `_factor_trend()`：趋势因子 - 基于 (MA5 - MA20) / MA20 计算乖离率得分
- [x] 3.4 实现 `_factor_momentum()`：动量因子 - 基于 RSI14 标准化得分
- [x] 3.5 实现 `_factor_volume()`：成交量因子 - 基于 volume / avg_volume_20 比值得分
- [x] 3.6 实现 `_factor_reversal()`：反转因子 - 基于近 3 日累计涨跌幅得分
- [x] 3.7 实现 `_factor_volatility()`：波动率因子 - 基于 ATR14 / close 标准化得分

## 4. 持仓管理模块

- [x] 4.1 创建 `backend/services/position_manager.py`：实现 PositionManager 类
  - `open_position()`：创建持仓记录、扣减资金、记录交易流水
  - `close_position()`：更新持仓状态、回笼资金、计算盈亏、记录交易流水
  - `check_sell_conditions()`：遍历所有 holding 持仓，检测止盈/止损/超时条件
  - `get_available_slots()`：返回可用持仓数 = max_positions - 当前 holding 数
  - `get_stats()`：计算胜率、已实现收益、浮动盈亏、总收益率、年化收益率
  - `get_return_comparison()`：对比实际年化收益与 target_annual_return，返回 on_track 状态
- [x] 4.2 在 `strategy_cash` 模型中添加 `initial_capital` 字段，首次初始化后锁定不变

## 5. 策略 API 路由

- [x] 5.1 在 routes.py 中实现策略接口（复用现有 api Blueprint，直接添加路由）
  - `GET /api/strategy/recommendations`：获取每日推荐
  - `GET /api/strategy/positions`：获取当前持仓
  - `GET /api/strategy/transactions`：分页查询交易记录
  - `GET /api/strategy/stats`：获取绩效统计
  - `POST /api/strategy/run`：手动触发策略执行
- [x] 5.2 策略路由已注册到现有 api Blueprint 中

## 6. 前端策略看板

- [x] 6.1 创建 `frontend/src/api/strategy.js`：封装策略相关 API 调用
- [x] 6.2 创建 `frontend/src/views/StrategyBoard.vue`：策略看板页面
  - 配置面板：可编辑参数（target_annual_return, max_positions, stop_profit_pct, stop_loss_pct, max_hold_days），修改止盈止损时实时预览预期年化收益
  - 运行按钮：手动触发策略
  - 收益对比卡片：进度条展示实际年化收益 vs 目标收益，绿色达标/红色未达标
  - 推荐列表：表格展示股票代码、名称、评分、建议买卖价
  - 持仓列表：表格展示持仓股、买入价、浮动盈亏、持有天数
  - 交易记录：分页表格
  - 绩效统计：年化收益率、目标收益率、胜率、累计收益、总权益、盈亏比
- [x] 6.3 在前端路由中注册 `/strategy` 路由

## 7. 数据库迁移

- [x] 7.1 运行数据库迁移脚本，创建策略相关的四张表
- [x] 7.2 初始化默认策略配置
