## Context

当前 `StockListCrawler` 配置了两个数据源：

1. `akshare_sina`：调用 `ak.stock_info_a_code_name()`。该函数内部串联调用 SH/SZ/BJ 三个交易所，其中 `stock_info_bj_name_code` 向 `https://www.bse.cn/nqxxController/nqxxCnzq.do` 发 POST 请求，本机网络长期 `RemoteDisconnected`，导致整条聚合链失败。
2. `akshare_em_spot`：调用 `ak.stock_zh_a_spot_em()`（东方财富实时快照）。本机同样 `RemoteDisconnected`，作为兜底失效。

`CrawlerBase.fetch()` 在两源都失败时返回 `CrawlerResult(success=False)`，`fetch_stock_list()` 据此抛 `CrawlerError`。`routes.update_stock_list` 未 try/except，Flask 转 500 + 兜底文案"成功 0 只，耗时 0 秒"，掩盖了真实错误。

经实测，沪深交易所直连接口工作正常：
- `ak.stock_info_sh_name_code(symbol='主板A股')` → 1699 行，列 `[证券代码, 证券简称, 上市日期, ...]`
- `ak.stock_info_sz_name_code(symbol='A股列表')` → 2895 行，列 `[板块, A股代码, A股简称, A股上市日期, ...]`
- BJ 端点单独调用仍 `RemoteDisconnected`。

## Goals / Non-Goals

**Goals:**
- 让"更新股票列表"按钮在 BJ 端点不可达时仍能返回有效的沪深 A 股列表（≥4500 只）。
- 主列表返回后，BJ 作为可选补充源独立尝试，失败仅打 WARN 日志、不拖垮主流程。
- API 失败时返回结构化错误（503 + `error` 字段），并在 `CrawlStatus` 表留下真实异常信息。
- 不破坏现有 `CrawlerBase` 的多源/重试/限流框架，仅扩展 `StockListCrawler` 的源类型。

**Non-Goals:**
- 不修复 akshare 上游 BSE 接口（属于第三方库问题）。
- 不重构 `CrawlerBase`，不动 rate_limiter。
- 不引入新的 HTTP 客户端或反爬框架。
- 不调整前端错误展示（前端当前只看 `success_count`/`message`，已能正确处理新响应）。
- 不替换 `stock_zh_a_spot_em` 备用源（保留作为最后兜底，等其恢复即可生效）。

## Decisions

### Decision 1: 主源改为 SH+SZ 直连合并，弃用 `stock_info_a_code_name`

**选择**：新增源类型 `akshare_sh_sz`，在 `_fetch_from_source` 内依次调用 `stock_info_sh_name_code(symbol='主板A股')` + `stock_info_sz_name_code(symbol='A股列表')`，分别标准化后合并去重返回。

**理由**：
- 直连交易所最稳定，不依赖第三方聚合层。
- 已实测两接口可正常返回 ~4594 只 A 股，覆盖核心需求。
- `stock_info_a_code_name` 的"聚合"价值低于它对 BSE 的强依赖带来的脆弱性。

**备选方案**：
- A. 修复 akshare 调用方式：monkey-patch 跳过 BJ。→ 侵入第三方库，升级易碎，否决。
- B. 改用东方财富 `stock_zh_a_spot_em` 作主源。→ 当前同样 RemoteDisconnected，不可靠；且实时快照语义不是"列表"语义，否决。
- C. 用 Tencent 接口。→ Tencent 没有现成的"全 A 股代码列表"接口，只有按代码查日线，否决。

### Decision 2: BJ 作为独立可选源，单独 try/except

**选择**：在 `akshare_sh_sz` 源内部，主列表（SH+SZ）拿到后，再尝试 `stock_info_bj_name_code()`，成功则合并 BJ 行（~250 只），失败则仅 WARN 不抛错。整源返回值是"主列表 + BJ（若可用）"。

**理由**：
- BJ 股票占比小（~5%），偶尔缺失不影响绝大多数策略回测和行情展示。
- 把 BJ 与 SH/SZ 放在同一 try 块里会让 BJ 失败再次拖垮整源，违背修复初衷。
- 独立 try/except 让"部分成功"成为可能，符合 Long-tail 容错策略。

**备选方案**：
- A. BJ 单独作为第三个 `DEFAULT_SOURCES` 项。→ 但 `CrawlerBase.fetch()` 的语义是"任一源成功就返回"，BJ 单源如果成功而 SH+SZ 失败会只返回 BJ 250 只，造成"成功但只有 250 只"的误导。否决，改为在 `akshare_sh_sz` 源内部聚合。

### Decision 3: `akshare_em_spot` 保留为兜底源

**选择**：`DEFAULT_SOURCES = [akshare_sh_sz, akshare_em_spot]`，顺序：直连 → 实时快照兜底。

**理由**：
- 当前 `akshare_em_spot` 也挂，但属于偶发网络问题，恢复后仍可作有效兜底。
- 不增加额外源，避免过度工程。

### Decision 4: 路由层 503 + 结构化错误

**选择**：`update_stock_list` 包 `try/except CrawlerError`，失败时：
- 返回 HTTP 503 + `{error: str(e), sources_tried: [...]}`。
- 调用 `record_crawl_status(crawl_type='list', status='failed', error_message=str(e))`。

**理由**：
- 500 是"服务器内部错误"语义，这里实际是"上游数据源不可用"，503 更准确。
- `error` 字段让前端能显示真实原因（如"BSE endpoint unreachable"），而非"成功 0 只"。
- `CrawlStatus` 落库真实错误，便于后续在"爬虫状态"页面展示。

### Decision 5: 标准化字段映射

**选择**：在 `_normalize_sh_dataframe` / `_normalize_sz_dataframe` 中分别从 `证券代码/证券简称`、`A股代码/A股简称` 提取，统一输出 `{code, name}`，复用现有 `normalize_stock_list_row` 做 A 股过滤与代码清洗。

**理由**：保持与现有 `_normalize_dataframe` 输出结构一致，下游 `save_stock_list` 无需改动。

## Risks / Trade-offs

- **[风险] 沪深接口未来也出现 RemoteDisconnected** → 已有 `akshare_em_spot` 兜底；并在路由层返回明确错误，便于人工介入。
- **[风险] SH/SZ 接口列名变更** → 在 normalize 函数中用 `row.get('证券代码', row.get('code', ''))` 兼容多种命名，并在 BJ 失败时打 WARN。
- **[权衡] BJ 股票缺失** → 接受 ~5% 缺口；如需完整可在 `CrawlStatus.error_message` 中显式记录"BJ source skipped"提示运维。
- **[权衡] 503 vs 500 状态码变化** → 前端当前不依赖 500 状态码做特殊逻辑，仅 `if (!res.ok)` 类判断，503 同样触发；如未来有前端区分需同步检查。
- **[风险] `stock_info_sh_name_code(symbol=...)` 的 symbol 取值可能随 akshare 版本变化** → 用常量 `SH_SYMBOL_MAIN_A = '主板A股'`、`SZ_SYMBOL_A_LIST = 'A股列表'` 集中定义，便于后续维护。
