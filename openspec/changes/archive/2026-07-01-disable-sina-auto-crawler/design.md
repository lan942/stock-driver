## Context

当前股票爬虫系统使用双数据源切换策略：东方财富（stock_zh_a_spot_em）优先，新浪（stock_zh_a_spot）备用。然而，东方财富API近期不稳定（ConnectionError/RemoteDisconnected），新浪API虽稳定但缺少关键分析字段（换手率、市盈率、市净率、市值）。此外，Stock模型缺少price_date字段，无法确定数据的时效性。系统没有爬取状态记录机制，无法监控爬取进度或追踪失败记录。定时任务机制缺失，需手动触发爬取，效率低下。

**Constraints**:
- SQLite数据库，单数据源架构
- Flask应用运行在5000端口
- 东方财富API不稳定但提供完整字段，暂无其他可用数据源
- 必须避免频繁爬取导致IP被封禁

**Stakeholders**:
- 开发者：需要监控爬取状态和手动重试
- 用户：需要查看时效性准确的股票数据

## Goals / Non-Goals

**Goals:**
- 禁用新浪数据源，StockRealtimeCrawler仅使用东方财富源（简化逻辑，避免使用不完整数据）
- Stock模型增加price_date字段，记录价格数据日期（追踪时效性）
- 新增CrawlStatus模型，记录每次爬取的类型、状态、时间、成功/失败数量、错误信息
- 实现定时任务调度器，自动执行股票列表更新（每日一次）和实时行情爬取（交易日每5分钟）

**Non-Goals:**
- 不解决东方财富API不稳定问题（外部因素，等待官方修复）
- 不增加雪球等新数据源（雪球需token且只能单只查询，不适合全市场爬取）
- 不实现自动重试机制（仅记录失败状态，用户手动判断重试）
- 不实现交易日判断逻辑（定时任务每日固定时间运行，由用户判断交易日）

## Decisions

### Decision 1: 禁用新浪数据源的策略

**选择**: 完全移除新浪数据源切换逻辑，StockRealtimeCrawler仅使用东方财富源

**理由**:
- 新浪数据缺少关键字段（换手率、市盈率、市净率、市值），无法满足全市场分析需求
- 双数据源切换增加了代码复杂度，且新浪数据不完整会导致分析结果不准确
- 东方财富API虽不稳定，但提供完整字段，更符合分析需求

**替代方案考虑**:
- **保留新浪作为备用**: 虽能提高可用性，但数据不完整会导致分析结果不一致，用户体验差
- **使用雪球替代**: 雪球需token且只能单只查询，不适合全市场爬取（5000+股票），性能差

**影响**: 东方财富API不稳定期间，实时行情爬取可能失败，但CrawlStatus会记录失败状态，用户可手动重试

### Decision 2: price_date字段的类型和更新策略

**选择**: price_date使用Date类型（仅日期，不含时间），每次更新价格时同步更新

**理由**:
- 股票价格数据本身只有日期概念（日线数据），不需要精确时间戳
- Date类型简化存储和查询，符合股票数据业务语义
- 每次更新价格时同步更新price_date，确保数据时效性一致

**替代方案考虑**:
- **使用DateTime类型**: 增加不必要的复杂度，股票价格数据不需要时间戳
- **仅在首次爬取时设置price_date**: 无法反映数据更新时效性，误导用户

### Decision 3: CrawlStatus模型的字段设计

**选择**: 记录爬取类型、状态、时间、成功/失败数量、错误信息

**字段设计**:
- `crawl_type`: String（'list'或'realtime'）
- `status`: String（'success'、'partial'、'failed'）
- `crawl_time`: DateTime（爬取开始时间）
- `success_count`: Integer（成功数量）
- `fail_count`: Integer（失败数量）
- `error_message`: Text（错误信息，仅失败时记录）

**理由**:
- crawl_type区分股票列表爬取和实时行情爬取
- status区分完全成功、部分成功、完全失败
- success_count/fail_count量化爬取效果
- error_message记录失败原因，方便用户排查

**替代方案考虑**:
- **不记录success_count/fail_count**: 无法量化爬取效果，用户难以判断数据完整性
- **不记录error_message**: 用户无法排查失败原因，无法判断是否值得重试

### Decision 4: 定时任务调度器选型

**选择**: 使用APScheduler的BackgroundScheduler

**理由**:
- APScheduler是Python最成熟的定时任务库，支持多种触发器（interval、cron）
- BackgroundScheduler在后台线程运行，不阻塞Flask主线程
- 支持任务持久化（可选），适合Flask应用

**替代方案考虑**:
- **Celery**: 需要Redis/RabbitMQ作为broker，架构复杂，不适合小型项目
- **系统cron**: 需外部配置，无法集成到Flask应用，难以监控和管理

**任务配置**:
- 股票列表更新：每日00:30执行（cron触发器）
- 实时行情爬取：每5分钟执行（interval触发器，仅交易日）

### Decision 5: 数据库迁移策略

**选择**: 使用SQLite ALTER TABLE语句手动迁移

**理由**:
- SQLite不支持复杂的ALTER TABLE（如DROP COLUMN），需手动迁移
- 项目规模小，手动迁移可控
- 使用迁移脚本确保迁移过程可追溯

**迁移步骤**:
1. 备份现有数据库文件
2. 创建crawl_status表
3. 为stocks表增加price_date列
4. 更新现有数据：将price_date设置为最近一次爬取日期

**替代方案考虑**:
- **使用Alembic**: 需引入额外依赖，增加复杂度，不适合小型项目
- **重建数据库**: 丢失现有数据，影响用户体验

## Risks / Trade-offs

### Risk 1: 东方财富API不稳定导致爬取失败

- **风险**: 东方财富API可能持续不稳定，导致实时行情无法更新
- **缓解**: CrawlStatus记录失败状态和错误信息，用户可手动重试或等待API恢复
- **Trade-off**: 暂不引入雪球等新数据源，避免架构复杂化

### Risk 2: 定时任务在非交易日运行浪费资源

- **风险**: 定时任务在周末或节假日运行，无意义爬取浪费资源
- **缓解**: 用户可通过API手动控制定时任务暂停/恢复
- **Trade-off**: 不实现交易日判断逻辑（需额外数据源），保持简单

### Risk 3: 数据库迁移失败导致数据丢失

- **风险**: ALTER TABLE操作失败，可能导致数据损坏或丢失
- **缓解**: 迁移前备份数据库文件，迁移失败可回滚
- **Trade-off**: 不使用Alembic等迁移工具，手动迁移可控但需谨慎操作

### Risk 4: APScheduler与Flask集成可能存在线程安全问题

- **风险**: BackgroundScheduler在后台线程运行，可能与Flask主线程存在并发问题
- **缓解**: APScheduler官方文档提供Flask集成最佳实践，确保线程安全
- **Trade-off**: 不使用Celery等分布式任务队列，保持架构简单

## Migration Plan

### 步骤1: 数据库备份
- 复制data/stock.db为data/stock.db.backup
- 验证备份文件完整性

### 步骤2: 创建crawl_status表
```sql
CREATE TABLE crawl_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crawl_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    crawl_time DATETIME NOT NULL,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    error_message TEXT
);
```

### 步骤3: 为stocks表增加price_date列
```sql
ALTER TABLE stocks ADD COLUMN price_date DATE;
```

### 步骤4: 更新现有数据
- 查询最近的StockDaily记录，获取最近爬取日期
- 更新所有Stock记录的price_date为最近爬取日期（或NULL）

### 步骤5: 验证迁移
- 检查表结构是否正确
- 检查数据完整性
- 测试API接口是否正常工作

### 回滚策略
- 若迁移失败，删除data/stock.db
- 将data/stock.db.backup恢复为data/stock.db
- 重新启动应用

## Open Questions

暂无待解决问题，设计已充分考虑技术可行性和业务需求。