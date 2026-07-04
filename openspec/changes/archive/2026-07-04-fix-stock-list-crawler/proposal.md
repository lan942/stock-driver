## Why

前端"更新股票列表"按钮点击后返回 500（成功 0 只，耗时 0 秒）。根因：主源 `akshare.stock_info_a_code_name` 内部会调用北交所接口 `stock_info_bj_name_code`，而 `https://www.bse.cn/nqxxController/nqxxCnzq.do` 从本机网络持续 `RemoteDisconnected`，导致主源整链失败；备用源 `stock_zh_a_spot_em` 当前同样 `RemoteDisconnected`。两个源同时不可用，`StockListCrawler.fetch_stock_list()` 抛 `CrawlerError`，但 `routes.update_stock_list` 未捕获，Flask 直接返回 500 + 兜底文案，用户无法定位真实原因。

此外，BSE 端点长期不稳定（每次 `stock_info_a_code_name` 调用都会被它拖垮），需要换掉这个"一损俱损"的依赖路径。

## What Changes

- **BREAKING** `StockListCrawler` 主源由 `stock_info_a_code_name`（聚合接口，依赖 BSE）改为直接合并沪深交易所接口：`stock_info_sh_name_code(symbol='主板A股')` + `stock_info_sz_name_code(symbol='A股列表')`，避开 BSE 端点。
- 新增第三源 `stock_info_bj_name_code`（北交所直连）作为可选补充，单独 try/except 失败不影响沪深主列表返回（BJ 股票约 250 只，缺失可接受）。
- 备用源保留 `stock_zh_a_spot_em`，作为两源均失败时的最后兜底。
- `routes.update_stock_list` 增加 try/except，将 `CrawlerError` 转为 HTTP 503 + 结构化错误信息（`{error, sources_tried}`），不再以 500 静默兜底。
- 失败时通过 `record_crawl_status(crawl_type='list', status='failed', error_message=...)` 记录真实异常堆栈，便于排查。
- `StockListCrawler` 增加日志：每个源开始/失败/成功都打 INFO/WARN 日志。
- 同步 `openspec/specs/stock-list-crawler/spec.md`：数据源列表、失败处理场景。

## Capabilities

### New Capabilities
<!-- 无新增 capability -->

### Modified Capabilities
- `stock-list-crawler`: 主源由聚合接口改为沪深直连接口；新增 BJ 作为可选补充源；失败时主列表仍可返回（部分成功）；调用方对 `CrawlerError` 做结构化错误响应。

## Impact

- **代码**：
  - `backend/services/crawler/stock_list.py`：`DEFAULT_SOURCES` 重构，`_fetch_from_source` 新增 `akshare_sh_sz` 类型处理多源合并 + BJ 单独 try/except。
  - `backend/api/routes.py`：`update_stock_list` 加 try/except + 503 响应 + 失败状态记录。
  - `backend/services/scheduler.py`：`_update_stock_list` 同步调整日志与 error_message 字段（已有 try/except，仅需精修）。
- **Spec**：`openspec/specs/stock-list-crawler/spec.md` 数据源与失败场景更新。
- **依赖**：无新增（仍使用 akshare）。
- **数据库**：无 schema 变更。
- **API 契约**：`POST /api/crawler/update_list` 失败时状态码由 500 改为 503，响应体增加 `error` 字段（前端如有依赖 500 状态码需同步检查；当前前端只看 `success_count`/`message`，影响可控）。
- **测试**：新增 `tests/test_stock_list_crawler.py` 覆盖多源合并、BJ 失败容忍、整体失败抛错等场景。
