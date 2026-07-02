## Why

当前股票数据爬取系统存在以下严重问题：

1. **东方财富接口频繁封IP**：东财的 `stock_zh_a_hist`（日线）、`stock_zh_a_spot_em`（实时行情）、`stock_individual_info_em`（个股信息）等接口频繁出现 `RemoteDisconnected` 连接错误，导致数据爬取完全不可用，系统无法正常运行。

2. **实时行情数据源不稳定**：当前实时行情使用东财快照接口作为主源、直接HTTP作为备用，但两者都是东财数据源，封IP后同时失效，缺乏真正的异构数据源冗余。

3. **历史日线数据无法补充**：当前历史日线使用东财 `stock_zh_a_hist` 接口，东财封IP后无法为新股票或缺失数据补充历史日线。

4. **股票列表接口存在风险**：当前股票列表使用东财接口（`stock_zh_a_spot_em` 或 `stock_info_a_code_name`），同样面临东财封IP的风险。

经过测试验证，**腾讯财经接口**（akshare `stock_zh_a_daily`）具有以下优势：
- 稳定性高：连续20次请求0失败，未触发封IP
- 响应快：平均0.31秒/只股票
- 数据全：支持上市以来全部历史日线数据
- 核心字段完整：OHLCV、成交额、换手率等技术分析核心字段齐全

虽然腾讯接口缺少 PE/PB/总市值 等估值字段，但这些对于历史日线分析并非必须，可以接受缺失。

## What Changes

- **历史日线爬虫**：新增腾讯日线数据源（`stock_zh_a_daily`），作为历史日线数据的主数据源
- **实时行情爬虫**：将腾讯相关接口评估为备选数据源（需进一步验证腾讯实时行情接口可用性）
- **股票列表爬虫**：评估腾讯是否有股票列表接口，如有则切换；如无则保持现有方案
- **数据字段策略**：接受腾讯接口缺失 PE/PB/总市值 等估值字段，不影响核心使用
- **现有东财爬虫**：保留作为备用数据源，默认关闭或降级

## Capabilities

### New Capabilities

- `tencent-stock-daily-crawler`: 腾讯股票日线数据爬虫，支持历史数据批量爬取和单只股票补充
- `tencent-stock-list-crawler`（如果腾讯有列表接口）: 腾讯股票列表爬虫

### Modified Capabilities

- `stock-realtime-crawler`: 增加腾讯作为备选数据源（如果腾讯有实时接口）
- `stock-list-crawler`: 评估是否切换到腾讯数据源
- `auto-crawler-scheduler`: 调整调度逻辑适配腾讯按股票逐个爬取的模式

## Impact

- **Backend**:
  - `backend/services/crawler/stock_daily.py`: 新增腾讯日线爬虫模块
  - `backend/services/crawler/stock_list.py`: 评估是否切换腾讯源
  - `backend/services/crawler/stock_realtime.py`: 评估是否增加腾讯源
  - `backend/services/crawler/normalizer.py`: 增加腾讯数据字段映射（英文字段名、换手率小数转百分比等）
  - `backend/services/stock_service.py`: 新增按股票批量保存日线数据的方法
  - `backend/api/routes.py`: 新增腾讯日线爬取相关API端点

- **Database**:
  - `stock_daily` 表结构不变，PE/PB/market_cap 允许为 NULL
  - `crawl_status` 表增加 `source` 字段记录数据来源（可选）

- **Dependencies**:
  - 无需新增依赖（akshare 已安装，腾讯接口为 akshare 内置）

- **Frontend**:
  - 爬取进度展示需适配"按股票逐个爬取"的进度模式
  - 股票详情页 PE/PB 等字段为空时友好展示
