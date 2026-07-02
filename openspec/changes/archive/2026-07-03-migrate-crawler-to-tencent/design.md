## Context

当前股票数据爬取系统严重依赖东方财富数据源，但东财接口频繁封IP（`RemoteDisconnected` 错误），导致实时行情、历史日线、股票列表等核心功能不可用。

经过前期测试验证：
- **腾讯日线接口 `stock_zh_a_daily`**：稳定可用，平均0.31s/只股票，连续20次请求不触发封IP
- **腾讯股票列表接口**：akshare 中未找到腾讯的股票列表接口（仅有 `stock_zh_a_hist_tx`、`stock_zh_a_tick_tx_js`、`stock_zh_index_daily_tx`）
- **腾讯实时行情接口**：akshare 中无明确的腾讯全市场实时行情快照接口

**Constraints**:
- SQLite 数据库
- 已有 `CrawlerBase` 抽象基类和 `normalizer.py` 归一化工具，需复用
- 股票列表已有数据存储在数据库中，可作为腾讯日线爬取的代码来源
- 腾讯接口缺少 PE/PB/总市值 等估值字段，接受这些字段为 NULL
- 腾讯日线是按单只股票逐个请求，而非一次性返回全市场

**Stakeholders**:
- 开发者：需要稳定可用的数据源
- 用户：需要历史日线数据用于分析

## Goals / Non-Goals

**Goals:**
- 新增腾讯日线爬虫（`TencentStockDailyCrawler`），支持单只和批量爬取
- 历史日线数据爬取切换到腾讯为主数据源
- 实时行情保留东财为主、腾讯无全市场快照接口则跳过
- 股票列表：腾讯无列表接口，保留现有方案（但需增加可靠性）
- 爬取调度器适配腾讯"按股票逐个爬取"的模式，支持进度跟踪
- 数据归一化层增加腾讯数据字段映射

**Non-Goals:**
- 不实现腾讯实时行情（腾讯无全市场快照接口，逐个爬取5000+只效率太低）
- 不补充 PE/PB/市值 等估值字段（接受缺失）
- 不改变数据库表结构（stock_daily 表已有字段允许为 NULL）
- 不删除东财爬虫代码，保留作为备用

## Decisions

### Decision 1: 腾讯日线爬虫架构设计

**选择**: 新增 `TencentStockDailyCrawler` 继承 `CrawlerBase`，单数据源（腾讯），支持单只和批量爬取。

**设计**:

```
backend/services/crawler/stock_daily.py
├── TencentStockDailyCrawler (extends CrawlerBase)
│   ├── fetch_single(code, start_date, end_date, adjust) -> DataFrame
│   ├── fetch_batch(codes, start_date, end_date, adjust, callback) -> (success, fail)
│   └── _fetch_from_source() / _is_rate_limit_error()
```

**腾讯接口参数**:
- `symbol`: 股票代码，格式 `sh600519` / `sz000001`
- `start_date`: 开始日期，格式 `YYYYMMDD`
- `end_date`: 结束日期，格式 `YYYYMMDD`
- `adjust`: 复权类型，`qfq`/`hfq`/`""`(不复权)

**腾讯返回字段（英文）**:
| 字段 | 类型 | 说明 | 单位 |
|------|------|------|------|
| date | date | 日期 | - |
| open | float | 开盘价 | 元 |
| high | float | 最高价 | 元 |
| low | float | 最低价 | 元 |
| close | float | 收盘价 | 元 |
| volume | float | 成交量 | 股 |
| amount | float | 成交额 | 元 |
| outstanding_share | float | 流通股本 | 股 |
| turnover | float | 换手率 | 小数（0.003983 = 0.3983%） |

**归一化映射**:
- `amount` → `turnover`（成交额，单位元，无需转换）
- `turnover` × 100 → `turnover_rate`（换手率，从小数转百分比）
- 计算 `change_percent` = `(今收 - 昨收) / 昨收 × 100`
- `pe` / `pb` / `market_cap` → `None`（腾讯不提供）

**理由**:
- 腾讯接口稳定、速度快、封IP少
- 复用现有 `CrawlerBase` 架构，保持代码一致性
- 归一化层已有完善的单位转换工具，只需增加英文字段映射

**替代方案考虑**:
- **直接调用腾讯HTTP API（绕过akshare）**：增加维护成本，akshare已封装好，稳定性有保障

### Decision 2: 股票列表数据源策略

**选择**: 腾讯无股票列表接口，保留现有 `stock_info_a_code_name`（新浪）作为主源，不切换。

**理由**:
- akshare 中未找到腾讯的 A 股股票列表接口
- 新浪 `stock_info_a_code_name` 接口之前测试可用
- 股票列表更新频率低（每天一次即可），封IP风险相对可控
- 数据库中已有股票列表数据，即使接口暂时不可用也不影响核心功能

**风险缓解**:
- 股票列表爬取频率降低为每周一次
- 保留数据库已有数据作为兜底

### Decision 3: 实时行情数据源策略

**选择**: 保留现有东财为主、东财直接HTTP为备的方案，不增加腾讯实时源。

**理由**:
- 腾讯无全市场实时行情快照接口
- 逐个爬取5000+只股票的实时行情，按0.3s/只计算需约25分钟，时效性太差
- 实时行情可以容忍偶尔失败（日线才是分析核心）
- 东财封IP问题主要影响历史日线批量爬取，实时行情每天只爬一次影响较小

### Decision 4: 批量爬取进度与调度策略

**选择**: 日线批量爬取使用"按股票逐个处理 + 进度回调"模式，调度器增加历史日线补数据任务。

**批量爬取设计**:
```python
def fetch_batch(
    self,
    codes: list[str],
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> tuple[int, int, list[dict]]:
    """
    批量爬取多只股票日线数据
    返回: (成功数, 失败数, 所有数据列表)
    """
```

**调度策略**:
- 新增"历史日线补数据"任务：每日收盘后执行，为每只股票补充当日日线
- 沿用 `CrawlStatus` 记录爬取状态
- 进度通过内存变量跟踪，供前端轮询

**理由**:
- 腾讯接口是单只股票模式，天然适合逐个处理
- 进度回调便于前端展示
- 每日增量爬取（每只股票只爬最新一天）耗时约 5500 × 0.3s ≈ 28分钟，可以接受

### Decision 5: 限流配置

**选择**: 腾讯接口限流配置相对宽松。

**配置**:
```python
RateLimitConfig(
    max_retries=3,
    base_wait=0.5,        # 基础等待0.5秒
    max_wait=30.0,        # 最大等待30秒
    requests_per_window=60,  # 每分钟60次
    window_seconds=60.0,
)
```

**理由**:
- 测试显示连续20次请求无压力，封IP阈值高
- 设置适度限流以防万一，不过度保守

## Risks / Trade-offs

### Risk 1: 腾讯接口也可能封IP

- **风险**: 批量爬取5000+只股票可能触发腾讯封IP
- **缓解**: 采用适度限流（每分钟60次）+ 指数退避重试
- **Trade-off**: 爬取速度 vs 稳定性，优先保障稳定性

### Risk 2: 批量爬取时间过长

- **风险**: 5500只股票 × 0.3s/只 ≈ 28分钟，全量历史补数据更久
- **缓解**:
  - 每日增量只爬最新一天，28分钟可接受
  - 全量历史数据可后台异步执行，不阻塞主流程
- **Trade-off**: 用时间换稳定性

### Risk 3: PE/PB/市值字段缺失影响体验

- **风险**: 用户可能依赖这些估值字段
- **缓解**: 接受缺失，这些字段对技术分析非必须；未来可从其他来源补充
- **Trade-off**: 功能完整性 vs 系统可用性，优先保障系统可用

### Risk 4: 股票列表接口不可用影响新股票发现

- **风险**: 新浪股票列表接口也可能失效
- **缓解**: 降低更新频率（每周一次），数据库已有数据作为兜底
- **Trade-off**: 新股票发现延迟 vs 接口稳定性

## Migration Plan

### 步骤1: 新增腾讯日线爬虫模块

- 创建 `backend/services/crawler/stock_daily.py`
- 实现 `TencentStockDailyCrawler` 类
- 增加 `normalizer.py` 中的腾讯数据归一化函数

### 步骤2: 更新数据服务层

- 在 `stock_service.py` 中新增 `save_stock_daily_batch()` 方法
- 支持批量保存多只股票的日线数据

### 步骤3: 新增 API 端点

- `POST /crawler/fetch_daily/<code>`: 单只股票历史日线（使用腾讯源）
- `POST /crawler/fetch_daily_batch`: 批量补日线数据
- `GET /crawler/progress`: 爬取进度查询

### 步骤4: 更新调度器

- 新增历史日线每日更新任务（收盘后执行）
- 实时行情任务保持不变
- 股票列表任务保持不变（降低频率可选）

### 步骤5: 更新前端

- 爬取进度页适配批量爬取进度展示
- 股票详情页处理 PE/PB 等字段为空的情况

### 步骤6: 测试验证

- 单只股票日线爬取测试
- 批量爬取测试（至少100只股票）
- 调度器自动执行测试
- 数据完整性验证

## Open Questions

1. **全量历史数据回填范围**：是否需要为所有股票回填上市以来的全部历史数据？还是只回填最近1年/3年？
2. **每日增量更新时间**：历史日线每日更新放在收盘后什么时间执行？与实时行情任务的关系？
3. **股票列表更新频率**：是否从每日调整为每周？
