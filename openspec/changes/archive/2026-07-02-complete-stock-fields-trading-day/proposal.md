## Why

当前系统存在以下问题：

1. **Stock模型字段不完整**：缺少开盘价(open)、最高价(high)、最低价(low)、换手率(turnover_rate)等关键分析字段，无法满足全市场分析需求。

2. **爬取时间策略不合理**：实时行情每5分钟执行一次，但东方财富API是一次性返回全市场快照，每分钟调用毫无意义；没有判断交易日（周末/节假日），浪费资源。

3. **爬取时机错误**：东方财富实时快照接口返回的是盘中数据，应该在收盘后（下午3点后）爬取才能获取完整的日K线数据。

4. **限流策略过于保守**：用户测试东方财富不容易限流，但当前配置每分钟仅10次请求且有1秒等待，影响爬取效率。

## What Changes

- **Stock模型增加字段**：open（开盘价）、high（最高价）、low（最低价）、turnover_rate（换手率）
- **StockDaily模型增加字段**：turnover_rate（换手率）
- **新增交易日判断**：判断是否为周末或节假日，仅在交易日执行爬取
- **调整爬取时间**：实时行情改为每个交易日收盘后（15:00后）执行一次
- **优化限流策略**：降低等待时间，提高请求限制（东方财富一次性返回全市场数据，只需1次请求）

## Capabilities

### New Capabilities

- `trading-day-utils`: 交易日判断工具，支持周末和节假日判断
- `complete-stock-fields`: Stock模型补全关键字段（open/high/low/turnover_rate）

### Modified Capabilities

- `auto-crawler-scheduler`: 修改爬取时间策略，仅在交易日收盘后爬取
- `stock-realtime-crawler`: 调整限流配置，移除不必要的等待

## Impact

- **Backend**:
  - `backend/models/stock.py`: Stock模型增加open/high/low/turnover_rate字段
  - `backend/models/stock.py`: StockDaily模型增加turnover_rate字段
  - `backend/services/utils/trading_day.py`: 新增交易日判断工具
  - `backend/services/scheduler.py`: 修改定时任务配置和爬取逻辑
  - `backend/services/crawler/stock_realtime.py`: 调整限流参数

- **Database**:
  - stocks表增加open/high/low/turnover_rate列
  - stock_daily表增加turnover_rate列

- **Dependencies**:
  - 无需新增依赖