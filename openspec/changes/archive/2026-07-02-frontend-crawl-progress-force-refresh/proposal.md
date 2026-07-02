## Why

当前数据爬取页面（Crawler.vue）点击更新后只有按钮 loading 状态，用户无法直观看到爬取进度和最终结果；实时行情更新会受到当日已有成功爬取记录的影响（调度器检查），且不支持指定数据日期——而东方财富快照接口在非交易时间返回的其实是最近一个交易日的数据，用户需要手动指定日期才能正确记录。

## What Changes

- 股票列表更新：增加进度条和结果摘要（成功数、失败数、耗时）展示
- 实时行情更新：增加进度条和结果摘要（成功数、失败数、耗时）展示
- 实时行情更新：增加强制刷新（忽略当日已有成功记录，始终执行爬取）
- 实时行情更新：增加日期选择器，用户可指定数据对应日期
- 后端对应接口调整：支持 `force` 参数（跳过当日成功检查）和 `date` 参数（指定价格日期）
- 后端爬取状态接口：提供进度查询能力（轮询方式）

## Capabilities

### New Capabilities
- `crawl-ui-progress`: 前端爬取操作的进度展示、结果反馈、强制刷新与日期选择能力

### Modified Capabilities
- `auto-crawler-scheduler`: 手动触发实时行情更新时支持跳过当日成功记录检查、支持指定数据日期

## Impact

**前端：**
- `frontend/src/views/Crawler.vue` — 爬取操作 UI 重构，增加进度条、结果卡片、日期选择器
- `frontend/src/api/stock.js` — API 调用增加 `force` 和 `date` 参数，新增进度查询接口

**后端 API：**
- `backend/api/routes.py` — `update_realtime` 接口增加 `force` 和 `date` 参数，新增爬取状态/进度查询接口

**后端服务：**
- `backend/services/stock_service.py` — 保存实时行情时支持传入指定日期，强制刷新时跳过当日成功检查
