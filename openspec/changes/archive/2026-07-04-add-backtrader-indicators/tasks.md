## 1. 后端依赖与环境准备

- [x] 1.1 安装 backtrader Python 包到项目依赖
- [x] 1.2 创建 `backend/services/indicator_engine.py` 模块结构

## 2. 指标引擎核心实现

- [x] 2.1 实现 `IndicatorEngine` 类：封装轻量 Backtrader Cerebro 实例
- [x] 2.2 实现数据源适配器：从 `stock_daily` 查询数据并转为 PandasData Feed
- [x] 2.3 实现内置策略类：在 `__init__` 中根据请求动态声明指标
- [x] 2.4 实现指标映射表：将指标 ID（MA、RSI、BOLL 等）映射到 Backtrader 指标类
- [x] 2.5 实现 KDJ 指标（组合 Stochastic + SMA）
- [x] 2.6 实现结果序列化：将 Backtrader lines 转为 Python dict/list
- [x] 2.7 实现结果缓存：基于 LRU + TTL 的内存缓存

## 3. 新增 API 路由

- [x] 3.1 注册 `GET /api/stocks/<code>/indicators` 路由：解析参数、调用引擎、返回结果
- [x] 3.2 注册 `GET /api/stocks/<code>/indicators/list` 路由：返回可用指标清单
- [x] 3.3 添加错误处理：股票不存在、无数据、无效指标名等情况的响应

## 4. 前端页面改造

- [x] 4.1 更新 `frontend/src/api/stock.js`：添加 `getIndicators()` 和 `getIndicatorsList()` API 调用
- [x] 4.2 重构 `StockDetail.vue`：用新 indicators API 替换旧 daily API 的数据源
- [x] 4.3 扩展技术指标表格：增加 MA60、BOLL、KDJ、ATR、ADX 列，支持水平滚动
- [x] 4.4 创建 `IndicatorPanel.vue` 组件：指标选择 + 参数设置 + 刷新按钮
- [x] 4.5 创建 `ChartOverlay.vue` 组件：K线图上的指标叠加控制（均线/布林带）

## 5. 图表指标叠加

- [x] 5.1 修改 K 线图渲染：支持在 candlestick 上叠加 line series
- [x] 5.2 实现均线叠加逻辑：MA5/MA10/MA20/MA60 可选显示
- [x] 5.3 实现布林带叠加逻辑：上/中/下三线在图表上的渲染
- [x] 5.4 实现叠加控制 UI：切换开关 + 参数调整 + 刷新联动

## 6. 验证与测试

- [x] 6.1 单元测试：IndicatorEngine compute/cache/adapter 各场景
- [x] 6.2 手动验证：在浏览器打开 `/stock/000001`，确认指标和叠加正常显示
- [x] 6.3 回归验证：原 `/api/stocks/<code>/daily` 接口不受影响