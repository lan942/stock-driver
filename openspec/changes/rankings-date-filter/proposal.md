## Why

涨跌排行页面（TopStocks）当前只展示 Stock 表的实时行情数据，没有日期标识，用户无法判断这是哪一天的数据；同时无法查看历史某天的涨跌排行，只能看"当前"一张快照，缺少回溯能力。

## What Changes

- 后端 `/stocks/top/gainers` 和 `/stocks/top/losers` 新增 `date` 查询参数：传入日期时从 `StockDaily` 表查询该日涨跌排行，不传时默认查最新一天
- 后端排行接口返回结果新增 `price_date` 字段，明确标注数据日期
- 前端 `TopStocks.vue` 顶部新增日期选择器：默认填入最新数据日期，支持切换历史日期，支持清空回到"最新"
- 前端切换日期时自动重新加载两个榜单
- 前端显示当前查看的日期信息

## Capabilities

### New Capabilities
- `stock-rankings`: 股票涨跌排行榜查询能力，支持按指定交易日查询涨幅/跌幅 Top N，默认返回最新交易日数据

### Modified Capabilities
<!-- 无现有 spec 的需求变更 -->

## Impact

- 后端
  - `backend/services/analysis.py`：`get_top_gainers` / `get_top_losers` 增加 `query_date` 参数，按日期从 `StockDaily` 表查询
  - `backend/api/routes.py`：`/stocks/top/gainers` 和 `/stocks/top/losers` 读取 `date` 参数并透传，返回结果增加 `price_date` 字段
- 前端
  - `frontend/src/api/stock.js`：`getTopGainers` / `getTopLosers` 支持传入 `date` 参数
  - `frontend/src/views/TopStocks.vue`：新增日期选择器、日期切换逻辑、当前日期提示条
- 数据：依赖 `stock_daily` 表已有数据（已完成腾讯源历史数据爬取）
- 不涉及破坏性变更：原 `limit` 参数保持兼容，`date` 为可选参数
