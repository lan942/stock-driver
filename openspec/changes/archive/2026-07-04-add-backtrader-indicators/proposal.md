## Why

股票详情页目前仅展示 MA5/10/20、MACD、RSI 五个基础技术指标，缺少布林带、KDJ、MA60、EMA、ATR 等投资者常用的技术分析工具。同时，K线图上没有均线等指标叠加，可视化分析能力有限。引入 Backtrader 的内置指标引擎后，可以零成本获得 100+ 专业技术指标，大幅提升股票详情页的分析价值。

## What Changes

- **后端新增**：基于 Backtrader 的指标计算服务，替代现有的手动 pandas 计算
- **新增 API**：`GET /api/stocks/<code>/indicators`，返回更丰富的技术指标数据
- **新增 API**：`GET /api/stocks/<code>/indicators/list`，返回可用的指标列表
- **前端扩展**：股票详情页的技术指标表格增加更多指标列（布林带、KDJ、MA60 等）
- **前端优化**：K线图叠加均线、布林带等可切换的指标线
- **数据流**：从数据库读取 `stock_daily` 数据 → Backtrader PandasData Feed → 策略计算指标 → 序列化返回前端

## Capabilities

### New Capabilities
- `backtrader-indicator-engine`: 基于 Backtrader 的指标计算引擎，支持动态加载任意内置指标
- `enhanced-stock-indicators-api`: 扩展的股票技术指标 API，支持按需查询特定指标和参数
- `chart-indicator-overlay`: K线图指标叠加功能，支持切换显示均线、布林带等

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- **后端新增模块**: `backend/services/indicator_engine.py` — Backtrader 指标计算封装
- **后端新增依赖**: `backtrader` Python 包
- **后端扩展路由**: `backend/api/routes.py` — 新增 `/api/stocks/<code>/indicators` 和 `/api/stocks/<code>/indicators/list`
- **前端修改文件**: `frontend/src/views/StockDetail.vue` — 扩展指标表格和图表叠加
- **前端新增组件**: `frontend/src/components/IndicatorPanel.vue` — 指标选择与展示面板
- **前端新增组件**: `frontend/src/components/ChartOverlay.vue` — 图表指标叠加控制
- **无数据库变更**: 指标运行时计算，不新增存储字段