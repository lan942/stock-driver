## Why

当前项目缺少稳定的 A 股数据爬取能力。akshare 是主力数据源，但其接口存在限流风险，需要构建具有容错能力的爬虫基础层，确保数据采集的连续性和可靠性。

## What Changes

- 新增 `StockCrawlerBase` 爬虫基类，统一管理接口调用、限流重试、异常处理
- 实现多数据源自动切换机制，当主接口触发限流时自动切换备用接口
- 统一字段单位转换，确保存储的数据单位一致
- 核心爬取能力：股票列表、实时行情、日线数据
- 支持手动触发重试和自动降级策略

## Capabilities

### New Capabilities

- `stock-list-crawler`: A 股股票列表爬取，支持全量获取和增量更新
- `stock-realtime-crawler`: 实时行情爬取，支持多字段（代码、开盘价、收盘价、成交额、换手、涨跌幅）
- `api-rate-limiter`: API 限流管理器，支持重试队列、自动切换接口、降级策略
- `data-normalizer`: 数据标准化工具，统一不同接口的单位差异

## Impact

- 新增 `backend/services/crawler/base.py` - 爬虫基类和限流管理器
- 新增 `backend/services/crawler/stock_list.py` - 股票列表爬虫
- 新增 `backend/services/crawler/stock_realtime.py` - 实时行情爬虫
- 新增 `backend/services/crawler/normalizer.py` - 数据标准化工具
- 修改 `backend/services/crawler/__init__.py` - 导出公共接口
- 依赖 akshare 库，需要处理接口返回值单位差异
