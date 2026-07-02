- [x] 1.1 新增 `TencentStockDailyCrawler` 类（backend/services/crawler/stock_daily.py）
  - [x] 继承 CrawlerBase 基类
  - [x] 实现 _fetch_from_source（调用 ak.stock_zh_a_daily）
  - [x] 实现 _is_rate_limit_error
  - [x] 实现 fetch_single 方法（单只股票日线）
  - [x] 实现 fetch_batch 方法（批量 + 进度回调）

- [x] 1.2 扩展 normalizer.py 支持腾讯数据归一化
  - [x] 新增 normalize_tencent_daily_row 函数
  - [x] 英文字段映射（date/open/high/low/close/volume/amount/turnover）
  - [x] 换手率从小数转百分比
  - [x] 涨跌幅从收盘价计算
  - [x] PE/PB/market_cap 设为 None

- [x] 2.1 更新 stock_service.py 新增批量保存日线方法
  - [x] 新增 save_daily_batch 函数（多只股票批量保存）
  - [x] 复用现有 save_realtime_quotes 的字段保存逻辑
  - [x] 返回 (成功数, 失败数, 新增数, 更新数)

- [x] 3.1 新增/更新 API 端点
  - [x] 改造 POST /crawler/fetch_daily/<code> 使用腾讯源
  - [x] 新增 POST /crawler/fetch_daily_batch（批量补日线）
  - [x] 新增 GET /crawler/progress/daily（日线爬取进度）

- [x] 4.1 更新调度器 scheduler.py
  - [x] 新增 daily_quotes_update 任务（每日收盘后执行日线增量更新）
  - [x] 实现 _update_daily_quotes 方法（从Stock表取所有code，逐个爬最新一天）
  - [x] 记录 crawl_status（crawl_type='daily'）
  - [x] 交易日判断（与实时行情复用）

- [x] 5.1 股票列表爬虫策略调整
  - [x] StockListCrawler 增加新浪源为主（stock_info_a_code_name）
  - [x] 调度器股票列表更新频率调整为每周一
  - [x] 增加东财实时快照作为备用源

- [x] 6.1 前端爬取进度页适配
  - [x] 新增日线批量爬取的进度展示
  - [x] 进度条显示已完成/总数
  - [x] 股票详情页 PE/PB 为空时显示 "--"

- [x] 7.1 测试验证
  - [x] 单只股票日线爬取测试（数据完整性）
  - [x] 批量爬取测试（3只股票验证稳定性）
  - [x] 数据保存到数据库测试
  - [x] PE/PB 为空时前端展示正常（已有逻辑）
