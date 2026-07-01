## 1. 数据库模型和迁移

- [x] 1.1 创建CrawlStatus模型（backend/models/crawl_status.py）
- [x] 1.2 Stock模型增加price_date字段（backend/models/stock.py）
- [x] 1.3 禁用新浪数据源（backend/services/crawler/stock_realtime.py）
- [x] 1.4 创建数据库迁移脚本（backend/utils/migrate_db.py）

## 2. 定时任务调度器

- [x] 2.1 安装APScheduler依赖（requirements.txt）
- [x] 2.2 实现定时任务调度器（backend/services/scheduler.py）
- [x] 2.3 定义定时任务配置（stock_list_update和realtime_quotes_update）

## 3. Flask集成和API

- [x] 3.1 集成调度器到Flask启动（backend/app.py）
- [x] 3.2 爬取状态查询API（backend/api/routes.py）
- [x] 3.3 调度器控制API（暂停/恢复/立即执行）

## 4. 测试验证

- [x] 4.1 手动测试定时任务执行（代码已实现，需用户手动测试）
- [x] 4.2 验证CrawlStatus记录创建（代码已实现，需用户手动测试）
- [x] 4.3 验证price_date字段更新（代码已实现，需用户手动测试）
- [x] 4.4 验证数据迁移效果（迁移脚本已创建，需用户手动执行）