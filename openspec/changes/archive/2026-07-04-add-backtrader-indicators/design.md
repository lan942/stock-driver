## Context

当前股票详情页通过 `GET /api/stocks/<code>/daily` 获取技术指标，后端使用 `analysis.py` 中的 pandas 计算逻辑，仅支持 MA5/10/20、MACD、RSI 五个指标。K 线图表也未叠加任何技术指标线。

此次变更引入 Backtrader 作为指标计算引擎，利用其 100+ 内置指标，在不改变现有数据库结构的前提下，扩展可展示的技术指标种类，并增强 K 线图的叠加可视化能力。

## Goals / Non-Goals

**Goals:**
- 建立基于 Backtrader 的通用指标计算引擎，支持动态加载任意内置指标
- 新增 API 接口，支持按需查询特定指标及参数
- 股票详情页扩展指标表格，展示更多技术分析数据
- K 线图支持叠加均线、布林带等可切换指标线
- 复用现有 `stock_daily` 数据，无需新增存储

**Non-Goals:**
- 不引入实盘交易或策略回测功能
- 不修改现有数据库 schema
- 不替换现有的 `analysis.py`（保留作为前端基础指标查询的轻量通道）
- 不实现 WebSocket 推送，指标数据通过 REST API 按需获取

## Decisions

### 1. 使用 Backtrader 而非自研指标计算
- **选择**: 使用 Backtrader Cerebro 引擎运行一个最小化策略来计算指标
- **理由**: Backtrader 提供 100+ 经过充分测试的内置指标（SMA、EMA、MACD、RSI、Bollinger、 Stochastic、ATR、ADX 等），且支持自定义参数，避免了重复造轮子。其 `PandasData` Feed 与现有 `stock_daily` 数据天然兼容
- **替代方案**: 在 `analysis.py` 中继续用 pandas 手写更多指标。否决理由是每个新指标都需要手动实现、测试和维护

### 2. 轻量 Cerebro 实例（非完整回测）
- **选择**: 创建一个最小化的 Cerebro 实例，仅加载数据和策略，不配置 Broker、不执行交易
- **理由**: Backtrader 在 `__init__` 阶段会计算所有声明的指标，无需运行完整的回测流程。这种方式开销极低，单次计算可在几十毫秒内完成
- **替代方案**: 使用 pandas-ta 或 ta 库。否决理由是和项目现有技术栈（已有 Backtrader 计划）保持一致，减少依赖数量

### 3. 结果缓存策略
- **选择**: 基于 `functools.lru_cache` 实现内存缓存，以 (code, days, indicators_hash) 为 key，TTL 5 分钟
- **理由**: 同一用户在浏览同一只股票时会在短时间内多次请求指标数据（切换指标、调整天数），缓存可避免重复计算。TTL 5 分钟平衡了实时性和性能
- **替代方案**: Redis 缓存。否决理由是对当前单用户场景过度设计

### 4. API 设计
- **选择**: 新增独立 API `/api/stocks/<code>/indicators`，不修改现有 `/api/stocks/<code>/daily`
- **理由**: 保持向后兼容，现有前端功能不受影响。新 API 支持请求参数指定指标列表和参数，灵活性更高
- **替代方案**: 扩展 `/api/stocks/<code>/daily` 的查询参数。否决理由是会增加该接口的复杂度，且已有前端依赖其返回结构

### 5. 前端图表叠加架构
- **选择**: 前端 ECharts 直接渲染叠加线，不引入额外图表库
- **理由**: 项目已使用 ECharts，其原生支持多条 series 叠加。均线、布林带等均为折线图 series，可直接在现有 K 线图基础上追加
- **替代方案**: 使用 TradingView 轻量图表。否决理由是需要引入额外依赖，且 ECharts 已能满足需求

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| Backtrader Cerebro 每次启动有固定开销（约 50-100ms） | 使用缓存减少重复计算；LRU 限制 100 条 |
| 大量用户并发请求可能导致后端计算压力 | 缓存命中率预计 >90%（同股票同参数重复请求）；必要时可加限流 |
| Backtrader 某些指标（如 KDJ）需自定义实现 | KDJ 可通过组合 Stochastic + MovingAverageSimple 实现，封装在引擎内部 |
| 内存缓存在服务重启后丢失 | 5 分钟 TTL 设计，重启后首次请求重新计算，影响极小 |