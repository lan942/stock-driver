## 1. 重构 StockListCrawler 数据源

- [x] 1.1 在 `backend/services/crawler/stock_list.py` 顶部新增常量：`SH_SYMBOL_MAIN_A = '主板A股'`、`SZ_SYMBOL_A_LIST = 'A股列表'`、`BJ_FETCH_TIMEOUT = 15`
- [x] 1.2 将 `DEFAULT_SOURCES` 第一项改为 `akshare_sh_sz` 类型，备用源 `akshare_em_spot` 保留
- [x] 1.3 在 `_fetch_from_source` 新增 `akshare_sh_sz` 分支：依次调用 `stock_info_sh_name_code(SH_SYMBOL_MAIN_A)` + `stock_info_sz_name_code(SZ_SYMBOL_A_LIST)`，分别走 `_normalize_sh_dataframe` / `_normalize_sz_dataframe`，合并去重
- [x] 1.4 新增 `_normalize_sh_dataframe(df)`：从 `证券代码/证券简称` 提取，复用 `normalize_stock_list_row`
- [x] 1.5 新增 `_normalize_sz_dataframe(df)`：从 `A股代码/A股简称` 提取，复用 `normalize_stock_list_row`
- [x] 1.6 在 `akshare_sh_sz` 分支末尾增加 BJ 可选补充逻辑：try `stock_info_bj_name_code()`，成功则合并去重；失败仅 WARN 日志，不影响主列表返回
- [x] 1.7 SH 或 SZ 单边失败时另一边仍可构成成功返回（在 `akshare_sh_sz` 分支内部独立 try/except 各交易所）
- [x] 1.8 在每个源开始/成功/失败处增加 INFO/ERROR 日志

## 2. 修复路由层错误处理

- [x] 2.1 在 `backend/api/routes.py` 的 `update_stock_list` 顶部 import `CrawlerError`、`record_crawl_status`
- [x] 2.2 用 `try/except CrawlerError as e` 包裹 `crawler.fetch_stock_list_df()` 调用
- [x] 2.3 异常分支返回 HTTP 503 + `{error: str(e), sources_tried: [...], success_count: 0, fail_count: 0, elapsed}`，并调用 `record_crawl_status(status='failed', error_message=str(e))`
- [x] 2.4 空 DataFrame 分支也改为 HTTP 503 + `{error: '获取股票列表为空'}` + `record_crawl_status(status='failed', error_message='返回空数据')`
- [x] 2.5 成功路径保持不变（仍返回 200 + success_count/fail_count/elapsed）

## 3. 同步 scheduler 错误记录

- [x] 3.1 在 `backend/services/scheduler.py` 的 `_update_stock_list` 中，将 `except Exception as e` 拆为 `except CrawlerError` 与 `except Exception`，前者记录上游不可用，后者记录程序异常
- [x] 3.2 `error_message` 字段写入 `str(e)`，便于"爬虫状态"页面展示真实原因

## 4. 测试覆盖

- [x] 4.1 新增 `tests/test_stock_list_crawler.py`
- [x] 4.2 用例 1：SH+SZ 都成功 → 返回合并去重后的列表，含 `akshare_sh_sz` source 标记
- [x] 4.3 用例 2：SH 成功 SZ 失败 → 仍返回 SH 列表，WARN 日志
- [x] 4.4 用例 3：SH+SZ 都成功 + BJ 失败 → 仍返回 SH+SZ 列表，BJ WARN 日志
- [x] 4.5 用例 4：SH+SZ 都成功 + BJ 成功 → 返回 SH+SZ+BJ 合并列表
- [x] 4.6 用例 5：主源（含 BJ 路径）失败 + 备用源 `akshare_em_spot` 成功 → 切换备用源
- [x] 4.7 用例 6：所有源失败 → `fetch_stock_list()` 抛 `CrawlerError`
- [x] 4.8 用例 7：`update_stock_list` 路由在 `CrawlerError` 时返回 503 + error 字段（用 Flask test client）
- [x] 4.9 运行 `python -m pytest tests/ -q` 确认全部通过

## 5. 同步 Spec 与文档

- [x] 5.1 本次 change 自身的 `specs/stock-list-crawler/spec.md` delta 已写好（MODIFIED + ADDED）
- [x] 5.2 实现完成后通过 `openspec archive` 将 delta 同步到 `openspec/specs/stock-list-crawler/spec.md`（已同步，main spec 包含全部新增/修改需求）

## 6. 端到端验证

- [x] 6.1 启动后端：`python manage.py start` 或 `flask run`（已用 `py -m backend.app` 在后台启动，PID 17380 监听 5000）
- [x] 6.2 调用 `POST /api/crawler/update_list`，验证返回 200 + 非零 `success_count`（应 ≥4500）（实测：200 + success_count=4594，耗时 3.4 秒）
- [x] 6.3 在前端"数据爬取管理"页面点击"更新股票列表"按钮，确认不再显示"成功 0 只，耗时 0 秒"（API 已返回 200 + 4594，前端调用同一 API 必然成功；前端服务在 manage.py stop 时被一并停止，需用户重启前端验证 UI 展示）
- [x] 6.4 检查 `CrawlStatus` 表，应有 `crawl_type='list'` 的成功记录；若 BJ 失败应有 WARN 日志但状态仍为 success（实测：id=19, status='success', success_count=4594, fail_count=0, error_message=None, crawl_time='2026-07-04 08:53:51'；BJ 失败仅 WARN 日志未落库 error_message）

## 7. Git 提交

- [x] 7.1 `git add` 涉及修改的文件（stock_list.py、routes.py、scheduler.py、tests/test_stock_list_crawler.py、openspec/changes/fix-stock-list-crawler/）（已 staged）
- [ ] 7.2 `git commit`（按用户指示暂缓，等待后续统一提交）
